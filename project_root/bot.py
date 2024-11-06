from telegram.ext import Application
from dotenv import load_dotenv
import os
import logging
from handlers.settings import SettingsHandler
from handlers.image_settings import ImageSettingsHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN not found in environment variables")
            
        self.application = Application.builder().token(self.token).build()
        
        # Initialize handlers
        self.settings_handler = SettingsHandler()
        self.image_settings_handler = ImageSettingsHandler()
        
    async def start(self, update, context):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Здравствуйте! Я GPT бот, который может работать с текстом и изображениями.\n\n"
            "Доступные команды:\n"
            "/settings - Настройки текстовой модели\n"
            "/image_settings - Настройки модели изображений\n"
            "/history - История сообщений\n"
            "/clear_history - Очистить историю\n"
            "/help - Помощь"
        )

    def setup_handlers(self):
        """Setup all command and message handlers"""
        from telegram.ext import CommandHandler
        
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        
        # Add settings handlers
        self.application.add_handler(self.settings_handler.get_conversation_handler())
        self.application.add_handler(self.image_settings_handler.get_conversation_handler())
        
    def run(self):
        """Run the bot in polling mode"""
        logger.info("Starting bot...")
        self.setup_handlers()
        self.application.run_polling(allowed_updates=True)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run() 