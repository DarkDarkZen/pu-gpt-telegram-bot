from telegram import Update
from telegram.ext import Application
import json
import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add parent directory to path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import GPTBot
from config import config

# Initialize FastAPI app
app = FastAPI()

# Initialize bot
bot = GPTBot()

@app.post(f"/api/webhook")
async def telegram_webhook(request: Request):
    """Handle webhook requests from Telegram"""
    try:
        # Get request body
        data = await request.json()
        
        # Parse update
        update = Update.de_json(data, bot.application.bot)
        
        # Process update
        await bot.application.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"} 