import os
import logging
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import config
from knowledge_base import kb

logger = logging.getLogger("control_bot")

control_app: Optional[Client] = None

def is_admin(user_id: int) -> bool:
    if not config.ADMIN_TELEGRAM_ID:
        return False
    return user_id == config.ADMIN_TELEGRAM_ID

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    status_emoji = "🟢 ON" if kb.is_auto_answer_enabled else "🔴 OFF"
    toggle_text = f"⚡ Toggle Auto-Answer ({status_emoji})"

    keyboard = [
        [InlineKeyboardButton("📊 Status & Stats", callback_data="menu_status"), InlineKeyboardButton(toggle_text, callback_data="menu_toggle")],
        [InlineKeyboardButton("📚 Knowledge Base", callback_data="menu_kb"), InlineKeyboardButton("📜 Last Answered Quiz", callback_data="menu_last_quiz")],
        [InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="menu_refresh")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def notify_admin_quiz_answered(question: str, options: dict, answer_key: str, status: str = "Submitted"):
    """Sends a real-time report to the admin Telegram account when a quiz is answered."""
    kb.set_last_quiz(question, options, answer_key, status)

    if not control_app or not config.ADMIN_TELEGRAM_ID:
        return

    answer_val = options.get(answer_key, "N/A")
    options_text = "\n".join([f"  • {k}: {v}" for k, v in options.items()])

    report = (
        "🎯 **Quiz Answered Report**\n\n"
        f"**Question:**\n{question}\n\n"
        f"**Options:**\n{options_text}\n\n"
        f"**Selected Answer:** `{answer_key}` ({answer_val})\n"
        f"**Status:** {status}"
    )

    try:
        await control_app.send_message(chat_id=config.ADMIN_TELEGRAM_ID, text=report)
    except Exception as e:
        logger.error(f"Failed to send quiz notification to admin: {e}")

def setup_control_bot(app: Client):
    global control_app
    control_app = app

    @app.on_message(filters.command(["start", "menu"]) & filters.private)
    async def start_handler(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            await message.reply_text("❌ Unauthorized access.")
            return

        text = (
            "🤖 **Quiz Bot Control Dashboard**\n\n"
            "Welcome! Manage your Telegram Quiz Userbot and study materials here.\n\n"
            "• Upload `.pdf` documents to feed study context.\n"
            "• Send YouTube video URLs to pull transcripts into knowledge base.\n"
            "• Use the buttons below to manage settings."
        )
        await message.reply_text(text, reply_markup=get_main_menu_keyboard())

    @app.on_message(filters.document & filters.private)
    async def pdf_upload_handler(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return

        if message.document and message.document.file_name and message.document.file_name.endswith(".pdf"):
            status_msg = await message.reply_text("📄 Processing PDF document...")
            temp_path = f"/tmp/{message.document.file_name}"
            try:
                await client.download_media(message, file_name=temp_path)
                doc_title = message.document.file_name.replace(".pdf", "")
                kb.add_pdf(doc_title, temp_path)

                await status_msg.edit_text(f"✅ **PDF Added to Knowledge Base!**\nTitle: `{doc_title}`")
            except Exception as e:
                logger.exception("Error processing PDF")
                await status_msg.edit_text(f"❌ Error adding PDF: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            await message.reply_text("⚠️ Please send a valid `.pdf` file.")

    @app.on_message(filters.regex(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$') & filters.private)
    async def youtube_link_handler(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return

        url = message.text.strip()
        status_msg = await message.reply_text("🎥 Extracting YouTube transcript...")
        try:
            doc_id = kb.add_youtube(url)
            await status_msg.edit_text(f"✅ **YouTube Transcript Added to Knowledge Base!**\nID: `{doc_id}`")
        except Exception as e:
            logger.exception("Error extracting YouTube transcript")
            await status_msg.edit_text(f"❌ Error extracting transcript: {e}")

    @app.on_callback_query()
    async def callback_handler(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Unauthorized", show_alert=True)
            return

        data = callback.data

        if data == "menu_toggle":
            kb.is_auto_answer_enabled = not kb.is_auto_answer_enabled
            kb.save()
            status_str = "ENABLED" if kb.is_auto_answer_enabled else "DISABLED"
            await callback.answer(f"Auto-answering is now {status_str}!")
            await callback.message.edit_reply_markup(reply_markup=get_main_menu_keyboard())

        elif data == "menu_status":
            auto_status = "🟢 Enabled" if kb.is_auto_answer_enabled else "🔴 Disabled"
            doc_count = len(kb.documents)
            text = (
                "📊 **Bot Status & Stats**\n\n"
                f"• **Auto-Answering:** {auto_status}\n"
                f"• **Target Quiz Bot:** `@{config.TARGET_QUIZ_BOT}`\n"
                f"• **Answer Delay:** `{config.ANSWER_DELAY_SECONDS}` seconds\n"
                f"• **AI Provider:** `{config.AI_PROVIDER.upper()}`\n"
                f"• **Knowledge Base Documents:** `{doc_count}`"
            )
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())

        elif data == "menu_kb":
            docs = kb.list_documents()
            if not docs:
                text = "📚 **Knowledge Base**\n\nNo study materials loaded yet.\nUpload PDFs or send YouTube links to add content!"
            else:
                lines = ["📚 **Knowledge Base Documents:**\n"]
                for i, d in enumerate(docs, 1):
                    lines.append(f"{i}. **{d['title']}** ({d['type']}) - {d['size']} chars")
                text = "\n".join(lines)

            kb_inline = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Clear Knowledge Base", callback_data="kb_clear")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_refresh")]
            ])
            await callback.message.edit_text(text, reply_markup=kb_inline)

        elif data == "kb_clear":
            kb.clear()
            await callback.answer("Knowledge base cleared!")
            await callback.message.edit_text("🧹 Knowledge base cleared.", reply_markup=get_main_menu_keyboard())

        elif data == "menu_last_quiz":
            lq = kb.last_quiz
            if not lq:
                text = "📜 **Last Answered Quiz**\n\nNo quizzes answered since last restart."
            else:
                opts = "\n".join([f"  • {k}: {v}" for k, v in lq['options'].items()])
                text = (
                    "📜 **Last Answered Quiz**\n\n"
                    f"**Question:**\n{lq['question']}\n\n"
                    f"**Options:**\n{opts}\n\n"
                    f"**Answer:** `{lq['answer_key']}` ({lq['answer_value']})\n"
                    f"**Status:** {lq['status']}"
                )
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())

        elif data == "menu_refresh":
            text = "🤖 **Quiz Bot Control Dashboard**\n\nSelect an option below or send study files/links:"
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
