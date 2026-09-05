import logging
import asyncio
from pyrogram import Client
from config import config
from telegram_bot import setup_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

def main():
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment.")
        return

    session = config.TELEGRAM_STRING_SESSION.strip() if config.TELEGRAM_STRING_SESSION else "quiz_userbot"

    app = Client(
        name="quiz_userbot_session",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
        session_string=session if config.TELEGRAM_STRING_SESSION else None
    )

    setup_handlers(app)

    logger.info(f"Starting Telegram Quiz Userbot (Targeting bot: '{config.TARGET_QUIZ_BOT}')...")
    app.run()

if __name__ == "__main__":
    main()
