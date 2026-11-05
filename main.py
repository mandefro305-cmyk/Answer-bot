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

    sessions = config.get_session_strings()
    userbot_apps = []

    if sessions:
        for idx, sess in enumerate(sessions, 1):
            client = Client(
                name=f"quiz_userbot_session_{idx}",
                api_id=config.TELEGRAM_API_ID,
                api_hash=config.TELEGRAM_API_HASH,
                session_string=sess
            )
            setup_handlers(client)
            userbot_apps.append(client)
    else:
        # Default single session file if no session string provided
        client = Client(
            name="quiz_userbot_session",
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH
        )
        setup_handlers(client)
        userbot_apps.append(client)

    apps = list(userbot_apps)

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

    logger.info(f"Starting {len(userbot_apps)} Telegram Quiz Userbot account(s) (Targeting bot: '{config.TARGET_QUIZ_BOT}')...")

    await asyncio.gather(*[app.start() for app in apps])

    # Pre-warm dialog peer cache for all userbot instances to resolve channel peer IDs (e.g., -100...)
    for idx, ub in enumerate(userbot_apps, 1):
        try:
            logger.info(f"Pre-warming dialog peer cache for userbot account {idx}...")
            async for _ in ub.get_dialogs(limit=200):
                pass
        except Exception as e:
            logger.warning(f"Dialog peer cache pre-warming warning for account {idx}: {e}")

    logger.info("All services started successfully. Listening for messages...")
    await asyncio.Event().wait()

def main():
    try:
        asyncio.run(start_services())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down services...")

if __name__ == "__main__":
    main()
