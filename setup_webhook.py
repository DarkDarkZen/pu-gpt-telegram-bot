import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def setup_webhook():
    """Set up webhook for Telegram bot"""
    try:
        # Get configuration
        bot_token = os.getenv("TELEGRAM_TOKEN")
        webhook_url = os.getenv("WEBHOOK_URL")
        
        if not bot_token:
            raise ValueError("TELEGRAM_TOKEN is not set")
        if not webhook_url:
            raise ValueError("WEBHOOK_URL is not set")
            
        # Initialize bot
        bot = Bot(token=bot_token)
        
        # Delete any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Set new webhook
        webhook_info = await bot.set_webhook(
            url=f"{webhook_url}/api/webhook",
            allowed_updates=["message", "callback_query"]
        )
        
        if webhook_info:
            print(f"✅ Webhook set successfully to {webhook_url}/api/webhook")
        else:
            print("❌ Failed to set webhook")
            
        # Get and print webhook info
        info = await bot.get_webhook_info()
        print("\nWebhook Info:")
        print(f"URL: {info.url}")
        print(f"Pending updates: {info.pending_update_count}")
        print(f"Last error: {info.last_error}")
        
    except Exception as e:
        print(f"❌ Error setting up webhook: {e}")

if __name__ == "__main__":
    asyncio.run(setup_webhook()) 