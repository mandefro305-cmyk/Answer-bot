import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from control_bot import is_admin, notify_admin_quiz_answered, get_main_menu_keyboard

def test_is_admin():
    with patch("config.config.ADMIN_TELEGRAM_ID", 123456789):
        assert is_admin(123456789) is True
        assert is_admin(999999999) is False

def test_get_main_menu_keyboard():
    keyboard = get_main_menu_keyboard()
    assert keyboard is not None
    assert len(keyboard.inline_keyboard) >= 4

@pytest.mark.asyncio
async def test_notify_admin_quiz_answered():
    mock_app = AsyncMock()
    with patch("control_bot.control_app", mock_app), \
         patch("config.config.ADMIN_TELEGRAM_ID", 123456789):

        await notify_admin_quiz_answered("What is leverage?", {"A": "1:100", "B": "1:1"}, "A", "Submitted", bot_username="TestBot")

        mock_app.send_message.assert_called_once()
        call_kwargs = mock_app.send_message.call_args[1]
        assert call_kwargs["chat_id"] == 123456789
        assert "What is leverage?" in call_kwargs["text"]
        assert "`A` (1:100)" in call_kwargs["text"]
        assert "@TestBot" in call_kwargs["text"]
