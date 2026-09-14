import os
import json
import re
import csv
import io
import time
import logging
import urllib.request
from typing import Dict, List, Optional
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_bytes, convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

from config import config

logger = logging.getLogger("knowledge_base")

DATA_FILE = "knowledge_base.json"

class KnowledgeBase:
    def __init__(self, storage_path: str = DATA_FILE):
        self.storage_path = storage_path
        self.documents: Dict[str, dict] = {}
        self.is_auto_answer_enabled: bool = True
        self.last_quiz: Optional[dict] = None
        self.quiz_history: List[dict] = []
        self.settings: dict = {
            "answer_delay": config.ANSWER_DELAY_SECONDS,
            "ai_provider": config.AI_PROVIDER,
            "ai_model": config.OPENAI_MODEL if config.AI_PROVIDER == "openai" else config.GEMINI_MODEL,
            "manual_approval_mode": False,
            "target_bots": [config.TARGET_QUIZ_BOT] if config.TARGET_QUIZ_BOT else ["BirrForexChallengeBot"]
        }
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.is_auto_answer_enabled = data.get("is_auto_answer_enabled", True)
                    self.last_quiz = data.get("last_quiz", None)
                    self.quiz_history = data.get("quiz_history", [])
                    loaded_settings = data.get("settings", {})
                    self.settings.update(loaded_settings)
            except Exception as e:
                logger.error(f"Failed to load knowledge base file: {e}")

    def save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "documents": self.documents,
                    "is_auto_answer_enabled": self.is_auto_answer_enabled,
                    "last_quiz": self.last_quiz,
                    "quiz_history": self.quiz_history,
                    "settings": self.settings
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")

    def get_setting(self, key: str, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key: str, value):
        self.settings[key] = value
        self.save()

    def get_target_bots(self) -> List[str]:
        bots = self.settings.get("target_bots", [])
        if not bots:
            bots = [config.TARGET_QUIZ_BOT] if config.TARGET_QUIZ_BOT else ["BirrForexChallengeBot"]
        return [b.lstrip("@").strip().lower() for b in bots if b]

    def add_target_bot(self, bot_username: str) -> bool:
        clean = bot_username.lstrip("@").strip()
        if not clean:
            return False
        current = self.get_target_bots()
        if clean.lower() not in [c.lower() for c in current]:
            current_bots = self.settings.get("target_bots", [])
            current_bots.append(clean)
            self.settings["target_bots"] = current_bots
            self.save()
            return True
        return False

    def remove_target_bot(self, bot_username: str) -> bool:
        clean = bot_username.lstrip("@").strip().lower()
        current_bots = self.settings.get("target_bots", [])
        new_bots = [b for b in current_bots if b.lstrip("@").strip().lower() != clean]
        if len(new_bots) != len(current_bots):
            self.settings["target_bots"] = new_bots
            self.save()
            return True
        return False

    def add_quiz_history(self, question: str, options: dict, answer_key: str, status: str = "Submitted", bot_username: str = ""):
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "bot": bot_username or config.TARGET_QUIZ_BOT,
            "question": question,
            "options": options,
            "answer_key": answer_key,
            "answer_value": options.get(answer_key, ""),
            "status": status
        }
        self.last_quiz = record
        self.quiz_history.insert(0, record)  # prepend latest
        if len(self.quiz_history) > 500:     # keep last 500
            self.quiz_history = self.quiz_history[:500]
        self.save()

    def export_quiz_history_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Target Bot", "Question", "Option A", "Option B", "Option C", "Option D", "Selected Key", "Selected Value", "Status"])
        for q in self.quiz_history:
            opts = q.get("options", {})
            writer.writerow([
                q.get("timestamp", ""),
                q.get("bot", ""),
                q.get("question", ""),
                opts.get("A", ""),
                opts.get("B", ""),
                opts.get("C", ""),
                opts.get("D", ""),
                q.get("answer_key", ""),
                q.get("answer_value", ""),
                q.get("status", "")
            ])
        return output.getvalue()

    def _ocr_pdf_pages(self, pdf_path_or_stream) -> List[str]:
        if not HAS_OCR:
            return []
        try:
            images = []
            if isinstance(pdf_path_or_stream, (str, os.PathLike)):
                images = convert_from_path(pdf_path_or_stream)
            elif isinstance(pdf_path_or_stream, bytes):
                images = convert_from_bytes(pdf_path_or_stream)
            elif hasattr(pdf_path_or_stream, "read"):
                if hasattr(pdf_path_or_stream, "seek"):
                    pdf_path_or_stream.seek(0)
                content = pdf_path_or_stream.read()
                if hasattr(pdf_path_or_stream, "seek"):
                    pdf_path_or_stream.seek(0)
                images = convert_from_bytes(content)

            ocr_texts = []
            for img in images:
                txt = pytesseract.image_to_string(img) or ""
                ocr_texts.append(txt.strip())
            return ocr_texts
        except Exception as e:
            logger.warning(f"OCR pdf conversion failed: {e}")
            return []

    def add_pdf(self, title: str, pdf_path_or_stream) -> str:
        data_bytes = None
        if hasattr(pdf_path_or_stream, "read") and not isinstance(pdf_path_or_stream, (str, os.PathLike, bytes)):
            if hasattr(pdf_path_or_stream, "seek"):
                pdf_path_or_stream.seek(0)
            data_bytes = pdf_path_or_stream.read()
            if hasattr(pdf_path_or_stream, "seek"):
                pdf_path_or_stream.seek(0)
            pdf_src = io.BytesIO(data_bytes)
        else:
            pdf_src = pdf_path_or_stream

        reader = PdfReader(pdf_src)
        text_pages = []
        pages_needing_ocr = []

        for i, page in enumerate(reader.pages):
            txt = (page.extract_text() or "").strip()
            if txt:
                text_pages.append((i, txt))
            else:
                pages_needing_ocr.append(i)

        if pages_needing_ocr and HAS_OCR:
            ocr_src = data_bytes if data_bytes is not None else pdf_path_or_stream
            ocr_results = self._ocr_pdf_pages(ocr_src)
            for page_idx in pages_needing_ocr:
                if page_idx < len(ocr_results) and ocr_results[page_idx]:
                    text_pages.append((page_idx, ocr_results[page_idx]))

        text_pages.sort(key=lambda x: x[0])
        formatted_pages = [f"--- Page {idx+1} ---\n{text}" for idx, text in text_pages if text.strip()]
        extracted_text = "\n\n".join(formatted_pages).strip()

        if not extracted_text:
            raise ValueError("No readable text found in PDF document (including OCR scan).")

        doc_id = f"pdf_{title.lower().replace(' ', '_')}"
        self.documents[doc_id] = {
            "title": title,
            "type": "PDF",
            "text": extracted_text
        }
        self.save()
        logger.info(f"Added PDF to Knowledge Base: '{title}' ({len(extracted_text)} chars)")
        return doc_id

    def add_youtube(self, url_or_id: str, custom_title: Optional[str] = None) -> str:
        video_id = self._extract_youtube_id(url_or_id)
        if not video_id:
            raise ValueError("Invalid YouTube URL or Video ID.")

        text = self._fetch_youtube_transcript_text(video_id)
        title = custom_title or f"YouTube Video ({video_id})"

        doc_id = f"yt_{video_id}"
        self.documents[doc_id] = {
            "title": title,
            "type": "YouTube Video",
            "video_id": video_id,
            "text": text.strip()
        }
        self.save()
        logger.info(f"Added YouTube Transcript to Knowledge Base: '{title}' ({len(text)} chars)")
        return doc_id

    def _fetch_youtube_transcript_text(self, video_id: str) -> str:
        # Tier 1: yt-dlp direct caption URL extraction
        try:
            text = self._fetch_youtube_via_ytdlp(video_id)
            if text and text.strip():
                return text.strip()
        except Exception as e:
            logger.warning(f"yt-dlp transcript extraction failed for {video_id}: {e}")

        # Tier 2: Fallback to youtube-transcript-api
        try:
            raw = None
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                raw = YouTubeTranscriptApi.get_transcript(video_id)
            elif hasattr(YouTubeTranscriptApi, "fetch"):
                raw = YouTubeTranscriptApi.fetch(video_id)
            else:
                ytt = YouTubeTranscriptApi()
                if hasattr(ytt, "fetch"):
                    fetched = ytt.fetch(video_id)
                    raw = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
                elif hasattr(ytt, "get_transcript"):
                    raw = ytt.get_transcript(video_id)

            if raw:
                items = []
                for item in raw:
                    if isinstance(item, dict) and "text" in item:
                        items.append(item["text"])
                res = " ".join(items).strip()
                if res:
                    return res
        except Exception as e:
            logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")

        raise ValueError(
            f"Could not retrieve a transcript for YouTube video '{video_id}'. "
            "Please ensure the video has available captions or subtitles."
        )

    def _fetch_youtube_via_ytdlp(self, video_id: str) -> Optional[str]:
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Try different player_client configurations to bypass cloud/datacenter IP blocks (e.g. Railway, AWS)
        client_options = [
            ['android', 'ios', 'mweb', 'web'],
            ['android_creator', 'android'],
            ['ios', 'android'],
            ['mweb', 'android'],
            ['web']
        ]

        for client_list in client_options:
            ydl_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {'youtube': {'player_client': client_list}}
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    subs = info.get('subtitles') or {}
                    auto_subs = info.get('automatic_captions') or {}
                    all_subs = {**auto_subs, **subs}

                    if not all_subs:
                        continue

                    pref_langs = ['am-orig', 'am', 'en'] + [k for k in all_subs.keys() if k not in ['am-orig', 'am', 'en']]

                    for lang in pref_langs:
                        if lang in all_subs:
                            formats = all_subs[lang]
                            json3_fmt = next((f for f in formats if f.get('ext') == 'json3'), None)
                            vtt_fmt = next((f for f in formats if f.get('ext') == 'vtt'), None)
                            chosen_fmt = json3_fmt or vtt_fmt or (formats[0] if formats else None)

                            if chosen_fmt and chosen_fmt.get('url'):
                                sub_url = chosen_fmt['url']
                                try:
                                    req = urllib.request.Request(
                                        sub_url,
                                        headers={'User-Agent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 11; US)'}
                                    )
                                    with urllib.request.urlopen(req, timeout=10) as resp:
                                        content = resp.read().decode('utf-8')
                                        if chosen_fmt.get('ext') == 'json3':
                                            data = json.loads(content)
                                            segs = []
                                            for event in data.get('events', []):
                                                for seg in event.get('segs', []):
                                                    txt = seg.get('utf8', '').strip()
                                                    if txt and txt != '\n':
                                                        segs.append(txt)
                                            text = " ".join(segs)
                                        else:
                                            clean = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
                                            clean = re.sub(r'\d\d:\d\d:\d\d\.\d{3} --> \d\d:\d\d:\d\d\.\d{3}.*\n', '', clean)
                                            clean = re.sub(r'<[^>]+>', '', clean)
                                            lines = [l.strip() for l in clean.splitlines() if l.strip()]
                                            text = " ".join(lines)

                                        if text and text.strip():
                                            return text.strip()
                                except Exception as err:
                                    logger.debug(f"Failed fetching caption track '{lang}' for {video_id}: {err}")
            except Exception as client_err:
                logger.debug(f"yt-dlp extraction with player_client {client_list} failed for {video_id}: {client_err}")

        return None

    def _extract_youtube_id(self, url_or_id: str) -> Optional[str]:
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id
        pattern = r'(?:v=|\/([0-9A-Za-z_-]{11}).*|youtu\.be\/)([0-9A-Za-z_-]{11})'
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1) or match.group(2)
        return None

    def get_context_text(self) -> str:
        if not self.documents:
            return ""

        context_parts = []
        for doc in self.documents.values():
            context_parts.append(f"### Document: {doc.get('title')} ({doc.get('type')})\n{doc.get('text')}")

        return "\n\n".join(context_parts)

    def list_documents(self) -> List[dict]:
        return [
            {"id": k, "title": v.get("title"), "type": v.get("type"), "size": len(v.get("text", ""))}
            for k, v in self.documents.items()
        ]

    def clear(self):
        self.documents = {}
        self.save()

    def set_last_quiz(self, question: str, options: dict, answer_key: str, status: str = "Submitted", bot_username: str = ""):
        self.add_quiz_history(question, options, answer_key, status, bot_username)

kb = KnowledgeBase()
