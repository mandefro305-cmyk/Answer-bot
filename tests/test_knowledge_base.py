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

def test_add_youtube(temp_kb):
    with patch.object(temp_kb, "_fetch_youtube_transcript_text") as mock_fetch:
        mock_fetch.return_value = "Welcome to the lesson on margin level percentage. EUR USD is the currency pair used in this example."

        doc_id = temp_kb.add_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", custom_title="Forex Lesson")
        assert doc_id == "yt_dQw4w9WgXcQ"
        assert "EUR USD is the currency pair" in temp_kb.get_context_text()

def test_toggle_and_last_quiz(temp_kb):
    assert temp_kb.is_auto_answer_enabled is True
    temp_kb.is_auto_answer_enabled = False
    temp_kb.save()

    temp_kb.set_last_quiz("What is leverage?", {"A": "1:100", "B": "1:1"}, "A")
    assert temp_kb.last_quiz["question"] == "What is leverage?"
    assert temp_kb.last_quiz["answer_key"] == "A"
