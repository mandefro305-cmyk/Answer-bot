from parser import parse_quiz
from ai_solver import _extract_option_key

def test_parser_standard():
    text = """Question 2/5 ⏱️

In which account type can you trade less than 1,000 units of a currency?

A) Micro Account
B) Standard Account
C) Pro Account
D) You cannot trade less than 1,000 units"""

    parsed = parse_quiz(text)
    assert parsed is not None
    assert "In which account type can you trade" in parsed.question
    assert parsed.options == {
        "A": "Micro Account",
        "B": "Standard Account",
        "C": "Pro Account",
        "D": "You cannot trade less than 1,000 units"
    }

def test_parser_with_inline_buttons():
    text = """Question 5/5 ⏱️

Which order type was specified in the section video as the newer order type useful in placing order for Volatile Asset?"""
    inline_buttons = ["A) Stop limit", "B) Stop", "C) Trailing", "D) Limit"]

    parsed = parse_quiz(text, inline_buttons=inline_buttons)
    assert parsed is not None
    assert "Which order type was specified" in parsed.question
    assert parsed.options == {
        "A": "Stop limit",
        "B": "Stop",
        "C": "Trailing",
        "D": "Limit"
    }

def test_extract_option_key():
    assert _extract_option_key("A", ["A", "B", "C", "D"]) == "A"
    assert _extract_option_key("Option B", ["A", "B", "C", "D"]) == "B"
    assert _extract_option_key("The correct answer is C.", ["A", "B", "C", "D"]) == "C"
