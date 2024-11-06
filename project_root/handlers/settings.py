from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils.database import User, UserSettings, init_db
from sqlalchemy.orm import Session
import logging

# States for text model settings conversation
(MAIN_MENU, MODEL_SETTINGS, BASE_URL, MODEL_SELECTION, 
 CUSTOM_MODEL, TEMPERATURE, MAX_TOKENS, ASSISTANT_URL) = range(8)

logger = logging.getLogger(__name__)
Session = init_db()

class SettingsHandler:
    def __init__(self):
        self.available_models = {
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "claude-3-sonnet": "Claude-3 Sonnet"
        }

    async def get_or_create_settings(self, user_id: int) -> UserSettings:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                user = User(telegram_id=user_id)
                session.add(user)
                session.commit()
            
            settings = user.settings
            if not settings:
                settings = UserSettings(user_id=user.id)
                session.add(settings)
                session.commit()
            return settings

    async def settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main settings menu"""
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
            f"🌐 URL: {settings.base_url}\n"
            f"🤖 Модель: {settings.model}\n"
            f"🌡�� Температура: {settings.temperature}\n"
            f"📊 Макс. токенов: {settings.max_tokens}\n"
            f"🔗 Ассистент: {'Включен' if settings.use_assistant else 'Выключен'}"
        )
        
        if isinstance(update, Update):
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.edit_message_text(text, reply_markup=reply_markup)
        return MAIN_MENU

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
            await update.message.reply_text("⚠️ Пожалуйста, введите целое число")
            return MAX_TOKENS

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

    async def handle_custom_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom model input"""
        model_name = update.message.text
        
        with Session() as session:
            settings = await self.get_or_create_settings(update.effective_user.id)
            settings.model = model_name
            session.commit()
        
        await update.message.reply_text(f"✅ Модель установлена: {model_name}")
        return await self.settings_menu(update, context)

    def get_conversation_handler(self):
        """Return conversation handler for settings"""
        return ConversationHandler(
            entry_points=[CommandHandler('settings', self.settings_menu)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.model_selection, pattern="^select_model$"),
                    CallbackQueryHandler(self.temperature_selection, pattern="^edit_temperature$"),
                    CallbackQueryHandler(lambda u, c: u.message.reply_text(
                        "Введите новый Base URL:"), pattern="^edit_base_url$"),
                    CallbackQueryHandler(lambda u, c: u.message.reply_text(
                        "Введите максимальное количество токенов (минимум 150):"), 
                        pattern="^edit_max_tokens$"),
                    CallbackQueryHandler(lambda u, c: u.message.reply_text(
                        "Введите URL ассистента:"), pattern="^edit_assistant_url$"),
                ],
                MODEL_SELECTION: [
                    CallbackQueryHandler(self.handle_model_selection, pattern="^model_"),
                    CallbackQueryHandler(lambda u, c: u.message.reply_text(
                        "Введите название модели:"), pattern="^custom_model$"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                TEMPERATURE: [
                    CallbackQueryHandler(self.handle_temperature, pattern="^temp_"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                BASE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_base_url)],
                MAX_TOKENS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_max_tokens)],
                ASSISTANT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_assistant_url)],
                CUSTOM_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_model)],
            },
            fallbacks=[CallbackQueryHandler(self.settings_menu, pattern="^close$")],
        )