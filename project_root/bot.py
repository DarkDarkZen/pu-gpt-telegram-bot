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
        
        # Load environment variables
        if os.path.exists('.env'):
            logger.debug("Loading .env file")
            load_dotenv()
        else:
            logger.debug("No .env file found, using system environment variables")
        
        # Debug: Print all environment variables (excluding sensitive data)
        env_vars = {k: '***' if 'TOKEN' in k or 'KEY' in k else v for k, v in os.environ.items()}
        logger.debug(f"Environment variables: {env_vars}")
        
        # Try both possible environment variable names
        self.token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            logger.error("Telegram bot token not found in environment variables")
            logger.debug(f"Available environment variables: {list(os.environ.keys())}")
            raise ValueError(
                "Telegram bot token not found in environment variables. "
                "Please set either TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN in your Railway.app environment variables "
                "or .env file."
            )
        else:
            logger.debug("Telegram bot token found")
        
        try:
            # Initialize persistence with Railway-friendly path
            persistence_path = os.path.join(os.getcwd(), 'data', 'conversation_data')
            logger.debug(f"Setting persistence path to: {persistence_path}")
            persistence = PicklePersistence(
                filepath=persistence_path,
                update_interval=30
            )
            
            self.application = (
                Application.builder()
                .token(self.token)
                .persistence(persistence)
                .concurrent_updates(True)
                .build()
            )
            logger.debug("Application built successfully")
            
            # Initialize job queue
            self.application.job_queue.scheduler.start()
            logger.debug("Job queue initialized")
            
            # Initialize handlers
            self.history_handler = HistoryHandler()
            self.settings_handler = SettingsHandler()
            self.image_settings_handler = ImageSettingsHandler()
            self.chat_handler = ChatHandler(history_handler=self.history_handler)
            logger.debug("All handlers initialized")
            
            self._running = False
            self._offset = None
            
            # Add error handler
            self.application.add_error_handler(self.error_handler)
            logger.debug("Error handler added")
            
        except Exception as e:
            logger.error(f"Error during bot initialization: {str(e)}", exc_info=True)
            raise
    
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
                # Stop job queue
                if self.application.job_queue:
                    self.application.job_queue.scheduler.shutdown(wait=True)
                # Stop application
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
        logger.debug(f"Received message: {update.message.text}")
        
        # Check if message exists
        if not update.message:
            return

        # Get bot's username and message text
        bot_username = context.bot.username
        message_text = update.message.text if update.message.text else ""

        # Check if message is meant for bot in group chats
        if update.effective_chat.type not in ["private", "channel"]:
            # Check if message mentions the bot
            is_for_bot = False
            
            # Check for direct mention at start
            if message_text.startswith(f"@{bot_username}"):
                is_for_bot = True
                message_text = message_text.replace(f"@{bot_username}", "", 1).strip()
            
            # Check for mentions in entities
            elif update.message.entities:
                for entity in update.message.entities:
                    if entity.type == "mention":
                        mention = message_text[entity.offset:entity.offset + entity.length]
                        if mention == f"@{bot_username}":
                            is_for_bot = True
                            message_text = message_text.replace(mention, "").strip()
                            break
            
            # If message is not for this bot, ignore it
            if not is_for_bot:
                return
        
        try:
            # Save user message to history
            await self.history_handler.save_message(
                update.effective_user.id,
                message_text or "(изображение)",
                role='user'
            )
            
            # If message is a reply to bot's message and contains an image
            if (update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id):
                if update.message.photo:
                    # Handle image variation request
                    await self.chat_handler.handle_image_variation(update, context)
                    return
                elif update.message.reply_to_message.photo:
                    # Handle combined image and text generation
                    await self.chat_handler.handle_combined_image_generation(update, context)
                    return
            
            # Handle image generation if message starts with /image
            if message_text and message_text.startswith('/image '):
                prompt = message_text[7:].strip()  # Remove '/image ' prefix
                if prompt:
                    context.user_data['image_prompt'] = prompt
                    await self.chat_handler.handle_image_generation(update, context)
                    return
            
            # If message contains an image
            if update.message.photo:
                # Store the prompt in context for image generation
                context.user_data['image_prompt'] = update.message.caption or "Generate an image variation"
                await self.chat_handler.handle_image_variation(update, context)
                return
            
            # Store the processed text in context
            context.user_data['processed_text'] = message_text
            
            # Handle text messages with streaming response
            await self.chat_handler.stream_openai_response(update, context)
            
        except Exception as e:
            error_message = f"❌ Произошла ошибка: {str(e)}"
            logger.error(error_message)
            await update.message.reply_text(error_message)

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