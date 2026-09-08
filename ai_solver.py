import re
import logging
from typing import Dict, Optional
from config import config
from knowledge_base import kb

logger = logging.getLogger("ai_solver")

def solve_quiz(question: str, options: Dict[str, str], provider: Optional[str] = None, model: Optional[str] = None) -> Optional[str]:
    """
    Sends question and options to OpenAI or Gemini API and returns the selected option key (A, B, C, or D).
    Incorporate reference study material from knowledge base if available.
    """
    selected_provider = (provider or kb.get_setting("ai_provider", config.AI_PROVIDER)).lower()
    selected_model = model or kb.get_setting("ai_model")

    options_text = "\n".join([f"{key}: {val}" for key, val in options.items()])

    kb_context = kb.get_context_text()
    context_section = f"Reference Study Material:\n{kb_context}\n\n" if kb_context else ""

    prompt = (
        "You are an expert quiz solver. Analyze the following question and select the correct option.\n\n"
        f"{context_section}"
        f"Question:\n{question}\n\n"
        f"Options:\n{options_text}\n\n"
        "Instructions:\n"
        "Respond ONLY with the single upper-case letter corresponding to the correct answer (e.g. A, B, C, or D).\n"
        "Do not include any explanation or extra characters."
    )

    raw_answer = ""

    providers_to_try = []
    if selected_provider == "gemini":
        providers_to_try = ["gemini", "openai"]
    else:
        providers_to_try = ["openai", "gemini"]

    used_provider = None
    for p in providers_to_try:
        try:
            p_model = selected_model if p == selected_provider else None
            if p == "gemini":
                if not config.GEMINI_API_KEY:
                    continue
                raw_answer = _solve_with_gemini(prompt, model=p_model)
            else:
                if not config.OPENAI_API_KEY:
                    continue
                raw_answer = _solve_with_openai(prompt, model=p_model)

            if raw_answer:
                used_provider = p
                break
        except Exception as e:
            logger.warning(f"Provider '{p}' failed with error: {e}. Trying alternative provider if available...")

    if not raw_answer:
        logger.error("All configured AI solvers failed or returned empty responses.")
        return None

    # Parse key from answer
    answer_key = _extract_option_key(raw_answer, list(options.keys()))
    logger.info(f"AI Provider '{used_provider}' (requested: {selected_provider}) answered: raw='{raw_answer}', parsed='{answer_key}'")
    return answer_key

def _solve_with_openai(prompt: str, model: Optional[str] = None) -> str:
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured in environment")

    from openai import OpenAI
    client_kwargs = {"api_key": config.OPENAI_API_KEY}
    base_url = config.OPENAI_BASE_URL
    if base_url:
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    chosen_model = model or config.OPENAI_MODEL

    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": "You are a precise multiple-choice quiz solver."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    return response.choices[0].message.content or ""

def _solve_with_gemini(prompt: str, model: Optional[str] = None) -> str:
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in environment")

    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    chosen_model = model or config.GEMINI_MODEL

    response = client.models.generate_content(
        model=chosen_model,
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
