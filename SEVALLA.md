# Deploying Telegram Quiz Bot on Sevalla

This guide provides complete, step-by-step instructions for deploying and running this Telegram Quiz AI Userbot 24/7 on [Sevalla](https://sevalla.com/).

---

## Prerequisites

Before starting the deployment, make sure you have:
1. **Telegram API Credentials**: `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` obtained from [my.telegram.org](https://my.telegram.org).
2. **Pyrogram String Session**: Generated locally using `python generate_session.py`.
3. **AI Provider API Key**: Key for OpenAI (`OPENAI_API_KEY`), Google Gemini (`GEMINI_API_KEY`), or Groq (`GROQ_API_KEY`).
4. **Git Repository**: Push this codebase to your GitHub/GitLab account.
5. **Sevalla Account**: An active account on [Sevalla Dashboard](https://sevalla.com/).

---

## Step 1: Create an Application on Sevalla

1. Log in to your **Sevalla Dashboard**.
2. Click **Create Application** or **Add Service** -> **Application**.
3. **Source Code Integration**:
   - Choose **Git Repository** (GitHub / GitLab / Bitbucket).
   - Select your repository and deployment branch (e.g., `main` or `master`).
4. **Build Configuration**:
   - **Recommended**: Select **Dockerfile** as the build method. Sevalla will build using the repository's `Dockerfile`, which includes system packages for PDF processing and OCR (`tesseract-ocr`, `poppler-utils`, `gcc`).
   - Alternatively, if using **Nixpacks/Buildpacks**, the repository includes a `nixpacks.toml` file that automatically instructs Sevalla to install `tesseract-ocr` and `poppler-utils` during setup.
5. **Process Type / Application Resource**:
   - Select **Worker / Background Service** (or set HTTP target port to empty/none).
   - *Note*: This application is a long-running Telegram bot client that operates via WebSockets/MTProto, so it does not require an inbound web port.

---

## Step 2: Configure Environment Variables

In your application's settings on Sevalla, navigate to **Environment Variables** and add the following keys:

### Mandatory Variables
| Variable Name | Description | Example |
|---|---|---|
| `TELEGRAM_API_ID` | Telegram API ID from my.telegram.org | `1234567` |
| `TELEGRAM_API_HASH` | Telegram API Hash from my.telegram.org | `a1b2c3d4e5...` |
| `TELEGRAM_STRING_SESSION` | Pyrogram String Session string | `1BJW...` |
| `TARGET_QUIZ_BOT` | Primary target quiz bot username | `BirrForexChallengeBot` |
| `AI_PROVIDER` | Selected AI provider (`xkiro`, `openai`, `gemini`, or `groq`) | `xkiro` |

### Provider Specific Keys (at least one required based on `AI_PROVIDER`)
| Variable Name | Description | Example |
|---|---|---|
| `XKIRO_API_KEY` | Xkiro API Key | `xkiro_...` |
| `XKIRO_BASE_URL` | Xkiro Base URL (default: `https://api.xkiro.com/v1`) | `https://api.xkiro.com/v1` |
| `XKIRO_MODEL` | Xkiro Model (default: `qwen/qwen3.8-omni-flash:free`) | `qwen/qwen3.8-omni-flash:free` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-proj-...` |
| `OPENAI_MODEL` | OpenAI Model (default: `gpt-4o-mini`) | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | Optional custom base URL or router endpoint | `https://api.openai.com/v1` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini Model (default: `gemini-2.5-flash`) | `gemini-2.5-flash` |
| `GROQ_API_KEY` | Groq API Key | `gsk_...` |
| `GROQ_MODEL` | Groq Model (default: `openai/gpt-oss-120b`) | `openai/gpt-oss-120b` |

### Secondary Control Bot (Optional)
| Variable Name | Description | Example |
|---|---|---|
| `BOT_TOKEN` | Telegram Bot Token for control bot | `123456789:ABC...` |
| `ADMIN_TELEGRAM_ID` | Your personal Telegram user ID | `987654321` |
| `ANSWER_DELAY_SECONDS` | Answer delay in seconds | `5` |

---

## Step 3: Configure Persistent Storage Volume (Optional / Recommended)

The bot stores settings, dynamic target bot configurations, uploaded PDF/YouTube transcripts, and quiz history in `knowledge_base.json`.

By default, cloud containers are stateless and reset when re-deployed. To preserve knowledge base data and history across deployments:

1. In Sevalla Dashboard, go to your Application settings -> **Volumes** / **Persistent Storage**.
2. Click **Add Volume** / **Create Volume**:
   - **Mount Path**: `/app/data`
   - **Volume Size**: 1 GB (or preferred size)
3. Under **Environment Variables**, add:
   - `KNOWLEDGE_BASE_PATH`: `/app/data/knowledge_base.json`
4. Save configuration.

---

## Step 4: Deploy and Verify

1. Click **Deploy Application** in Sevalla.
2. Sevalla will build the Docker container using `Dockerfile` (installing `gcc`, `build-essential`, `poppler-utils`, `tesseract-ocr`, and Python requirements) and launch `python main.py`.
3. Check the **Application Logs** in Sevalla to verify startup:
   ```text
   INFO - main - Starting Telegram Quiz Userbot (Targeting bot: 'BirrForexChallengeBot')...
   INFO - main - All services started successfully. Listening for messages...
   ```
4. If configured with a `BOT_TOKEN`, open your Control Bot in Telegram and send `/start` to verify full remote control functionality!

---

## Troubleshooting

### PDF Upload Error: "tesseract is not installed or it's not in your PATH"
If you receive this error when uploading a PDF to the Knowledge Base via the Control Bot:
1. Ensure your Sevalla Application **Build Method** is set to **Dockerfile**.
2. If using **Nixpacks**, make sure `nixpacks.toml` is present in the root directory of your repository.
3. Trigger a **Re-deploy with clear cache** in the Sevalla Dashboard so the system packages (`tesseract-ocr` and `poppler-utils`) are installed during build.
