import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram_bot import is_target_bot, extract_inline_buttons, submit_answer

def test_is_target_bot():
    msg = MagicMock()
    msg.from_user.username = "BirrForexChallengeBot"
    msg.from_user.id = 123456789

    assert is_target_bot(msg, "BirrForexChallengeBot") is True
    assert is_target_bot(msg, "@BirrForexChallengeBot") is True
    assert is_target_bot(msg, "123456789") is True
    assert is_target_bot(msg, "OtherBot") is False

def test_extract_inline_buttons():
    btn1 = MagicMock()
    btn1.text = "A"
    btn2 = MagicMock()
    btn2.text = "B"

    reply_markup = MagicMock()
    reply_markup.inline_keyboard = [[btn1, btn2]]

    buttons = extract_inline_buttons(reply_markup)
    assert buttons == ["A", "B"]

@pytest.mark.asyncio
async def test_submit_answer_button_click():
    client = MagicMock()
    message = MagicMock()
    message.click = AsyncMock()

    btn1 = MagicMock()
    btn1.text = "A"
    btn2 = MagicMock()
    btn2.text = "B"

    message.reply_markup.inline_keyboard = [[btn1, btn2]]

    options = {"A": "Micro Account", "B": "Standard Account"}

    res = await submit_answer(client, message, "A", options)
    assert res is True
    message.click.assert_called_once_with("A")
