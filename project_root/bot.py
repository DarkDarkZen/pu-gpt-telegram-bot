from telegram import Update
from telegram.ext import Application, ContextTypes, PicklePersistence
from dotenv import load_dotenv
import os
import logging
from handlers.settings import SettingsHandler
from handlers.image_settings import ImageSettingsHandler
from handlers.history import HistoryHandler
from telegram.ext import MessageHandler, filters
from handlers.chat import ChatHandler
import asyncio
from utils.logging_config import setup_logging, log_function_call, DEBUG_MODE
import json
from pathlib import Path

# Set up logging directory
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
# Initialize logging
logger = setup_logging(__name__, os.path.join(LOGS_DIR, 'bot.log'))

class TelegramBot:
    def __init__(self):
        logger.debug("Initializing TelegramBot")
        
        try:
            # Create logs directory if it doesn't exist
            os.makedirs(LOGS_DIR, exist_ok=True)
            # Create data directory for persistence
            os.makedirs('data', exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create directories: {e}")
        
        load_dotenv()
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN not found in environment variables")
        
        # Initialize persistence
        persistence = PicklePersistence(
            filepath="data/conversation_data",
            update_interval=30  # Save every 30 seconds
        )
            
        self.application = (
            Application.builder()
            .token(self.token)
            .persistence(persistence)
            .build()
        )
        
        # Initialize handlers
        self.settings_handler = SettingsHandler()
        self.image_settings_handler = ImageSettingsHandler()
        self.history_handler = HistoryHandler()
        self.chat_handler = ChatHandler()
        
        self._running = False
        self._offset = None
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(
            "Exception while handling an update:",
            exc_info=context.error if DEBUG_MODE else False
        )
        
        # Log update object in debug mode
        if DEBUG_MODE:
            logger.debug(f"Update object: {update}")
            logger.debug(f"Context error: {context.error}")
        
        # Send message to user
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )
    
    async def stop(self):
        """Stop the bot"""
        if self._running:
            logger.info("Stopping bot...")
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
            finally:
                self._running = False
                logger.info("Bot stopped")
    
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

    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /debug command - only works in debug mode"""
        if not DEBUG_MODE:
            await update.message.reply_text("Debug mode is disabled")
            return
        
        user_id = update.effective_user.id
        logger.debug(f"Debug command called by user {user_id}")
        
        debug_info = {
            "user_id": user_id,
            "chat_id": update.effective_chat.id,
            "bot_info": await context.bot.get_me(),
            "update_id": update.update_id,
        }
        
        await update.message.reply_text(
            f"Debug information:\n{json.dumps(debug_info, indent=2)}"
        )

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
        
        if DEBUG_MODE:
            self.application.add_handler(CommandHandler("debug", self.debug_command))
        
    def run(self):
        """Run the bot in polling mode"""
        try:
            if not self._running:
                logger.info("Starting bot...")
                self.setup_handlers()
                self._running = True
                self.application.run_polling(
                    allowed_updates=True,
                    drop_pending_updates=True,
                    close_loop=False
                )
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