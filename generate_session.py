#!/usr/bin/env python3
"""
Utility script to generate Pyrogram String Session for Telegram Userbot.
Run this script locally to log in to Telegram and get TELEGRAM_STRING_SESSION for Railway / remote deployment.
"""
import asyncio
from pyrogram import Client

async def generate():
    print("=== Pyrogram String Session Generator ===")
    api_id_str = input("Enter TELEGRAM_API_ID: ").strip()
    api_hash = input("Enter TELEGRAM_API_HASH: ").strip()

    if not api_id_str or not api_hash:
        print("API ID and API Hash are required!")
        return

    api_id = int(api_id_str)

    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        session_str = await app.export_session_string()
        print("\n=== YOUR STRING SESSION (Copy & Keep Secret) ===")
        print(session_str)
        print("================================================\n")
        print("Set TELEGRAM_STRING_SESSION in your Railway / .env environment variables.")

if __name__ == "__main__":
    asyncio.run(generate())
