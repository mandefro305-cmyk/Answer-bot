import re
import logging
from typing import Dict, Optional
from config import config

logger = logging.getLogger("ai_solver")

def solve_quiz(question: str, options: Dict[str, str], provider: Optional[str] = None) -> Optional[str]:
    """
    Sends question and options to OpenAI or Gemini API and returns the selected option key (A, B, C, or D).
    """
    selected_provider = (provider or config.AI_PROVIDER).lower()
    options_text = "\n".join([f"{key}: {val}" for key, val in options.items()])

    prompt = (
        "You are an expert quiz solver. Analyze the following question and select the correct option.\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{options_text}\n\n"
        "Instructions:\n"
        "Respond ONLY with the single upper-case letter corresponding to the correct answer (e.g. A, B, C, or D).\n"
        "Do not include any explanation or extra characters."
    )

    raw_answer = ""

    if selected_provider == "gemini":
        raw_answer = _solve_with_gemini(prompt)
    else:
        raw_answer = _solve_with_openai(prompt)

    if not raw_answer:
        logger.error("AI solver returned empty response")
        return None

    # Parse key from answer
    answer_key = _extract_option_key(raw_answer, list(options.keys()))
    logger.info(f"AI Provider '{selected_provider}' answered: raw='{raw_answer}', parsed='{answer_key}'")
    return answer_key

def _solve_with_openai(prompt: str) -> str:
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured in environment")

    from openai import OpenAI
    client_kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        client_kwargs["base_url"] = config.OPENAI_BASE_URL
    client = OpenAI(**client_kwargs)

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise multiple-choice quiz solver."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    return response.choices[0].message.content or ""

def _solve_with_gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in environment")

    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt
    )

    return response.text or ""

def _extract_option_key(raw_text: str, valid_keys: list) -> Optional[str]:
    text = raw_text.strip().upper()
    if text in valid_keys:
        return text

    # Regex search for valid letter
    pattern = r'\b(' + '|'.join(valid_keys) + r')\b'
    match = re.search(pattern, text)
    if match:
        return match.group(1)

    # Fallback search for any key character
    for char in text:
        if char in valid_keys:
            return char

    return None
