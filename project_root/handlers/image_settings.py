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

    async def get_or_create_settings(self, user_id: int) -> dict:
        """Get or create image settings"""
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                user = User(telegram_id=user_id)
                session.add(user)
                session.commit()
            
            settings = session.query(ImageSettings).filter_by(user_id=user.id).first()
            if not settings:
                settings = ImageSettings(user_id=user.id)
                session.add(settings)
                session.commit()
            
            session.refresh(settings)
            
            settings_dict = {
                'base_url': settings.base_url,
                'model': settings.model,
                'size': settings.size,
                'quality': settings.quality,
                'style': settings.style,
                'hdr': settings.hdr
            }
            
        return settings_dict

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
            f"🌐 URL: {settings['base_url']}\n"
            f"🎨 Модель: {settings['model']}\n"
            f"📐 Размер: {settings['size']}\n"
            f"✨ Качество: {settings['quality']}\n"
            f"🎭 Стиль: {settings['style']}\n"
            f"HDR: {'Вкл' if settings['hdr'] else 'Выкл'}"
        )
        
        if isinstance(update, Update):
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.edit_message_text(text, reply_markup=reply_markup)
        return IMAGE_MAIN_MENU

    async def select_image_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image model selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for model_id, model_name in self.available_models.items():
            keyboard.append([InlineKeyboardButton(model_name, callback_data=f"set_model_{model_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите модель для генерации изображений:", reply_markup=reply_markup)
        return IMAGE_MODEL

    async def select_image_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image size selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for size_id, size_name in self.size_options.items():
            keyboard.append([InlineKeyboardButton(size_name, callback_data=f"set_size_{size_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите размер изображения:", reply_markup=reply_markup)
        return IMAGE_SIZE

    async def select_image_quality(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image quality selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for quality_id, quality_name in self.quality_options.items():
            keyboard.append([InlineKeyboardButton(quality_name, callback_data=f"set_quality_{quality_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите качество изображения:", reply_markup=reply_markup)
        return IMAGE_QUALITY

    async def select_image_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image style selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for style_id, style_name in self.style_options.items():
            keyboard.append([InlineKeyboardButton(style_name, callback_data=f"set_style_{style_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите стиль изображения:", reply_markup=reply_markup)
        return IMAGE_STYLE

    async def toggle_hdr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle HDR setting"""
        query = update.callback_query
        await query.answer()
        
        with Session() as session:
            settings = await self.get_or_create_settings(query.from_user.id)
            settings['hdr'] = not settings['hdr']
            session.commit()
        
        return await self.image_settings_menu(query, context)

    async def handle_setting_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings updates"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        setting_type = data.split('_')[1]
        value = '_'.join(data.split('_')[2:])
        
        with Session() as session:
            settings = await self.get_or_create_settings(query.from_user.id)
            
            if setting_type == 'model':
                settings['model'] = value
            elif setting_type == 'size':
                settings['size'] = value
            elif setting_type == 'quality':
                settings['quality'] = value
            elif setting_type == 'style':
                settings['style'] = value
                
            session.commit()
        
        return await self.image_settings_menu(query, context)

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
                IMAGE_MODEL: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_model_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_menu$"),
                ],
                IMAGE_SIZE: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_size_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_menu$"),
                ],
                IMAGE_QUALITY: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_quality_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_menu$"),
                ],
                IMAGE_STYLE: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_style_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_menu$"),
                ],
            },
            fallbacks=[CallbackQueryHandler(self.image_settings_menu, pattern="^close_image_settings$")],
            allow_reentry=True,
            name="image_settings_conversation",
            per_chat=True,
            per_user=True,
            per_message=True
        ) 