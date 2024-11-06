from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
from utils.database import User, ImageSettings, init_db
from sqlalchemy.orm import Session
import logging

# States for image settings conversation
(IMAGE_MAIN_MENU, IMAGE_BASE_URL, IMAGE_MODEL, 
 IMAGE_SIZE, IMAGE_QUALITY, IMAGE_STYLE) = range(6)

logger = logging.getLogger(__name__)
Session = init_db()

class ImageSettingsHandler:
    def __init__(self):
        self.available_models = {
            "dall-e-3": "DALL-E 3",
            "dall-e-2": "DALL-E 2",
            "stable-diffusion-xl": "Stable Diffusion XL",
            "midjourney": "Midjourney API"
        }
        
        self.size_options = {
            "1024x1024": "1024x1024 (Квадрат)",
            "1792x1024": "1792x1024 (Широкий)",
            "1024x1792": "1024x1792 (Высокий)",
        }
        
        self.quality_options = {
            "standard": "Стандартное",
            "hd": "Высокое (HD)"
        }
        
        self.style_options = {
            "natural": "Натуральный",
            "vivid": "Яркий",
            "anime": "Аниме"
        }

    async def get_or_create_settings(self, user_id: int) -> ImageSettings:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                user = User(telegram_id=user_id)
                session.add(user)
                session.commit()
            
            settings = user.image_settings
            if not settings:
                settings = ImageSettings(user_id=user.id)
                session.add(settings)
                session.commit()
            return settings

    async def image_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main image settings menu"""
        keyboard = [
            [InlineKeyboardButton("🌐 Базовый URL", callback_data="edit_image_base_url")],
            [InlineKeyboardButton("🎨 Модель", callback_data="select_image_model")],
            [InlineKeyboardButton("📐 Размер", callback_data="select_image_size")],
            [InlineKeyboardButton("✨ Качество", callback_data="select_image_quality")],
            [InlineKeyboardButton("🎭 Стиль", callback_data="select_image_style")],
            [InlineKeyboardButton("HDR", callback_data="toggle_hdr")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close_image_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings = await self.get_or_create_settings(update.effective_user.id)
        text = (
            "🖼 Настройки генерации изображений:\n\n"
            f"🌐 URL: {settings.base_url}\n"
            f"🎨 Модель: {settings.model}\n"
            f"📐 Размер: {settings.size}\n"
            f"✨ Качество: {settings.quality}\n"
            f"🎭 Стиль: {settings.style}\n"
            f"HDR: {'Вкл' if settings.hdr else 'Выкл'}"
        )
        
        if isinstance(update, Update):
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.edit_message_text(text, reply_markup=reply_markup)
        return IMAGE_MAIN_MENU

    def get_conversation_handler(self):
        """Return conversation handler for image settings"""
        return ConversationHandler(
            entry_points=[CommandHandler('image_settings', self.image_settings_menu)],
            states={
                IMAGE_MAIN_MENU: [
                    CallbackQueryHandler(self.select_image_model, pattern="^select_image_model$"),
                    CallbackQueryHandler(self.select_image_size, pattern="^select_image_size$"),
                    CallbackQueryHandler(self.select_image_quality, pattern="^select_image_quality$"),
                    CallbackQueryHandler(self.select_image_style, pattern="^select_image_style$"),
                    CallbackQueryHandler(self.toggle_hdr, pattern="^toggle_hdr$"),
                ],
                # Add other states and handlers
            },
            fallbacks=[CallbackQueryHandler(self.image_settings_menu, pattern="^close_image_settings$")],
        ) 