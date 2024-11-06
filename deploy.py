from telegram import Bot
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def set_webhook():
    """Set webhook for Telegram bot"""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    webhook_url = os.getenv("WEBHOOK_URL")
    
    # Remove existing webhook
    await bot.delete_webhook()
    
    # Set new webhook
    success = await bot.set_webhook(webhook_url)
    if success:
        print(f"Webhook set successfully to {webhook_url}")
    else:
        print("Failed to set webhook")

if __name__ == "__main__":
    asyncio.run(set_webhook()) 