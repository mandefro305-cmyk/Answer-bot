import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class ParsedQuiz:
    question: str
    options: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

def parse_quiz(text: str, inline_buttons: Optional[List[str]] = None) -> Optional[ParsedQuiz]:
    """
    Parses a Telegram message text and optional inline button labels to extract
    question text and A/B/C/D options.
    """
    if not text and not inline_buttons:
        return None

    lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
    question_lines = []
    options = {}

    # Option pattern for text lines: e.g. "A) Option text", "A. Option text", "(A) Option text", "A: Option text"
    option_pattern = re.compile(r'^(?:\(?([A-D])[\)\.\:\-]|Option\s+([A-D])[\)\.\:]?)\s*(.+)$', re.IGNORECASE)

    for line in lines:
        match = option_pattern.match(line)
        if match:
            key = (match.group(1) or match.group(2)).upper()
            val = match.group(3).strip()
            options[key] = val
        else:
            # Skip headers like "Question 2/5 ⏱️" or keep relevant question text
            question_lines.append(line)

    # Clean question text (remove standard question counter line if present at top)
    filtered_q_lines = []
    for q_line in question_lines:
        if re.match(r'^Question\s+\d+/\d+', q_line, re.IGNORECASE):
            continue
        filtered_q_lines.append(q_line)

    question_text = " ".join(filtered_q_lines).strip()

    # If options were not found in message text, check inline button labels
    if not options and inline_buttons:
        button_pattern = re.compile(r'^(?:\(?([A-D])[\)\.\:\-]|Option\s+([A-D])[\)\.\:]?)\s*(.+)$', re.IGNORECASE)
        single_letter_pattern = re.compile(r'^([A-D])$', re.IGNORECASE)

        for btn_text in inline_buttons:
            btn_text_clean = btn_text.strip()
            match = button_pattern.match(btn_text_clean)
            if match:
                key = (match.group(1) or match.group(2)).upper()
                val = match.group(3).strip()
                options[key] = val
            else:
                single_match = single_letter_pattern.match(btn_text_clean)
                if single_match:
                    key = single_match.group(1).upper()
                    options[key] = key  # Standalone letter option

    if not question_text or not options:
        return None

    return ParsedQuiz(
        question=question_text,
        options=options,
        raw_text=text or ""
    )
