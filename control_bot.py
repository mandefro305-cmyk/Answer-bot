import os
import io
import asyncio
import logging
import uuid
from typing import Optional, Dict, Tuple
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import config
from knowledge_base import kb

logger = logging.getLogger("control_bot")

control_app: Optional[Client] = None
pending_approvals: Dict[str, asyncio.Event] = {}
approval_results: Dict[str, bool] = {}
approval_selected_key: Dict[str, str] = {}

def is_admin(user_id: int) -> bool:
    if not config.ADMIN_TELEGRAM_ID:
        return False
    return user_id == config.ADMIN_TELEGRAM_ID

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    status_emoji = "🟢 ON" if kb.is_auto_answer_enabled else "🔴 OFF"
    manual_emoji = "✋ MANUAL" if kb.get_setting("manual_approval_mode", False) else "⚡ AUTO"
    delay_sec = kb.get_setting("answer_delay", config.ANSWER_DELAY_SECONDS)
    ai_p = kb.get_setting("ai_provider", config.AI_PROVIDER).upper()

    keyboard = [
        [
            InlineKeyboardButton(f"⚡ Auto: {status_emoji}", callback_data="menu_toggle"),
            InlineKeyboardButton(f"Mode: {manual_emoji}", callback_data="toggle_manual")
        ],
        [
            InlineKeyboardButton(f"⏱️ Delay: {delay_sec}s", callback_data="menu_delay_opts"),
            InlineKeyboardButton(f"🤖 AI: {ai_p}", callback_data="menu_ai_opts")
        ],
        [
            InlineKeyboardButton("🎯 Target Bots", callback_data="menu_bots"),
            InlineKeyboardButton("📚 Knowledge Base", callback_data="menu_kb")
        ],
        [
            InlineKeyboardButton("📊 Stats & CSV Export", callback_data="menu_stats"),
            InlineKeyboardButton("📜 Last Quiz", callback_data="menu_last_quiz")
        ],
        [
            InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="menu_refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def notify_admin_quiz_answered(question: str, options: dict, answer_key: str, status: str = "Submitted", bot_username: str = ""):
    """Sends a real-time report to the admin Telegram account when a quiz is answered."""
    if not control_app or not config.ADMIN_TELEGRAM_ID:
        return

    answer_val = options.get(answer_key, "N/A")
    options_text = "\n".join([f"  • {k}: {v}" for k, v in options.items()])
    target_str = f"@{bot_username}" if bot_username else f"@{config.TARGET_QUIZ_BOT}"

    report = (
        "🎯 **Quiz Answered Report**\n\n"
        f"**Target Bot:** `{target_str}`\n"
        f"**Question:**\n{question}\n\n"
        f"**Options:**\n{options_text}\n\n"
        f"**Selected Answer:** `{answer_key}` ({answer_val})\n"
        f"**Status:** {status}"
    )

    try:
        await control_app.send_message(chat_id=config.ADMIN_TELEGRAM_ID, text=report)
    except Exception as e:
        logger.error(f"Failed to send quiz notification to admin: {e}")

async def request_admin_approval(question: str, options: dict, answer_key: str, bot_username: str = "") -> Tuple[bool, str]:
    if not control_app or not config.ADMIN_TELEGRAM_ID:
        logger.warning("Control bot or admin ID missing. Cannot request manual approval. Defaulting to True.")
        return True, answer_key

    req_id = str(uuid.uuid4())[:8]
    event = asyncio.Event()
    pending_approvals[req_id] = event

    options_text = "\n".join([f"  • {k}: {v}" for k, v in options.items()])
    target_str = f"@{bot_username}" if bot_username else f"@{config.TARGET_QUIZ_BOT}"

    buttons = []
    # Button to approve proposed AI answer
    buttons.append([InlineKeyboardButton(f"✅ Approve [{answer_key}] ({options.get(answer_key, '')})", callback_data=f"apprv_yes:{req_id}")])
    # Buttons to pick alternative answer
    alt_row = []
    for k in options.keys():
        if k != answer_key:
            alt_row.append(InlineKeyboardButton(f"Select {k}", callback_data=f"apprv_alt:{req_id}:{k}"))
    if alt_row:
        buttons.append(alt_row)
    buttons.append([InlineKeyboardButton("❌ Reject / Skip", callback_data=f"apprv_no:{req_id}")])

    markup = InlineKeyboardMarkup(buttons)

    msg_text = (
        "❓ **Manual Answer Approval Requested**\n\n"
        f"**Target Bot:** `{target_str}`\n"
        f"**Question:**\n{question}\n\n"
        f"**Options:**\n{options_text}\n\n"
        f"**AI Recommended Answer:** `{answer_key}` ({options.get(answer_key, '')})\n\n"
        "Please approve or reject within 60 seconds."
    )

    try:
        await control_app.send_message(chat_id=config.ADMIN_TELEGRAM_ID, text=msg_text, reply_markup=markup)
    except Exception as e:
        logger.error(f"Failed to send approval request to admin: {e}")
        pending_approvals.pop(req_id, None)
        return True, answer_key

    try:
        await asyncio.wait_for(event.wait(), timeout=60.0)
        is_approved = approval_results.get(req_id, False)
        selected_k = approval_selected_key.get(req_id, answer_key)
        return is_approved, selected_k
    except asyncio.TimeoutError:
        logger.warning(f"Manual approval request {req_id} timed out after 60s.")
        return False, answer_key
    finally:
        pending_approvals.pop(req_id, None)
        approval_results.pop(req_id, None)
        approval_selected_key.pop(req_id, None)

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
            "Welcome! Manage your Telegram Quiz Userbot settings and knowledge base.\n\n"
            "• Upload `.pdf` documents to feed study context.\n"
            "• Send YouTube video URLs to pull transcripts into knowledge base.\n"
            "• Use the buttons below to control settings in real-time."
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

    @app.on_message(filters.command("addbot") & filters.private)
    async def add_bot_command(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("Usage: `/addbot @bot_username`")
            return
        bot_user = parts[1]
        if kb.add_target_bot(bot_user):
            await message.reply_text(f"✅ Added `{bot_user}` to target bots!")
        else:
            await message.reply_text(f"⚠️ `{bot_user}` is already in the target bot list.")

    @app.on_callback_query()
    async def callback_handler(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("Unauthorized", show_alert=True)
            return

        data = callback.data

        # Approval Handlers
        if data.startswith("apprv_"):
            parts = data.split(":")
            action = parts[0]
            req_id = parts[1]

            if req_id in pending_approvals:
                if action == "apprv_yes":
                    approval_results[req_id] = True
                    await callback.answer("✅ Answer Approved!")
                    await callback.message.edit_text(f"✅ **Approved by Admin.** Processing answer submission...")
                elif action == "apprv_alt":
                    alt_key = parts[2]
                    approval_results[req_id] = True
                    approval_selected_key[req_id] = alt_key
                    await callback.answer(f"✅ Selected Alternative Answer [{alt_key}]!")
                    await callback.message.edit_text(f"✅ **Admin selected Option [{alt_key}].** Processing submission...")
                elif action == "apprv_no":
                    approval_results[req_id] = False
                    await callback.answer("❌ Answer Rejected!")
                    await callback.message.edit_text(f"❌ **Rejected by Admin.** Question skipped.")

                evt = pending_approvals.get(req_id)
                if evt:
                    evt.set()
            else:
                await callback.answer("⚠️ Approval request expired or already handled.", show_alert=True)
            return

        # Navigation & Settings Handlers
        if data == "menu_toggle":
            kb.is_auto_answer_enabled = not kb.is_auto_answer_enabled
            kb.save()
            status_str = "ENABLED" if kb.is_auto_answer_enabled else "DISABLED"
            await callback.answer(f"Auto-answering is now {status_str}!")
            await callback.message.edit_reply_markup(reply_markup=get_main_menu_keyboard())

        elif data == "toggle_manual":
            curr = kb.get_setting("manual_approval_mode", False)
            kb.set_setting("manual_approval_mode", not curr)
            mode_str = "MANUAL APPROVAL" if not curr else "AUTOMATIC SUBMISSION"
            await callback.answer(f"Mode switched to {mode_str}!")
            await callback.message.edit_reply_markup(reply_markup=get_main_menu_keyboard())

        elif data == "menu_delay_opts":
            kb_delay = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("0s (Instant)", callback_data="set_delay:0"),
                    InlineKeyboardButton("2s", callback_data="set_delay:2"),
                    InlineKeyboardButton("5s", callback_data="set_delay:5")
                ],
                [
                    InlineKeyboardButton("10s", callback_data="set_delay:10"),
                    InlineKeyboardButton("15s", callback_data="set_delay:15"),
                    InlineKeyboardButton("30s", callback_data="set_delay:30")
                ],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_refresh")]
            ])
            curr = kb.get_setting("answer_delay", config.ANSWER_DELAY_SECONDS)
            await callback.message.edit_text(
                f"⏱️ **Select Answer Delay**\nCurrent delay: `{curr}` seconds\n\nChoose delay duration before userbot submits answer:",
                reply_markup=kb_delay
            )

        elif data.startswith("set_delay:"):
            val = int(data.split(":")[1])
            kb.set_setting("answer_delay", val)
            await callback.answer(f"Delay set to {val} seconds!")
            await callback.message.edit_text(
                f"✅ **Answer Delay updated to {val} seconds!**",
                reply_markup=get_main_menu_keyboard()
            )

        elif data == "menu_ai_opts":
            kb_ai = InlineKeyboardMarkup([
                [InlineKeyboardButton("OpenAI (gpt-4o-mini)", callback_data="set_ai:openai:gpt-4o-mini")],
                [InlineKeyboardButton("OpenAI (gpt-4o)", callback_data="set_ai:openai:gpt-4o")],
                [InlineKeyboardButton("Gemini (gemini-2.5-flash)", callback_data="set_ai:gemini:gemini-2.5-flash")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_refresh")]
            ])
            curr_p = kb.get_setting("ai_provider", config.AI_PROVIDER)
            curr_m = kb.get_setting("ai_model", config.OPENAI_MODEL)
            await callback.message.edit_text(
                f"🤖 **Select AI Provider & Model**\nCurrent: `{curr_p.upper()}` ({curr_m})\n\nSelect desired model:",
                reply_markup=kb_ai
            )

        elif data.startswith("set_ai:"):
            _, prov, model = data.split(":")
            kb.set_setting("ai_provider", prov)
            kb.set_setting("ai_model", model)
            await callback.answer(f"AI set to {prov.upper()} ({model})!")
            await callback.message.edit_text(
                f"✅ **AI Model updated to {prov.upper()} - `{model}`!**",
                reply_markup=get_main_menu_keyboard()
            )

        elif data == "menu_bots":
            bots = kb.get_target_bots()
            bot_list_text = "\n".join([f"• `@{b}`" for b in bots]) if bots else "None"
            kb_bots = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ How to Add Bot", callback_data="bot_info_add")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_refresh")]
            ])
            await callback.message.edit_text(
                f"🎯 **Target Quiz Bots**\n\nCurrently listening to:\n{bot_list_text}\n\nTo add a bot, send command `/addbot @botusername`.",
                reply_markup=kb_bots
            )

        elif data == "bot_info_add":
            await callback.answer("Send command /addbot @username in chat", show_alert=True)

        elif data == "menu_stats":
            total_quizzes = len(kb.quiz_history)
            auto_s = "🟢 ON" if kb.is_auto_answer_enabled else "🔴 OFF"
            man_s = "✋ Manual" if kb.get_setting("manual_approval_mode", False) else "⚡ Auto"
            delay_s = kb.get_setting("answer_delay", config.ANSWER_DELAY_SECONDS)
            ai_s = f"{kb.get_setting('ai_provider', config.AI_PROVIDER).upper()} ({kb.get_setting('ai_model', '')})"

            text = (
                "📊 **Bot Performance & Stats**\n\n"
                f"• **Total Quizzes Answered:** `{total_quizzes}`\n"
                f"• **Auto-Answer:** {auto_s}\n"
                f"• **Submission Mode:** {man_s}\n"
                f"• **Answer Delay:** `{delay_s}s`\n"
                f"• **Active AI Engine:** `{ai_s}`\n"
                f"• **Loaded Study Docs:** `{len(kb.documents)}`"
            )

            kb_stats = InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Export Quiz History (CSV)", callback_data="export_csv")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_refresh")]
            ])
            await callback.message.edit_text(text, reply_markup=kb_stats)

        elif data == "export_csv":
            csv_data = kb.export_quiz_history_csv()
            bio = io.BytesIO(csv_data.encode("utf-8"))
            bio.name = "quiz_history_report.csv"
            await callback.message.reply_document(bio, caption="📥 **Quiz History CSV Export**")
            await callback.answer("CSV exported successfully!")

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
                    f"**Target Bot:** `@{lq.get('bot', '')}`\n"
                    f"**Question:**\n{lq['question']}\n\n"
                    f"**Options:**\n{opts}\n\n"
                    f"**Answer:** `{lq['answer_key']}` ({lq['answer_value']})\n"
                    f"**Status:** {lq['status']}"
                )
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())

        elif data == "menu_refresh":
            text = "🤖 **Quiz Bot Control Dashboard**\n\nSelect an option below or send study files/links:"
            await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
