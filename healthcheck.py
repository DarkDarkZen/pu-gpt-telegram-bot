import requests
import os
from dotenv import load_dotenv

load_dotenv()

def check_bot_status():
    """Check if bot is responding to Telegram API"""
    bot_token = os.getenv("TELEGRAM_TOKEN")
    if not bot_token:
        return False
        
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe"
        )
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    if check_bot_status():
        print("Bot is healthy")
        exit(0)
    else:
        print("Bot is not responding")
        exit(1) 