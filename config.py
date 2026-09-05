import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_STRING_SESSION: str = os.getenv("TELEGRAM_STRING_SESSION", "")
    TARGET_QUIZ_BOT: str = os.getenv("TARGET_QUIZ_BOT", "BirrForexChallengeBot")
    ANSWER_DELAY_SECONDS: int = int(os.getenv("ANSWER_DELAY_SECONDS", "8"))

    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai").lower()

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip() or None
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

config = Config()
