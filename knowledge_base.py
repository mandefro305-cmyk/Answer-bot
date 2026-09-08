import os
import json
import re
import logging
from typing import Dict, List, Optional
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger("knowledge_base")

DATA_FILE = "knowledge_base.json"

class KnowledgeBase:
    def __init__(self, storage_path: str = DATA_FILE):
        self.storage_path = storage_path
        self.documents: Dict[str, dict] = {}  # doc_id -> {title, type, text, added_at}
        self.is_auto_answer_enabled: bool = True
        self.last_quiz: Optional[dict] = None
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.is_auto_answer_enabled = data.get("is_auto_answer_enabled", True)
                    self.last_quiz = data.get("last_quiz", None)
            except Exception as e:
                logger.error(f"Failed to load knowledge base file: {e}")

    def save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "documents": self.documents,
                    "is_auto_answer_enabled": self.is_auto_answer_enabled,
                    "last_quiz": self.last_quiz
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")

    def add_pdf(self, title: str, pdf_path_or_stream) -> str:
        """Extracts text from a PDF file/stream and adds it to the knowledge base."""
        reader = PdfReader(pdf_path_or_stream)
        text_pages = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            if txt.strip():
                text_pages.append(f"--- Page {i+1} ---\n{txt.strip()}")

        extracted_text = "\n\n".join(text_pages).strip()
        if not extracted_text:
            raise ValueError("No readable text found in PDF document.")

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
        """Extracts YouTube transcript and adds it to the knowledge base."""
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
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            raw = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            ytt = YouTubeTranscriptApi()
            fetched = ytt.fetch(video_id)
            raw = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched

        items = []
        for item in raw:
            if isinstance(item, dict) and "text" in item:
                items.append(item["text"])
        return " ".join(items)

    def _extract_youtube_id(self, url_or_id: str) -> Optional[str]:
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id
        pattern = r'(?:v=|\/([0-9A-Za-z_-]{11}).*|youtu\.be\/)([0-9A-Za-z_-]{11})'
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1) or match.group(2)
        return None

    def get_context_text(self) -> str:
        """Returns all knowledge base text concatenated to be included in LLM prompts."""
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

    def set_last_quiz(self, question: str, options: dict, answer_key: str, status: str = "Submitted"):
        self.last_quiz = {
            "question": question,
            "options": options,
            "answer_key": answer_key,
            "answer_value": options.get(answer_key, ""),
            "status": status
        }
        self.save()

kb = KnowledgeBase()
