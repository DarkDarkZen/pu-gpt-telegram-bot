from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils.database import User, UserSettings, init_db
from sqlalchemy.orm import Session
import logging
from utils.logging_config import setup_logging, log_function_call
import os

# States for text model settings conversation
(MAIN_MENU, MODEL_SETTINGS, BASE_URL, MODEL_SELECTION, 
 CUSTOM_MODEL, TEMPERATURE, MAX_TOKENS, ASSISTANT_URL) = range(8)

# Initialize logging
logger = setup_logging(__name__, 'settings.log')
Session = init_db()

class SettingsHandler:
    def __init__(self):
        logger.debug("Initializing SettingsHandler")
        self.available_models = {
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "claude-3-sonnet": "Claude-3 Sonnet"
        }

    @log_function_call(logger)
    async def get_or_create_settings(self, user_id: int) -> dict:
        """Get or create user settings"""
        try:
            with Session() as session:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    user = User(telegram_id=user_id)
                    session.add(user)
                    session.commit()
                
                settings = session.query(UserSettings).filter_by(user_id=user.id).first()
                if not settings:
                    settings = UserSettings(user_id=user.id)
                    session.add(settings)
                    session.commit()
                
                # Refresh the session to ensure all attributes are loaded
                session.refresh(settings)
                
                # Create a dictionary of settings values
                settings_dict = {
                    'base_url': settings.base_url,
                    'model': settings.model,
                    'temperature': settings.temperature,
                    'max_tokens': settings.max_tokens,
                    'use_assistant': settings.use_assistant,
                    'assistant_url': settings.assistant_url
                }
                logger.debug(f"Settings for user {user_id}: {settings_dict}")
                return settings_dict
        except Exception as e:
            logger.error(f"Error getting settings for user {user_id}: {e}", exc_info=True)
            raise

    @log_function_call(logger)
    async def settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main settings menu"""
        user_id = update.effective_user.id
        logger.info(f"Showing settings menu for user {user_id}")
        keyboard = [
            [InlineKeyboardButton("📝 Базовый URL", callback_data="edit_base_url")],
            [InlineKeyboardButton("🤖 Выбор модели", callback_data="select_model")],
            [InlineKeyboardButton("🌡️ Температура", callback_data="edit_temperature")],
            [InlineKeyboardButton("📊 Макс. токенов", callback_data="edit_max_tokens")],
            [InlineKeyboardButton("🔗 URL ассистента", callback_data="edit_assistant_url")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings = await self.get_or_create_settings(update.effective_user.id)
        text = (
            "⚙️ Текущие настройки:\n\n"
            f"🌐 URL: {settings['base_url']}\n"
            f"🤖 Модель: {settings['model']}\n"
            f"🌡 Температура: {settings['temperature']}\n"
            f"📊 Макс. токенов: {settings['max_tokens']}\n"
            f"🔗 Ассистент: {'Включен' if settings['use_assistant'] else 'Выключен'}"
        )
        
        if isinstance(update, Update):
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.edit_message_text(text, reply_markup=reply_markup)
        return MAIN_MENU

    @log_function_call(logger)
    async def model_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show model selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for model_id, model_name in self.available_models.items():
            keyboard.append([InlineKeyboardButton(model_name, callback_data=f"model_{model_id}")])
        
        keyboard.append([InlineKeyboardButton("✏️ Своя модель", callback_data="custom_model")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите модель:", reply_markup=reply_markup)
        return MODEL_SELECTION

    @log_function_call(logger)
    async def handle_model_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle model selection"""
        query = update.callback_query
        await query.answer()
        
        model = query.data.replace("model_", "")
        with Session() as session:
            settings = await self.get_or_create_settings(query.from_user.id)
            settings.model = model
            session.commit()
        
        return await self.settings_menu(query, context)

    @log_function_call(logger)
    async def temperature_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show temperature selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for i in range(0, 11, 2):
            temp = i / 10
            keyboard.append([InlineKeyboardButton(f"🌡️ {temp}", callback_data=f"temp_{temp}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите температуру (0 - более точно, 1 - более креативно):",
            reply_markup=reply_markup
        )
        return TEMPERATURE

    @log_function_call(logger)
    async def handle_base_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle base URL input"""
        user_id = update.effective_user.id
        new_url = update.message.text
        
        with Session() as session:
            settings = await self.get_or_create_settings(user_id)
            settings.base_url = new_url
            session.commit()
        
        await update.message.reply_text(f"✅ Base URL обновлен на: {new_url}")
        return await self.settings_menu(update, context)

    @log_function_call(logger)
    async def handle_temperature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle temperature selection"""
        query = update.callback_query
        await query.answer()
        
        temp = float(query.data.replace("temp_", ""))
        with Session() as session:
            settings = await self.get_or_create_settings(query.from_user.id)
            settings.temperature = temp
            session.commit()
        
        return await self.settings_menu(query, context)

    @log_function_call(logger)
    async def handle_max_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle max tokens input"""
        try:
            tokens = int(update.message.text)
            if tokens < 150:
                await update.message.reply_text("⚠️ Минимальное значение токенов: 150")
                return MAX_TOKENS
            
            with Session() as session:
                settings = await self.get_or_create_settings(update.effective_user.id)
                settings.max_tokens = tokens
                session.commit()
            
            await update.message.reply_text(f"✅ Максимальное количество токенов установлено: {tokens}")
            return await self.settings_menu(update, context)
        except ValueError:
            await update.message.reply_text("⚠️ Пожалуйста, вв��дите целое число")
            return MAX_TOKENS

    @log_function_call(logger)
    async def handle_assistant_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI assistant URL input"""
        user_id = update.effective_user.id
        assistant_url = update.message.text
        
        with Session() as session:
            settings = await self.get_or_create_settings(user_id)
            settings.assistant_url = assistant_url
            settings.use_assistant = True
            session.commit()
        
        await update.message.reply_text(f"✅ URL ассистента установлен: {assistant_url}")
        return await self.settings_menu(update, context)

    @log_function_call(logger)
    async def handle_custom_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom model input"""
        model_name = update.message.text
        
        with Session() as session:
            settings = await self.get_or_create_settings(update.effective_user.id)
            settings.model = model_name
            session.commit()
        
        await update.message.reply_text(f"✅ Модель установлена: {model_name}")
        return await self.settings_menu(update, context)

    @log_function_call(logger)
    async def handle_base_url_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start base URL input process"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Введите новый Base URL:")
        return BASE_URL

    @log_function_call(logger)
    async def handle_max_tokens_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start max tokens input process"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Введите максимальное количество токенов (минимум 150):")
        return MAX_TOKENS

    @log_function_call(logger)
    async def handle_assistant_url_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start assistant URL input process"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Введите URL ассистента:")
        return ASSISTANT_URL

    @log_function_call(logger)
    async def handle_custom_model_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start custom model input process"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Введите название модели:")
        return CUSTOM_MODEL

    @log_function_call(logger)
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("❌ Настройка отменена")
        else:
            await update.message.reply_text("❌ Настройка отменена")
        return ConversationHandler.END

    def get_conversation_handler(self):
        """Return conversation handler for settings"""
        return ConversationHandler(
            entry_points=[CommandHandler('settings', self.settings_menu)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.model_selection, pattern="^select_model$"),
                    CallbackQueryHandler(self.temperature_selection, pattern="^edit_temperature$"),
                    CallbackQueryHandler(self.handle_base_url_start, pattern="^edit_base_url$"),
                    CallbackQueryHandler(self.handle_max_tokens_start, pattern="^edit_max_tokens$"),
                    CallbackQueryHandler(self.handle_assistant_url_start, pattern="^edit_assistant_url$"),
                ],
                MODEL_SELECTION: [
                    CallbackQueryHandler(self.handle_model_selection, pattern="^model_"),
                    CallbackQueryHandler(self.handle_custom_model_start, pattern="^custom_model$"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                TEMPERATURE: [
                    CallbackQueryHandler(self.handle_temperature, pattern="^temp_"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                BASE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_base_url),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                MAX_TOKENS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_max_tokens),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                ASSISTANT_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_assistant_url),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                CUSTOM_MODEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_model),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.settings_menu, pattern="^close$"),
                CommandHandler('cancel', self.cancel),
            ],
            allow_reentry=True,
            name="settings_conversation"
        )