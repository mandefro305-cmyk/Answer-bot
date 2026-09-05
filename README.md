# Telegram Quiz AI Bot

An automated Telegram Userbot program that listens for multiple-choice quiz questions sent by a specified Telegram Quiz Bot (e.g., `@BirrForexChallengeBot`), uses OpenAI or Google Gemini API to analyze and determine the correct option, and automatically submits the answer (via inline button press or text reply).

## Features

- **Automated Quiz Detection**: Listens to questions and option choices (A/B/C/D) from Telegram quiz bots.
- **Dual AI Engine Support**: Seamlessly switch between OpenAI (`gpt-4o-mini`) and Google Gemini (`gemini-2.5-flash`).
- **Flexible Answer Submission**: Clicks corresponding inline keyboard buttons or sends text replies automatically.
- **Railway Deployment Ready**: Designed for 24/7 headless operation on Railway using Pyrogram String Sessions.

---

## Setup & Local Usage

### 1. Prerequisites
- Python 3.10+
- Telegram `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- API Key for OpenAI or Google Gemini

### 2. Installation
```bash
git clone <your-repo-url>
cd telegram-quiz-bot
pip install -r requirements.txt
```

### 3. Generate Pyrogram String Session
To run headlessly on Railway (or cloud platforms), generate a Pyrogram session string:
```bash
python generate_session.py
```
Follow the prompts to enter your phone number and login code. Copy the generated `TELEGRAM_STRING_SESSION`.

### 4. Configuration
Create a `.env` file based on `.env.example`:
```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_STRING_SESSION=your_session_string
TARGET_QUIZ_BOT=BirrForexChallengeBot

# AI Provider: "openai" or "gemini"
AI_PROVIDER=openai

# OpenAI Settings
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Gemini Settings (if AI_PROVIDER=gemini)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

### 5. Run Locally
```bash
python main.py
```

---

## Deploying on Railway

1. Push your repository to GitHub.
2. Go to [Railway.app](https://railway.app) and create a **New Project** -> **Deploy from GitHub repo**.
3. In your Railway service settings, navigate to **Variables** and set the environment variables from your `.env` file:
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`
   - `TELEGRAM_STRING_SESSION`
   - `TARGET_QUIZ_BOT`
   - `AI_PROVIDER` (`openai` or `gemini`)
   - `OPENAI_API_KEY` or `GEMINI_API_KEY`
4. Deploy! Railway will build using the `Dockerfile` / `railway.json` configuration.

---

## Testing

Run unit tests with pytest:
```bash
PYTHONPATH=. pytest
```
