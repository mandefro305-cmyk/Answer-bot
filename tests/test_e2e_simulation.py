import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram_bot import handle_quiz_message

@pytest.mark.asyncio
async def test_e2e_bot_quiz_flow_full_simulation():
    """
    Simulates receiving a real quiz message from @BirrForexChallengeBot,
    parsing the question, invoking AI solver with fallback handling,
    waiting for delay, and clicking the matching inline keyboard button.
    """
    client = MagicMock()

    message = MagicMock()
    message.from_user.username = "BirrForexChallengeBot"
    message.from_user.id = 987654321
    message.text = "In the section video what is the used currency pair in the example about margin level percentage"
    message.caption = None

    btn_a = MagicMock(text="GBP USD")
    btn_b = MagicMock(text="XAU USD")
    btn_c = MagicMock(text="EUR USD")
    btn_d = MagicMock(text="USD JPY")

    message.reply_markup.inline_keyboard = [
        [btn_a, btn_b],
        [btn_c, btn_d]
    ]
    message.click = AsyncMock()
    message.reply_text = AsyncMock()

    with patch("config.config.TARGET_QUIZ_BOT", "BirrForexChallengeBot"), \
         patch("config.config.ANSWER_DELAY_SECONDS", 5), \
         patch("config.config.AI_PROVIDER", "openai"), \
         patch("config.config.OPENAI_API_KEY", "mock-openai-key"), \
         patch("config.config.GEMINI_API_KEY", "mock-gemini-key"), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("ai_solver._solve_with_openai", side_effect=Exception("Connection error to OpenAI")), \
         patch("ai_solver._solve_with_gemini", return_value="C"):

        await handle_quiz_message(client, message)

        mock_sleep.assert_called_once_with(5)
        message.click.assert_called_once_with("EUR USD")
