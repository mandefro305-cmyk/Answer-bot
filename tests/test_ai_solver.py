import pytest
from unittest.mock import patch, MagicMock
from ai_solver import solve_quiz, _solve_with_openai, _solve_with_gemini

@patch("ai_solver._solve_with_openai")
def test_solve_quiz_openai(mock_openai):
    mock_openai.return_value = "A"
    question = "What is contract size?"
    options = {"A": "100k", "B": "10k"}

    ans = solve_quiz(question, options, provider="openai")
    assert ans == "A"
    mock_openai.assert_called_once()

@patch("ai_solver._solve_with_gemini")
def test_solve_quiz_gemini(mock_gemini):
    mock_gemini.return_value = "B) Standard"
    question = "What is contract size?"
    options = {"A": "100k", "B": "10k"}

    ans = solve_quiz(question, options, provider="gemini")
    assert ans == "B"
    mock_gemini.assert_called_once()

@patch("config.config.OPENAI_API_KEY", "mock-key")
@patch("openai.OpenAI")
def test_openai_api_call(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="C"))]
    mock_client.chat.completions.create.return_value = mock_completion

    res = _solve_with_openai("Test prompt")
    assert res == "C"

@patch("config.config.GEMINI_API_KEY", "mock-key")
@patch("google.genai.Client")
def test_gemini_api_call(mock_genai_cls):
    mock_client = MagicMock()
    mock_genai_cls.return_value = mock_client

    mock_response = MagicMock(text="D")
    mock_client.models.generate_content.return_value = mock_response

    res = _solve_with_gemini("Test prompt")
    assert res == "D"
