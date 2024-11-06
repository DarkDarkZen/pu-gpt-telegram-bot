from telegram import Update
from telegram.ext import Application
import json
import sys
import os

# Add parent directory to path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import GPTBot

# Initialize bot
bot = GPTBot()

async def webhook(request):
    """Handle webhook requests from Telegram"""
    try:
        # Parse update
        update = Update.de_json(json.loads(request.body), bot.application.bot)
        
        # Process update
        await bot.application.process_update(update)
        
        return {"statusCode": 200, "body": "ok"}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}

# Vercel serverless function handler
async def handler(request):
    if request.method == "POST":
        return await webhook(request)
    return {"statusCode": 405, "body": "Method not allowed"} 