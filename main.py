import logging
import asyncio
from pyrogram import Client
from config import config
from telegram_bot import setup_handlers
from control_bot import setup_control_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

async def start_services():
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment.")
        return

    session = config.TELEGRAM_STRING_SESSION.strip() if config.TELEGRAM_STRING_SESSION else "quiz_userbot"

    userbot_app = Client(
        name="quiz_userbot_session",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
        session_string=session if config.TELEGRAM_STRING_SESSION else None
    )
    setup_handlers(userbot_app)

    apps = [userbot_app]

    if config.BOT_TOKEN:
        control_app = Client(
            name="control_bot_session",
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH,
            bot_token=config.BOT_TOKEN
        )
        setup_control_bot(control_app)
        apps.append(control_app)
        logger.info("Secondary Control Bot enabled.")
    else:
        logger.info("BOT_TOKEN not provided; running Userbot only.")

    logger.info(f"Starting Telegram Quiz Userbot (Targeting bot: '{config.TARGET_QUIZ_BOT}')...")

    await asyncio.gather(*[app.start() for app in apps])
    logger.info("All services started successfully. Listening for messages...")
    await asyncio.Event().wait()

def main():
    try:
        asyncio.run(start_services())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down services...")

if __name__ == "__main__":
    main()
