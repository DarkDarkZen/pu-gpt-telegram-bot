from telegram import Update
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv
import os
import logging
from handlers.settings import SettingsHandler
from handlers.image_settings import ImageSettingsHandler
from handlers.history import HistoryHandler
from telegram.ext import MessageHandler, filters
from handlers.chat import ChatHandler
import asyncio

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
        self.history_handler = HistoryHandler()
        self.chat_handler = ChatHandler()
        
        self._running = False
        
    async def stop(self):
        """Stop the bot"""
        if self._running:
            await self.application.stop()
            await self.application.shutdown()
            self._running = False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        # Save message to history
        await self.history_handler.save_message(
            update.effective_user.id,
            update.message.text or "(изображение)"
        )
        
        # Handle image generation if message starts with /image
        if update.message.text and update.message.text.startswith('/image '):
            prompt = update.message.text[7:].strip()  # Remove '/image ' prefix
            if prompt:
                update.message.text = prompt  # Set the prompt as message text
                await self.chat_handler.handle_image_generation(update, context)
                return
        
        # Handle regular text messages with streaming response
        if update.message.text:
            await self.chat_handler.stream_openai_response(update, context)
        
        # Handle image variations
        if update.message.photo:
            await self.chat_handler.handle_image_variation(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 Доступные команды:\n\n"
            "/settings - Настройки текстовой модели\n"
            "/image_settings - Настройки генерации изображений\n"
            "/history - История сообщений\n"
            "/clear_history - Очистить историю\n\n"
            "📝 Для генерации текста просто отправьте сообщение\n"
            "🎨 Для генерации изображения используйте команду /image с описанием\n"
            "🖼 Для создания вариации отправьте изображение"
        )
        await update.message.reply_text(help_text)

    def setup_handlers(self):
        """Setup all command and message handlers"""
        from telegram.ext import CommandHandler
        
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Add settings handlers
        self.application.add_handler(self.settings_handler.get_conversation_handler())
        self.application.add_handler(self.image_settings_handler.get_conversation_handler())
        
        # Add history handler
        self.application.add_handler(self.history_handler.get_conversation_handler())
        
        # Add message handler for text and photos
        self.application.add_handler(
            MessageHandler(
                filters.TEXT | filters.PHOTO,
                self.handle_message
            )
        )
        
    def run(self):
        """Run the bot in polling mode"""
        try:
            if not self._running:
                logger.info("Starting bot...")
                self.setup_handlers()
                self._running = True
                self.application.run_polling(allowed_updates=True)
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            self._running = False
        finally:
            asyncio.run(self.stop())

if __name__ == "__main__":
    bot = TelegramBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")
    finally:
        asyncio.run(bot.stop()) 