import asyncio
import logging
from typing import List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup
from config import config
from parser import parse_quiz
from ai_solver import solve_quiz

logger = logging.getLogger("telegram_userbot")

def is_target_bot(message: Message, target: str) -> bool:
    if not target or not message.from_user:
        return False

    clean_target = target.lstrip("@").strip().lower()

    if message.from_user.username and message.from_user.username.lower() == clean_target:
        return True

    if str(message.from_user.id) == clean_target:
        return True

    return False

def extract_inline_buttons(reply_markup: Optional[InlineKeyboardMarkup]) -> List[str]:
    buttons = []
    if reply_markup and reply_markup.inline_keyboard:
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.text:
                    buttons.append(btn.text)
    return buttons

async def handle_quiz_message(client: Client, message: Message):
    if not is_target_bot(message, config.TARGET_QUIZ_BOT):
        return

    text = message.text or message.caption or ""
    inline_buttons = extract_inline_buttons(message.reply_markup)

    parsed = parse_quiz(text, inline_buttons=inline_buttons)
    if not parsed:
        logger.debug("Message received from target bot, but no quiz question detected.")
        return

    logger.info(f"Quiz Question detected:\nQuestion: {parsed.question}\nOptions: {parsed.options}")

    try:
        answer_key = solve_quiz(parsed.question, parsed.options)
        if not answer_key:
            logger.error("Could not determine answer from AI solver.")
            return

        logger.info(f"Selected Answer: {answer_key} -> {parsed.options.get(answer_key)}")

        if config.ANSWER_DELAY_SECONDS > 0:
            logger.info(f"Waiting {config.ANSWER_DELAY_SECONDS} seconds before submitting answer...")
            await asyncio.sleep(config.ANSWER_DELAY_SECONDS)

        await submit_answer(client, message, answer_key, parsed.options)
    except Exception as e:
        logger.exception(f"Error processing quiz message: {e}")

async def submit_answer(client: Client, message: Message, answer_key: str, options: dict) -> bool:
    if message.reply_markup and message.reply_markup.inline_keyboard:
        # 1. Try matching button prefix e.g. "A", "A)", "A.", "A:"
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                btn_text = (btn.text or "").strip()
                if (btn_text.upper() == answer_key or
                    btn_text.upper().startswith(f"{answer_key})") or
                    btn_text.upper().startswith(f"{answer_key}.") or
                    btn_text.upper().startswith(f"{answer_key}:") or
                    btn_text.upper().startswith(f"OPTION {answer_key}")):

                    logger.info(f"Clicking matching inline button: '{btn_text}'")
                    await message.click(btn_text)
                    return True

        # 2. Try matching option value text in button
        opt_value = options.get(answer_key, "").strip().lower()
        if opt_value:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    btn_text = (btn.text or "").strip()
                    if opt_value in btn_text.lower():
                        logger.info(f"Clicking inline button by value match: '{btn_text}'")
                        await message.click(btn_text)
                        return True

    # Fallback: send text reply
    logger.info(f"No matching inline button found. Replying with text: '{answer_key}'")
    await message.reply_text(answer_key)
    return True

def setup_handlers(app: Client):
    @app.on_message(filters.incoming)
    async def message_handler(client: Client, message: Message):
        await handle_quiz_message(client, message)

    @app.on_edited_message(filters.incoming)
    async def edited_message_handler(client: Client, message: Message):
        await handle_quiz_message(client, message)
