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
            f"🌡️ Температура: {settings.temperature}\n"
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

    def get_conversation_handler(self):
        """Return conversation handler for settings"""
        return ConversationHandler(
            entry_points=[CommandHandler('settings', self.settings_menu)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.model_selection, pattern="^select_model$"),
                    CallbackQueryHandler(self.temperature_selection, pattern="^edit_temperature$"),
                    # Add other menu handlers
                ],
                MODEL_SELECTION: [
                    CallbackQueryHandler(self.handle_model_selection, pattern="^model_"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
                TEMPERATURE: [
                    CallbackQueryHandler(self.handle_temperature, pattern="^temp_"),
                    CallbackQueryHandler(self.settings_menu, pattern="^back_to_menu$"),
                ],
            },
            fallbacks=[CallbackQueryHandler(self.settings_menu, pattern="^close$")],
        ) 