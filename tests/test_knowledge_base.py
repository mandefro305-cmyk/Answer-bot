import os
import pytest
from unittest.mock import MagicMock, patch
from knowledge_base import KnowledgeBase

@pytest.fixture
def temp_kb(tmp_path):
    file_path = str(tmp_path / "test_kb.json")
    return KnowledgeBase(storage_path=file_path)

def test_add_pdf(temp_kb, tmp_path):
    # Mock PdfReader
    with patch("knowledge_base.PdfReader") as mock_pdf_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Leverage is a key forex concept."
        mock_pdf_reader.return_value.pages = [mock_page]

        doc_id = temp_kb.add_pdf("Leverage Guide", "dummy.pdf")
        assert doc_id == "pdf_leverage_guide"
        assert len(temp_kb.documents) == 1
        assert "Leverage is a key forex concept" in temp_kb.get_context_text()

def test_add_pdf_ocr_fallback(temp_kb):
    with patch("knowledge_base.PdfReader") as mock_pdf_reader, \
         patch.object(temp_kb, "_ocr_pdf_pages") as mock_ocr:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # Scanned image page, empty text
        mock_pdf_reader.return_value.pages = [mock_page]
        mock_ocr.return_value = ["Training Section Disclaimer: All Business Involves Risk"]

        doc_id = temp_kb.add_pdf("Scanned Disclaimer", "scanned.pdf")
        assert doc_id == "pdf_scanned_disclaimer"
        assert len(temp_kb.documents) == 1
        assert "Training Section Disclaimer: All Business Involves Risk" in temp_kb.get_context_text()

def test_add_youtube(temp_kb):
    with patch.object(temp_kb, "_fetch_youtube_transcript_text") as mock_fetch:
        mock_fetch.return_value = "Welcome to the lesson on margin level percentage. EUR USD is the currency pair used in this example."

        doc_id = temp_kb.add_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", custom_title="Forex Lesson")
        assert doc_id == "yt_dQw4w9WgXcQ"
        assert "EUR USD is the currency pair" in temp_kb.get_context_text()

def test_youtube_ytdlp_fallback(temp_kb):
    with patch.object(temp_kb, "_fetch_youtube_via_ytdlp", return_value="Prop Firm Trading Rules"):
        doc_id = temp_kb.add_youtube("https://www.youtube.com/watch?v=h9OrKyzgj-w")
        assert doc_id == "yt_h9OrKyzgj-w"
        assert "Prop Firm Trading Rules" in temp_kb.get_context_text()

def test_youtube_failure_raises(temp_kb):
    with patch.object(temp_kb, "_fetch_youtube_via_ytdlp", return_value=None), \
         patch("knowledge_base.YouTubeTranscriptApi") as mock_ytt:
        mock_ytt.return_value.fetch.side_effect = Exception("Blocked IP")
        if hasattr(mock_ytt, "get_transcript"):
            mock_ytt.get_transcript.side_effect = Exception("Blocked IP")

        with pytest.raises(ValueError, match="Could not retrieve a transcript"):
            temp_kb.add_youtube("https://www.youtube.com/watch?v=invalid1234")

def test_toggle_and_last_quiz(temp_kb):
    assert temp_kb.is_auto_answer_enabled is True
    temp_kb.is_auto_answer_enabled = False
    temp_kb.save()

    temp_kb.set_last_quiz("What is leverage?", {"A": "1:100", "B": "1:1"}, "A", bot_username="BirrForexChallengeBot")
    assert temp_kb.last_quiz["question"] == "What is leverage?"
    assert temp_kb.last_quiz["answer_key"] == "A"
    assert temp_kb.last_quiz["bot"] == "BirrForexChallengeBot"

def test_settings_and_bots(temp_kb):
    temp_kb.set_setting("answer_delay", 8)
    assert temp_kb.get_setting("answer_delay") == 8

    added = temp_kb.add_target_bot("@AnotherQuizBot")
    assert added is True
    assert "anotherquizbot" in temp_kb.get_target_bots()

    removed = temp_kb.remove_target_bot("AnotherQuizBot")
    assert removed is True
    assert "anotherquizbot" not in temp_kb.get_target_bots()

def test_export_csv(temp_kb):
    temp_kb.add_quiz_history("Q1", {"A": "OptA", "B": "OptB"}, "A", status="Submitted", bot_username="testbot")
    csv_str = temp_kb.export_quiz_history_csv()
    assert "Timestamp,Target Bot,Question" in csv_str
    assert "testbot,Q1,OptA" in csv_str
