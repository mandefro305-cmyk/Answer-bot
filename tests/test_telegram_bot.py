import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_bot import is_target_bot, extract_inline_buttons, submit_answer, handle_quiz_message, handle_channel_challenge_trigger

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

def test_extract_inline_buttons_with_non_inline_markup():
    # Test ReplyKeyboardMarkup / ReplyKeyboardRemove without inline_keyboard
    from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
    reply_markup = ReplyKeyboardMarkup([["Option A", "Option B"]])
    buttons = extract_inline_buttons(reply_markup)
    assert buttons == ["Option A", "Option B"]

    remove_markup = ReplyKeyboardRemove()
    buttons_remove = extract_inline_buttons(remove_markup)
    assert buttons_remove == []

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

@pytest.mark.asyncio
async def test_handle_quiz_message_with_delay():
    client = MagicMock()
    message = MagicMock()
    message.from_user.username = "BirrForexChallengeBot"
    message.text = "Question: What is 2+2?\nA) 3\nB) 4\nC) 5\nD) 6"
    message.reply_markup = None
    message.reply_text = AsyncMock()

    with patch("telegram_bot.solve_quiz", return_value="B"), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("telegram_bot.kb.get_setting", return_value=8):

        await handle_quiz_message(client, message)

        mock_sleep.assert_called_once_with(8)
        message.reply_text.assert_called_once_with("B")

@pytest.mark.asyncio
async def test_handle_channel_challenge_trigger():
    client = MagicMock()
    client.send_message = AsyncMock()
    message = MagicMock()
    message.click = AsyncMock()

    btn = MagicMock()
    btn.text = "🚀 JOIN CHALLENGE NOW"
    btn.url = "https://t.me/BirrForexChallengeBot?start=quiz123"

    message.reply_markup.inline_keyboard = [[btn]]

    res = await handle_channel_challenge_trigger(client, message)
    assert res is True
    client.send_message.assert_called_once_with("BirrForexChallengeBot", "/start quiz123")
