# Project Overview
GPT Telegram bot which can work with text and images (all of these can be input and output)

# Core Functionalities
## 0. Bot should be deployed on railway.app and should work in polling mode
## 1. Bot should support openai streaming mode
## 2. Bot can be added into telegram groups
## 3. Bot should support user id's and can store user message history
## 4. There should be a settings panel, so one can edit 
the following parameters for text model:
-- base url of openai compatible model
-- model itself (either chose from the short list of 4 most popular openai models or enter manually the name of the model)
-- temperature (from 0 to 1, of possible use progress bar or something like this)
-- max tokens (from 150 till infinity)
-- There should be an option to use for text messages a pre-configured AI-assitant by providing uri of API end point. This should be instead of a GPT text model. When user choses AI-assitant in GPT text model settings it should overwrite GPT text model settings and all text questions should be handled by AI-assitant via API end point provided.
## 5. There should be a settings panel, so one can edit 
the following parameters for images model:
### base url of openai compatible image model
### model itself (either chose from the short list of most popular llm image models or enter manually the name of the model)
### all Key Parameters and Features of the image model
### handlers for each image setting (base_url, model, size, quality, style, hdr)
### get_image_settings and update_image_settings methods
## 6. There should be an option to clear message history for a user
## 7. validation for user inputs
## 8. confirmation dialogs for critical settings changes
## 9. Implement settings export/import functionality
## 10. Implement creating new images based on image and text input combined
## 11. Implement all needed logging and debugging into the code base, so it could be easily turned off after the project is perfectly running in production and turned back on when it is necessairy to troubleshoot possible issues

# Documenation
## Example of Procfile for Railway:
```
worker: python bot.py

```

## Example of Railway configuration file:
```
{
    "$schema": "https://railway.app/railway.schema.json",
    "build": {
        "builder": "NIXPACKS"
    },
    "deploy": {
        "startCommand": "python bot.py",
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
    }
}
```

## Example of simple status endpoint for railway.app deployment
```
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
```

## Example of support openai streaming mode
```
from telegram import Update
from telegram.ext import ContextTypes
from openai import AsyncOpenAI
import asyncio

async def stream_openai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Initial response message
    response_message = await update.message.reply_text("⌛ Генерирую ответ...")
    collected_chunks = []
    
    try:
        client = AsyncOpenAI()
        # Start streaming response
        stream = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": update.message.text}],
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                collected_chunks.append(chunk.choices[0].delta.content)
                # Update message every 20 chunks or when chunk ends with sentence
                if len(collected_chunks) % 20 == 0 or chunk.choices[0].delta.content.endswith(('.', '!', '?')):
                    current_response = ''.join(collected_chunks)
                    try:
                        await response_message.edit_text(current_response)
                    except Exception:
                        continue
                        
        # Final update with complete response
        final_response = ''.join(collected_chunks)
        await response_message.edit_text(final_response)
        
    except Exception as e:
        await response_message.edit_text(f"❌ Произошла ошибка: {str(e)}")

# Register handler in your bot
async def setup_handlers(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stream_openai_response))
```
## Example of a Telegram bot that can work in groups with proper permission handling and group-specific features.
```
from telegram import Update, ChatMemberUpdated, ChatPermissions, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters
)
from typing import Optional, Tuple

class GroupBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Admin commands
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("warn", self.cmd_warn))
        
        # Track member changes
        self.application.add_handler(ChatMemberHandler(self.track_members, ChatMemberHandler.CHAT_MEMBER))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if update.effective_chat.type == "private":
            await update.message.reply_text("Привет! Добавьте меня в группу для полного функционала.")
        else:
            await update.message.reply_text("Бот активирован в этой группе! Используйте /help для списка команд.")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📋 Доступные команды:\n"
            "/settings - Настройки группы (только админы)\n"
            "/warn - Предупредить пользователя (только админы)\n"
            "/help - Показать это сообщение"
        )
        await update.message.reply_text(help_text)

    async def check_admin(self, update: Update) -> bool:
        """Check if user is admin"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        member = await update.effective_chat.get_member(user_id)
        return member.status in ["creator", "administrator"]

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle group settings (admin only)"""
        if not await self.check_admin(update):
            await update.message.reply_text("⚠️ Эта команда доступна только администраторам.")
            return

        settings_text = (
            "⚙️ Настройки группы:\n"
            "1. Режим модерации: Включен\n"
            "2. Приветствие новых участников: Включено\n"
            "3. Антиспам: Включен"
        )
        await update.message.reply_text(settings_text)

    async def cmd_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Warn user (admin only)"""
        if not await self.check_admin(update):
            await update.message.reply_text("⚠️ Эта команда доступна только администраторам.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("↩️ Ответьте на сообщение пользователя, которого хотите предупредить.")
            return

        warned_user = update.message.reply_to_message.from_user
        await update.message.reply_text(f"⚠️ Пользователь {warned_user.mention_html()} получил предупреждение.")

    async def track_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track member updates in the group"""
        result = self.extract_status_change(update.chat_member)
        if result is None:
            return

        was_member, is_member = result

        if not was_member and is_member:
            # New member joined
            await update.effective_chat.send_message(
                f"👋 Добро пожаловать, {update.chat_member.new_chat_member.member.mention_html()}!"
            )
        elif was_member and not is_member:
            # Member left
            await update.effective_chat.send_message(
                f"👋 До свидания, {update.chat_member.new_chat_member.member.mention_html()}!"
            )

    @staticmethod
    def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
        """Extract status change from ChatMemberUpdated event"""
        status_change = chat_member_update.difference().get("status")
        if status_change is None:
            return None

        old_is_member = chat_member_update.old_chat_member.status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ]
        new_is_member = chat_member_update.new_chat_member.status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ]
        return old_is_member, new_is_member

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        # Example of basic message handling
        if update.effective_chat.type != "private":
            # Group message handling logic here
            pass

    def run(self):
        """Run the bot"""
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    bot = GroupBot(BOT_TOKEN)
    bot.run()
```

## Example of a Telegram bot that manages user IDs and message history using SQLite for storage.
```
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import sqlite3
from datetime import datetime
import json
from typing import Optional, List, Dict

class UserHistoryBot:
    def __init__(self, token: str, db_path: str = "user_history.db"):
        self.token = token
        self.db_path = db_path
        self.setup_database()
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

    def setup_handlers(self):
        """Setup bot command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("history", self.cmd_history))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def save_user(self, user_data: Dict):
        """Save or update user information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (
                user_data['id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name')
            ))

    async def save_message(self, user_id: int, message_text: str):
        """Save message to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO message_history (user_id, message_text)
                VALUES (?, ?)
            """, (user_id, message_text))

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Retrieve user message history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT message_text, timestamp
                FROM message_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await self.save_user(user.to_dict())
        
        welcome_text = (
            f"👋 Здравствуйте, {user.first_name}!\n\n"
            "Доступные команды:\n"
            "/history - Показать историю сообщений\n"
            "/stats - Показать статистику\n"
        )
        await update.message.reply_text(welcome_text)

    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user_id = update.effective_user.id
        history = await self.get_user_history(user_id)
        
        if not history:
            await update.message.reply_text("📭 История сообщений пуста")
            return

        history_text = "📋 Ваши последние сообщения:\n\n"
        for item in history:
            date = datetime.fromisoformat(item['timestamp']).strftime("%d.%m.%Y %H:%M")
            history_text += f"🕒 {date}\n📝 {item['message_text']}\n\n"
        
        await update.message.reply_text(history_text)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        
        with sqlite3.connect(self.db_path) as conn:
            # Get total messages count
            messages_count = conn.execute("""
                SELECT COUNT(*) FROM message_history WHERE user_id = ?
            """, (user_id,)).fetchone()[0]
            
            # Get first message date
            first_message = conn.execute("""
                SELECT MIN(timestamp) FROM message_history WHERE user_id = ?
            """, (user_id,)).fetchone()[0]

        stats_text = (
            "📊 Ваша статистика:\n\n"
            f"📝 Всего сообщений: {messages_count}\n"
            f"📅 Первое сообщение: {datetime.fromisoformat(first_message).strftime('%d.%m.%Y') if first_message else 'Нет данных'}"
        )
        
        await update.message.reply_text(stats_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user = update.effective_user
        message_text = update.message.text
        
        # Save user data and message
        await self.save_user(user.to_dict())
        await self.save_message(user.id, message_text)
        
        # Optional: Acknowledge message receipt
        await update.message.reply_text("✅ Сообщение сохранено")

    def run(self):
        """Run the bot"""
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
```

## Example of implementing settings panels for model configuration and AI assistant settings using inline keyboards and state management.
```
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from dataclasses import dataclass
from typing import Optional
import json

# States for conversation handler
(
    MAIN_MENU,
    MODEL_SETTINGS,
    BASE_URL,
    MODEL_SELECTION,
    CUSTOM_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    ASSISTANT_URL,
) = range(8)

@dataclass
class ModelSettings:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    assistant_url: Optional[str] = None
    use_assistant: bool = False

class SettingsHandler:
    def __init__(self):
        self.settings = {}  # Store settings per user
        self.load_settings()

    def load_settings(self):
        """Load settings from file"""
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            pass

    def save_settings(self):
        """Save settings to file"""
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)

    def get_user_settings(self, user_id: str) -> ModelSettings:
        """Get settings for specific user"""
        if str(user_id) not in self.settings:
            self.settings[str(user_id)] = ModelSettings().__dict__
        return ModelSettings(**self.settings[str(user_id)])

    async def settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main settings menu"""
        keyboard = [
            [InlineKeyboardButton("📝 Настройки модели", callback_data="model_settings")],
            [InlineKeyboardButton("🤖 Настройки ассистента", callback_data="assistant_settings")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚙️ Настройки:", reply_markup=reply_markup)
        return MAIN_MENU

    async def model_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show model settings menu"""
        query = update.callback_query
        user_settings = self.get_user_settings(query.from_user.id)
        
        keyboard = [
            [InlineKeyboardButton(f"🌐 Base URL: {user_settings.base_url}", callback_data="edit_base_url")],
            [InlineKeyboardButton(f"🤖 Модель: {user_settings.model}", callback_data="select_model")],
            [InlineKeyboardButton(f"🌡️ Temperature: {user_settings.temperature}", callback_data="edit_temperature")],
            [InlineKeyboardButton(f"📊 Max Tokens: {user_settings.max_tokens}", callback_data="edit_max_tokens")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Настройки модели:", reply_markup=reply_markup)
        return MODEL_SETTINGS

    async def model_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show model selection menu"""
        query = update.callback_query
        keyboard = [
            [InlineKeyboardButton("GPT-3.5-Turbo", callback_data="model_gpt-3.5-turbo")],
            [InlineKeyboardButton("GPT-4", callback_data="model_gpt-4")],
            [InlineKeyboardButton("GPT-4-Turbo", callback_data="model_gpt-4-turbo")],
            [InlineKeyboardButton("Claude-3-Sonnet", callback_data="model_claude-3-sonnet")],
            [InlineKeyboardButton("Своя модель", callback_data="custom_model")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите модель:", reply_markup=reply_markup)
        return MODEL_SELECTION

    async def temperature_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show temperature selection menu"""
        query = update.callback_query
        keyboard = []
        for i in range(0, 11, 2):
            temp = i / 10
            keyboard.append([InlineKeyboardButton(f"🌡️ {temp}", callback_data=f"temp_{temp}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите температуру (0 - более точно, 1 - более креативно):",
                                    reply_markup=reply_markup)
        return TEMPERATURE

    async def handle_base_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle base URL input"""
        user_id = str(update.message.from_user.id)
        new_url = update.message.text
        
        user_settings = self.get_user_settings(user_id)
        user_settings.base_url = new_url
        self.settings[user_id] = user_settings.__dict__
        self.save_settings()
        
        await update.message.reply_text(f"Base URL обновлен на: {new_url}")
        return await self.model_settings_menu(update, context)

    async def handle_max_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle max tokens input"""
        try:
            tokens = int(update.message.text)
            if tokens < 150:
                await update.message.reply_text("Минимальное значение токенов: 150")
                return MAX_TOKENS
                
            user_id = str(update.message.from_user.id)
            user_settings = self.get_user_settings(user_id)
            user_settings.max_tokens = tokens
            self.settings[user_id] = user_settings.__dict__
            self.save_settings()
            
            await update.message.reply_text(f"Max tokens установлено: {tokens}")
            return await self.model_settings_menu(update, context)
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите целое число")
            return MAX_TOKENS

    async def handle_assistant_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI assistant URL input"""
        user_id = str(update.message.from_user.id)
        assistant_url = update.message.text
        
        user_settings = self.get_user_settings(user_id)
        user_settings.assistant_url = assistant_url
        user_settings.use_assistant = True
        self.settings[user_id] = user_settings.__dict__
        self.save_settings()
        
        await update.message.reply_text(f"URL ассистента установлен: {assistant_url}")
        return await self.settings_menu(update, context)

    def get_conversation_handler(self):
        """Return conversation handler for settings"""
        return ConversationHandler(
            entry_points=[CommandHandler('settings', self.settings_menu)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.model_settings_menu, pattern="^model_settings$"),
                    CallbackQueryHandler(self.handle_assistant_url, pattern="^assistant_settings$"),
                ],
                MODEL_SETTINGS: [
                    CallbackQueryHandler(self.model_selection, pattern="^select_model$"),
                    CallbackQueryHandler(self.temperature_selection, pattern="^edit_temperature$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_max_tokens),
                ],
                MODEL_SELECTION: [
                    CallbackQueryHandler(self.handle_model_selection, pattern="^model_"),
                ],
                TEMPERATURE: [
                    CallbackQueryHandler(self.handle_temperature, pattern="^temp_"),
                ],
                BASE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_base_url),
                ],
                MAX_TOKENS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_max_tokens),
                ],
                ASSISTANT_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_assistant_url),
                ],
            },
            fallbacks=[CallbackQueryHandler(self.cancel, pattern="^close$")],
        )
```

## Example of implementing an image model settings panel with comprehensive configuration options
```
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from dataclasses import dataclass
from typing import Optional
import json

# States for conversation handler
(
    IMAGE_MAIN_MENU,
    IMAGE_BASE_URL,
    IMAGE_MODEL,
    IMAGE_SIZE,
    IMAGE_QUALITY,
    IMAGE_STYLE,
    IMAGE_HDR,
    CUSTOM_IMAGE_MODEL,
) = range(8)

@dataclass
class ImageModelSettings:
    base_url: str = "https://api.openai.com/v1"
    model: str = "dall-e-3"
    size: str = "1024x1024"
    quality: str = "standard"
    style: str = "natural"
    hdr: bool = False

class ImageSettingsHandler:
    def __init__(self):
        self.settings = {}
        self.load_settings()
        
        # Available options
        self.available_models = {
            "dall-e-3": "DALL-E 3",
            "dall-e-2": "DALL-E 2",
            "stable-diffusion-xl": "Stable Diffusion XL",
            "midjourney": "Midjourney API"
        }
        
        self.size_options = {
            "1024x1024": "1024x1024 (Стандарт)",
            "1792x1024": "1792x1024 (Широкий)",
            "1024x1792": "1024x1792 (Высокий)",
            "512x512": "512x512 (Маленький)"
        }

    def load_settings(self):
        """Load settings from file"""
        try:
            with open('image_settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            pass

    def save_settings(self):
        """Save settings to file"""
        with open('image_settings.json', 'w') as f:
            json.dump(self.settings, f)

    def get_user_settings(self, user_id: str) -> ImageModelSettings:
        """Get settings for specific user"""
        if str(user_id) not in self.settings:
            self.settings[str(user_id)] = ImageModelSettings().__dict__
        return ImageModelSettings(**self.settings[str(user_id)])

    async def image_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main image settings menu"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
        else:
            query = update

        user_settings = self.get_user_settings(update.effective_user.id)
        
        keyboard = [
            [InlineKeyboardButton(f"🌐 Base URL: {user_settings.base_url}", 
                                callback_data="edit_image_base_url")],
            [InlineKeyboardButton(f"🎨 Модель: {self.available_models.get(user_settings.model, user_settings.model)}", 
                                callback_data="select_image_model")],
            [InlineKeyboardButton(f"📐 Размер: {user_settings.size}", 
                                callback_data="select_image_size")],
            [InlineKeyboardButton(f"✨ Качество: {user_settings.quality}", 
                                callback_data="select_image_quality")],
            [InlineKeyboardButton(f"🎭 Стиль: {user_settings.style}", 
                                callback_data="select_image_style")],
            [InlineKeyboardButton(f"HDR: {'Вкл' if user_settings.hdr else 'Выкл'}", 
                                callback_data="toggle_hdr")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close_image_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = "🖼 Настройки генерации изображений:"
        
        if update.callback_query:
            await query.edit_message_text(message_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        
        return IMAGE_MAIN_MENU

    async def select_image_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show model selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for model_id, model_name in self.available_models.items():
            keyboard.append([InlineKeyboardButton(model_name, 
                                                callback_data=f"set_model_{model_id}")])
        
        keyboard.append([InlineKeyboardButton("✏️ Своя модель", 
                                            callback_data="custom_image_model")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", 
                                            callback_data="back_to_image_settings")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите модель для генерации изображений:", 
                                    reply_markup=reply_markup)
        return IMAGE_MODEL

    async def select_image_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show size selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        for size_id, size_name in self.size_options.items():
            keyboard.append([InlineKeyboardButton(size_name, 
                                                callback_data=f"set_size_{size_id}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", 
                                            callback_data="back_to_image_settings")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите размер изображения:", 
                                    reply_markup=reply_markup)
        return IMAGE_SIZE

    async def select_image_quality(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show quality selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("Стандартное качество", callback_data="set_quality_standard")],
            [InlineKeyboardButton("Высокое качество", callback_data="set_quality_hd")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите качество изображения:", 
                                    reply_markup=reply_markup)
        return IMAGE_QUALITY

    async def select_image_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show style selection menu"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("Натуральный", callback_data="set_style_natural")],
            [InlineKeyboardButton("Живописный", callback_data="set_style_vivid")],
            [InlineKeyboardButton("Аниме", callback_data="set_style_anime")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_image_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите стиль изображения:", 
                                    reply_markup=reply_markup)
        return IMAGE_STYLE

    async def handle_setting_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings updates"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        user_settings = self.get_user_settings(user_id)
        data = query.data
        
        if data.startswith("set_model_"):
            user_settings.model = data.replace("set_model_", "")
        elif data.startswith("set_size_"):
            user_settings.size = data.replace("set_size_", "")
        elif data.startswith("set_quality_"):
            user_settings.quality = data.replace("set_quality_", "")
        elif data.startswith("set_style_"):
            user_settings.style = data.replace("set_style_", "")
        elif data == "toggle_hdr":
            user_settings.hdr = not user_settings.hdr
        
        self.settings[user_id] = user_settings.__dict__
        self.save_settings()
        
        return await self.image_settings_menu(update, context)

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
                    CallbackQueryHandler(self.handle_setting_update, pattern="^toggle_hdr$"),
                ],
                IMAGE_MODEL: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_model_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_settings$"),
                ],
                IMAGE_SIZE: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_size_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_settings$"),
                ],
                IMAGE_QUALITY: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_quality_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_settings$"),
                ],
                IMAGE_STYLE: [
                    CallbackQueryHandler(self.handle_setting_update, pattern="^set_style_"),
                    CallbackQueryHandler(self.image_settings_menu, pattern="^back_to_image_settings$"),
                ],
            },
            fallbacks=[CallbackQueryHandler(self.image_settings_menu, pattern="^close_image_settings$")],
        )
```

## Example of Integration of settings panel with main bot
### for image settings panel
```
from telegram.ext import Application
from image_settings_handler import ImageSettingsHandler

class Bot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.image_settings_handler = ImageSettingsHandler()
        self.setup_handlers()

    def setup_handlers(self):
        # Add image settings conversation handler
        self.application.add_handler(self.image_settings_handler.get_conversation_handler())
        # Add other handlers...

    async def generate_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image generation with user settings"""
        user_id = str(update.effective_user.id)
        settings = self.image_settings_handler.get_user_settings(user_id)
        
        # Use settings for image generation
        image_params = {
            "model": settings.model,
            "size": settings.size,
            "quality": settings.quality,
            "style": settings.style,
            "hdr": settings.hdr
        }
        # Your image generation logic here...

    def run(self):
        self.application.run_polling()
```
### for text settings panel
```
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    settings = settings_handler.get_user_settings(user_id)
    
    if settings.use_assistant:
        # Use AI assistant API
        response = await call_assistant_api(settings.assistant_url, update.message.text)
    else:
        # Use OpenAI-compatible model
        response = await call_model_api(
            base_url=settings.base_url,
            model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            message=update.message.text
        )
```

## Example of implementing message history clearing functionality with different options for users.
```
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

class HistoryCleaner:
    def __init__(self, db_path: str = "user_history.db"):
        self.db_path = db_path

    async def show_clear_history_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display history clearing options"""
        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить всю историю", callback_data="clear_all")],
            [InlineKeyboardButton("📅 Очистить за последние 24 часа", callback_data="clear_24h")],
            [InlineKeyboardButton("📅 Очистить за последние 7 дней", callback_data="clear_7d")],
            [InlineKeyboardButton("📅 Очистить за последний месяц", callback_data="clear_30d")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_clear")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🗑️ Выберите период для очистки истории сообщений:",
            reply_markup=reply_markup
        )

    async def handle_clear_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle history clearing options"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel_clear":
            await query.edit_message_text("❌ Очистка истории отменена")
            return

        user_id = query.from_user.id
        days = {
            "clear_24h": 1,
            "clear_7d": 7,
            "clear_30d": 30,
            "clear_all": None
        }

        days_to_clear = days.get(query.data)
        deleted_count = await self.clear_history(user_id, days_to_clear)

        if days_to_clear:
            message = f"✅ Удалено {deleted_count} сообщений за последние {days_to_clear} дней"
        else:
            message = f"✅ Удалено {deleted_count} сообщений из истории"

        await query.edit_message_text(message)

    async def clear_history(self, user_id: int, days: Optional[int] = None) -> int:
        """Clear user's message history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if days is None:
                # Clear all history
                cursor.execute("""
                    DELETE FROM message_history 
                    WHERE user_id = ?
                """, (user_id,))
            else:
                # Clear history for specific period
                date_threshold = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    DELETE FROM message_history 
                    WHERE user_id = ? AND timestamp >= ?
                """, (user_id, date_threshold.isoformat()))
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

    def get_handlers(self):
        """Return handlers for the bot"""
        return [
            CommandHandler("clear_history", self.show_clear_history_menu),
            CallbackQueryHandler(self.handle_clear_history, pattern="^clear_")
        ]
```
### integration of clearing message history with the main bot
```
from telegram.ext import Application
from history_handler import HistoryCleaner

class Bot:
    def __init__(self, token: str, db_path: str = "user_history.db"):
        self.application = Application.builder().token(token).build()
        self.history_cleaner = HistoryCleaner(db_path)
        self.setup_handlers()

    def setup_handlers(self):
        # Add history clearing handlers
        for handler in self.history_cleaner.get_handlers():
            self.application.add_handler(handler)
        # Add other handlers...

    def run(self):
        self.application.run_polling()
```
### To add confirmation dialogs for extra safety, here's an enhanced version of the clearing process
```
class EnhancedHistoryCleaner(HistoryCleaner):
    async def show_clear_history_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display history clearing options with confirmation"""
        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить всю историю", callback_data="confirm_clear_all")],
            [InlineKeyboardButton("📅 Очистить за последние 24 часа", callback_data="confirm_clear_24h")],
            [InlineKeyboardButton("📅 Очистить за последние 7 дней", callback_data="confirm_clear_7d")],
            [InlineKeyboardButton("📅 Очистить за последний месяц", callback_data="confirm_clear_30d")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_clear")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🗑️ Выберите период для очистки истории сообщений:",
            reply_markup=reply_markup
        )

    async def show_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show confirmation dialog"""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("confirm_", "")
        period_text = {
            "clear_all": "всю историю",
            "clear_24h": "сообщения за последние 24 часа",
            "clear_7d": "сообщения за последние 7 дней",
            "clear_30d": "сообщения за последний месяц"
        }

        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=action),
                InlineKeyboardButton("❌ Нет", callback_data="cancel_clear")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ Вы уверены, что хотите удалить {period_text[action]}?\n"
            "Это действие нельзя отменить!",
            reply_markup=reply_markup
        )

    async def get_history_stats(self, user_id: int, days: Optional[int] = None) -> int:
        """Get message count for period"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if days is None:
                cursor.execute("""
                    SELECT COUNT(*) FROM message_history 
                    WHERE user_id = ?
                """, (user_id,))
            else:
                date_threshold = datetime.now() - timedelta(days=days)
                cursor.execute("""
                    SELECT COUNT(*) FROM message_history 
                    WHERE user_id = ? AND timestamp >= ?
                """, (user_id, date_threshold.isoformat()))
            
            return cursor.fetchone()[0]

    def get_handlers(self):
        """Return handlers for the bot"""
        return [
            CommandHandler("clear_history", self.show_clear_history_menu),
            CallbackQueryHandler(self.show_confirmation, pattern="^confirm_"),
            CallbackQueryHandler(self.handle_clear_history, pattern="^clear_"),
            CallbackQueryHandler(self.handle_cancel, pattern="^cancel_")
        ]
```
### Usage example
```
# Initialize bot with enhanced history cleaner
bot = Bot(token="YOUR_BOT_TOKEN", db_path="user_history.db")

# User commands:
# /clear_history - Show history clearing menu
```

# Project files structure
project_root/
│
├── main.py              # Entry point for Railway
├── bot.py               # Main bot logic
├── api.py               # FastAPI health check endpoint
├── handlers/
│   ├── __init__.py
│   ├── settings.py      # Settings handlers
│   ├── history.py       # History handlers
│   └── group.py         # Group handlers
│
├── utils/
│   ├── __init__.py
│   ├── database.py      # Database models and operations
│   └── helpers.py       # Common utilities and helper functions
│
├── requirements.txt     # Must include Railway-specific packages
├── Procfile            # Railway process definition
└── railway.json        # Railway configuration