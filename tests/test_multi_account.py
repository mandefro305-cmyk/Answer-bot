import pytest
from unittest.mock import MagicMock
from config import Config
from telegram_bot import get_account_label

def test_get_session_strings():
    Config.TELEGRAM_STRING_SESSIONS = "sess1, sess2 , sess3"
    Config.TELEGRAM_STRING_SESSION = ""
    sessions = Config.get_session_strings()
    assert sessions == ["sess1", "sess2", "sess3"]

    Config.TELEGRAM_STRING_SESSIONS = ""
    Config.TELEGRAM_STRING_SESSION = "single_sess"
    sessions = Config.get_session_strings()
    assert sessions == ["single_sess"]

def test_get_account_label():
    client_mock = MagicMock()
    me_mock = MagicMock()
    me_mock.username = "testuser"
    client_mock.me = me_mock
    assert get_account_label(client_mock) == "@testuser"

    me_mock.username = None
    me_mock.first_name = "Alice"
    me_mock.id = 12345
    assert get_account_label(client_mock) == "Alice (12345)"
