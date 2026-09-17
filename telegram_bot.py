import asyncio
import logging
from typing import List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup
from config import config
from parser import parse_quiz
from ai_solver import solve_quiz
from knowledge_base import kb
from control_bot import notify_admin_quiz_answered, request_admin_approval

logger = logging.getLogger("telegram_userbot")

user_app: Optional[Client] = None

def is_target_bot(message: Message, target: Optional[str] = None) -> bool:
    if not message.from_user:
        return False

    sender_username = (message.from_user.username or "").strip().lower()
    sender_id = str(message.from_user.id)

    if target:
        clean_target = target.lstrip("@").strip().lower()
        return sender_username == clean_target or sender_id == clean_target

    targets = kb.get_target_bots()
    for t in targets:
        clean = t.lstrip("@").strip().lower()
        if sender_username == clean or sender_id == clean:
            return True

    return False

def extract_inline_buttons(reply_markup) -> List[str]:
    buttons = []
    if not reply_markup:
        return buttons

    inline_kb = getattr(reply_markup, "inline_keyboard", None)
    if inline_kb:
        for row in inline_kb:
            for btn in row:
                btn_text = getattr(btn, "text", None)
                if btn_text:
                    buttons.append(btn_text)
    else:
        reply_kb = getattr(reply_markup, "keyboard", None)
        if reply_kb:
            for row in reply_kb:
                for btn in row:
                    btn_text = getattr(btn, "text", None) if not isinstance(btn, str) else btn
                    if btn_text:
                        buttons.append(btn_text)
    return buttons

import re

CHALLENGE_KEYWORDS = ["join challenge", "start challenge", "open challenge", "enter challenge", "play challenge"]

async def handle_channel_challenge_trigger(client: Client, message: Message) -> bool:
    inline_kb = getattr(message.reply_markup, "inline_keyboard", None) if message.reply_markup else None
    if not inline_kb:
        return False

    for row in inline_kb:
        for btn in row:
            btn_text = (btn.text or "").strip().lower()
            if any(kw in btn_text for kw in CHALLENGE_KEYWORDS):
                logger.info(f"Challenge trigger button detected: '{btn.text}' in message {message.id}")
                # Check if it's a URL deep link to a bot
                if hasattr(btn, "url") and btn.url:
                    match = re.search(r"t(?:elegram)?\.me/([A-Za-z0-9_]+)(?:\?start=(.+))?", btn.url)
                    if match:
                        bot_username = match.group(1)
                        start_param = match.group(2)
                        cmd = f"/start {start_param}" if start_param else "/start"
                        logger.info(f"Opening deep-link bot @{bot_username} with command '{cmd}'")
                        await client.send_message(bot_username, cmd)
                        return True
                # Otherwise click the inline callback button
                try:
                    logger.info(f"Clicking challenge inline button '{btn.text}'")
                    await message.click(btn.text)
                    return True
                except Exception as e:
                    logger.error(f"Failed to click challenge button '{btn.text}': {e}")
    return False

async def handle_quiz_message(client: Client, message: Message):
    # Check if this message is a channel announcement / challenge trigger button
    await handle_channel_challenge_trigger(client, message)

    if not is_target_bot(message):
        return

    if not kb.is_auto_answer_enabled:
        logger.info("Auto-answering is currently disabled via Control Bot. Skipping message.")
        return

    text = message.text or message.caption or ""
    inline_buttons = extract_inline_buttons(message.reply_markup)

    parsed = parse_quiz(text, inline_buttons=inline_buttons)
    if not parsed:
        logger.debug("Message received from target bot, but no quiz question detected.")
        return

    bot_identifier = message.from_user.username or str(message.from_user.id)
    logger.info(f"Quiz Question detected from @{bot_identifier}:\nQuestion: {parsed.question}\nOptions: {parsed.options}")

    try:
        answer_key = solve_quiz(parsed.question, parsed.options)
        if not answer_key:
            logger.error("Could not determine answer from AI solver.")
            return

        logger.info(f"Selected Answer: {answer_key} -> {parsed.options.get(answer_key)}")

        delay = int(kb.get_setting("answer_delay", config.ANSWER_DELAY_SECONDS))
        if delay > 0:
            logger.info(f"Waiting {delay} seconds before submitting answer...")
            await asyncio.sleep(delay)

        manual_mode = kb.get_setting("manual_approval_mode", False)
        if manual_mode:
            logger.info("Manual approval mode is ON. Requesting approval from Admin...")
            approved, chosen_key = await request_admin_approval(parsed.question, parsed.options, answer_key, bot_username=bot_identifier)
            if approved:
                logger.info(f"Admin APPROVED key [{chosen_key}]. Submitting...")
                await submit_answer(client, message, chosen_key, parsed.options)
                kb.add_quiz_history(parsed.question, parsed.options, chosen_key, status=f"Approved & Submitted ({delay}s)", bot_username=bot_identifier)
            else:
                logger.info("Admin REJECTED or approval timed out. Skipping submission.")
                kb.add_quiz_history(parsed.question, parsed.options, answer_key, status="Rejected / Timed Out", bot_username=bot_identifier)
        else:
            await submit_answer(client, message, answer_key, parsed.options)
            kb.add_quiz_history(parsed.question, parsed.options, answer_key, status=f"Submitted ({delay}s)", bot_username=bot_identifier)
            await notify_admin_quiz_answered(parsed.question, parsed.options, answer_key, status=f"Submitted in {delay}s", bot_username=bot_identifier)

    except Exception as e:
        logger.exception(f"Error processing quiz message: {e}")

async def submit_answer(client: Client, message: Message, answer_key: str, options: dict) -> bool:
    inline_kb = getattr(message.reply_markup, "inline_keyboard", None) if message.reply_markup else None
    if inline_kb:
        # 1. Try matching button prefix e.g. "A", "A)", "A.", "A:"
        for row in inline_kb:
            for btn in row:
                btn_text = (getattr(btn, "text", "") or "").strip()
                if (btn_text.upper() == answer_key or
                    btn_text.upper().startswith(f"{answer_key})") or
                    btn_text.upper().startswith(f"{answer_key}.") or
                    btn_text.upper().startswith(f"{answer_key}:") or
                    btn_text.upper().startswith(f"OPTION {answer_key}")):

                    logger.info(f"Clicking matching inline button: '{btn_text}'")
                    await message.click(btn_text)
                    return True

        # 2. Try exact matching option value text in button
        opt_value = options.get(answer_key, "").strip().lower()
        if opt_value:
            for row in inline_kb:
                for btn in row:
                    btn_text = (getattr(btn, "text", "") or "").strip()
                    if opt_value == btn_text.lower():
                        logger.info(f"Clicking inline button by exact value match: '{btn_text}'")
                        await message.click(btn_text)
                        return True
            # Substring fallback
            for row in inline_kb:
                for btn in row:
                    btn_text = (getattr(btn, "text", "") or "").strip()
                    if opt_value in btn_text.lower():
                        logger.info(f"Clicking inline button by substring match: '{btn_text}'")
                        await message.click(btn_text)
                        return True

    # Fallback for ReplyKeyboardMarkup or plain text: match reply keyboard text or send answer
    reply_kb = getattr(message.reply_markup, "keyboard", None) if message.reply_markup else None
    if reply_kb:
        opt_val = options.get(answer_key, "").strip()
        for row in reply_kb:
            for btn in row:
                btn_text = getattr(btn, "text", btn) if not isinstance(btn, str) else btn
                btn_str = str(btn_text).strip()
                if btn_str.upper() == answer_key or (opt_val and opt_val.lower() in btn_str.lower()):
                    logger.info(f"Replying with matched reply keyboard button text: '{btn_str}'")
                    await message.reply_text(btn_str)
                    return True

    # Fallback: send text reply with answer_key
    logger.info(f"No inline or reply keyboard match found. Replying with text: '{answer_key}'")
    await message.reply_text(answer_key)
    return True

def setup_handlers(app: Client):
    global user_app
    user_app = app

    @app.on_message(filters.incoming)
    async def message_handler(client: Client, message: Message):
        await handle_quiz_message(client, message)

    @app.on_edited_message(filters.incoming)
    async def edited_message_handler(client: Client, message: Message):
        await handle_quiz_message(client, message)
