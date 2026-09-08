import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_bot import is_target_bot, handle_quiz_message
from knowledge_base import KnowledgeBase
from control_bot import request_admin_approval, pending_approvals, approval_results, approval_selected_key

@pytest.fixture
def temp_kb(tmp_path):
    file_path = str(tmp_path / "test_kb_multi.json")
    return KnowledgeBase(storage_path=file_path)

def test_multi_target_bots(temp_kb):
    temp_kb.add_target_bot("@BotOne")
    temp_kb.add_target_bot("BotTwo")

    msg1 = MagicMock()
    msg1.from_user.username = "BotOne"
    msg1.from_user.id = 100

    msg2 = MagicMock()
    msg2.from_user.username = "BotTwo"
    msg2.from_user.id = 200

    msg3 = MagicMock()
    msg3.from_user.username = "BotThree"
    msg3.from_user.id = 300

    with patch("telegram_bot.kb", temp_kb):
        assert is_target_bot(msg1) is True
        assert is_target_bot(msg2) is True
        assert is_target_bot(msg3) is False

@pytest.mark.asyncio
async def test_manual_approval_granted():
    mock_app = AsyncMock()
    with patch("control_bot.control_app", mock_app), \
         patch("config.config.ADMIN_TELEGRAM_ID", 123456):

        async def simulate_admin_click():
            await asyncio.sleep(0.05)
            # Find the req_id from pending_approvals
            req_id = list(pending_approvals.keys())[0]
            approval_results[req_id] = True
            evt = pending_approvals[req_id]
            evt.set()

        asyncio.create_task(simulate_admin_click())

        approved, key = await request_admin_approval(
            "What is 1+1?",
            {"A": "1", "B": "2"},
            "B",
            bot_username="TestBot"
        )

        assert approved is True
        assert key == "B"
        mock_app.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_manual_approval_rejected():
    mock_app = AsyncMock()
    with patch("control_bot.control_app", mock_app), \
         patch("config.config.ADMIN_TELEGRAM_ID", 123456):

        async def simulate_admin_reject():
            await asyncio.sleep(0.05)
            req_id = list(pending_approvals.keys())[0]
            approval_results[req_id] = False
            evt = pending_approvals[req_id]
            evt.set()

        asyncio.create_task(simulate_admin_reject())

        approved, key = await request_admin_approval(
            "What is 1+1?",
            {"A": "1", "B": "2"},
            "B",
            bot_username="TestBot"
        )

        assert approved is False
