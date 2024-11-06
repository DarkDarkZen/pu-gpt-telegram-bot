from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from openai import AsyncOpenAI
import asyncio
import json
from config import config
from models import TextModelSettings, User, MessageHistory
import aiohttp
from typing import Dict, Any, List, Optional
from enum import Enum, auto

# Add these new error classes at the top of the file
class AssistantAPIError(Exception):
    """Base exception for Assistant API errors"""
    pass

class AssistantConnectionError(AssistantAPIError):
    """Connection errors with Assistant API"""
    pass

class AssistantResponseError(AssistantAPIError):
    """Invalid response from Assistant API"""
    pass

class AssistantTimeoutError(AssistantAPIError):
    """Timeout from Assistant API"""
    pass

# Add these states for the settings conversation
class SettingsState(Enum):
    MAIN_MENU = auto()
    TEXT_MODEL = auto()
    BASE_URL = auto()
    MODEL_SELECTION = auto()
    TEMPERATURE = auto()
    MAX_TOKENS = auto()
    ASSISTANT_URL = auto()
    CONFIRM = auto()
    IMAGE_MENU = auto()
    IMAGE_BASE_URL = auto()
    IMAGE_MODEL = auto()
    IMAGE_SIZE = auto()
    IMAGE_QUALITY = auto()
    IMAGE_STYLE = auto()

class GPTBot:
    def __init__(self):
        self.config = config
        self.config.validate()
        self.application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        self.message_history = MessageHistory(config.DATABASE_URL)
        self.available_models = {
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "claude-3-sonnet": "Claude 3 Sonnet"
        }
        self.available_image_models = {
            "dall-e-3": "DALL-E 3",
            "dall-e-2": "DALL-E 2",
            "stable-diffusion-xl": "Stable Diffusion XL",
        }
        
        self.image_sizes = {
            "1024x1024": "1024x1024 (Квадрат)",
            "1792x1024": "1792x1024 (Широкий)",
            "1024x1792": "1024x1792 (Высокий)",
            "512x512": "512x512 (Маленький)",
        }
        
        self.image_qualities = {
            "standard": "Стандартное",
            "hd": "Высокое качество",
        }
        
        self.image_styles = {
            "natural": "Натуральный",
            "vivid": "Яркий",
            "anime": "Аниме",
        }
        self.setup_handlers()

    def setup_handlers(self):
        """Setup bot command and message handlers"""
        # Add settings handler
        settings_handler = ConversationHandler(
            entry_points=[CommandHandler("settings", self.show_settings_menu)],
            states={
                SettingsState.MAIN_MENU: [
                    CallbackQueryHandler(self.text_model_menu, pattern="^text_settings$"),
                    CallbackQueryHandler(self.toggle_assistant, pattern="^toggle_assistant$"),
                ],
                SettingsState.TEXT_MODEL: [
                    CallbackQueryHandler(self.handle_text_model_setting, pattern="^set_"),
                    CallbackQueryHandler(self.show_settings_menu, pattern="^back$"),
                ],
                SettingsState.BASE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_base_url),
                    CallbackQueryHandler(self.text_model_menu, pattern="^back$"),
                ],
                SettingsState.MODEL_SELECTION: [
                    CallbackQueryHandler(self.handle_model_selection, pattern="^model_"),
                    CallbackQueryHandler(self.text_model_menu, pattern="^back$"),
                ],
                SettingsState.TEMPERATURE: [
                    CallbackQueryHandler(self.handle_temperature, pattern="^temp_"),
                    CallbackQueryHandler(self.text_model_menu, pattern="^back$"),
                ],
                SettingsState.MAX_TOKENS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_max_tokens),
                    CallbackQueryHandler(self.text_model_menu, pattern="^back$"),
                ],
                SettingsState.ASSISTANT_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_assistant_url),
                    CallbackQueryHandler(self.show_settings_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_MENU: [
                    CallbackQueryHandler(self.handle_image_setting, pattern="^set_img_"),
                    CallbackQueryHandler(self.show_settings_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_BASE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_image_base_url),
                    CallbackQueryHandler(self.image_model_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_MODEL: [
                    CallbackQueryHandler(self.handle_image_model, pattern="^img_model_"),
                    CallbackQueryHandler(self.image_model_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_SIZE: [
                    CallbackQueryHandler(self.handle_image_size, pattern="^img_size_"),
                    CallbackQueryHandler(self.image_model_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_QUALITY: [
                    CallbackQueryHandler(self.handle_image_quality, pattern="^img_quality_"),
                    CallbackQueryHandler(self.image_model_menu, pattern="^back$"),
                ],
                SettingsState.IMAGE_STYLE: [
                    CallbackQueryHandler(self.handle_image_style, pattern="^img_style_"),
                    CallbackQueryHandler(self.image_model_menu, pattern="^back$"),
                ],
            },
            fallbacks=[CallbackQueryHandler(self.cancel_settings, pattern="^cancel$")],
        )
        
        self.application.add_handler(settings_handler)
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = (
            "👋 Здравствуйте!\n\n"
            "Я GPT бот, который может работать с текстом и изображениями.\n"
            "Просто отправьте мне сообщение, и я отвечу в режиме реального времени."
        )
        await update.message.reply_text(welcome_text)

    async def stream_openai_response(self, 
                                   update: Update, 
                                   text_settings: TextModelSettings,
                                   prompt: str):
        """Stream OpenAI response with real-time updates"""
        # Initial response message
        response_message = await update.message.reply_text("⌛ Генерирую ответ...")
        collected_chunks = []
        
        try:
            client = AsyncOpenAI(
                api_key=self.config.OPENAI_API_KEY,
                base_url=text_settings.base_url
            )

            # Start streaming response
            stream = await client.chat.completions.create(
                model=text_settings.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=text_settings.temperature,
                max_tokens=text_settings.max_tokens,
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
            
            # Save message to history
            await self.save_conversation(
                update.effective_user.id,
                prompt,
                final_response
            )
            
        except Exception as e:
            error_message = f"❌ Произошла ошибка: {str(e)}"
            await response_message.edit_text(error_message)

    async def save_conversation(self, 
                                user_id: int, 
                                prompt: str, 
                                response: str,
                                assistant_type: str = "gpt"):
        """Save conversation to message history with assistant type"""
        import sqlite3
        from datetime import datetime
        
        with sqlite3.connect(self.message_history.db_path) as conn:
            timestamp = datetime.now().isoformat()
            
            # Save user message
            conn.execute("""
                INSERT INTO messages (user_id, message_text, role, timestamp, assistant_type)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, prompt, "user", timestamp, assistant_type))
            
            # Save assistant response
            conn.execute("""
                INSERT INTO messages (user_id, message_text, role, timestamp, assistant_type)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, response, "assistant", timestamp, assistant_type))

    async def get_user_settings(self, user_id: int) -> TextModelSettings:
        """Get or create user settings"""
        import sqlite3
        
        with sqlite3.connect(self.message_history.db_path) as conn:
            cursor = conn.execute("""
                SELECT text_settings FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            
            if result:
                settings_dict = json.loads(result[0])
                return TextModelSettings(**settings_dict)
            
            # Create default settings if user doesn't exist
            default_settings = TextModelSettings(
                base_url=self.config.OPENAI_BASE_URL,
                model=self.config.DEFAULT_TEXT_MODEL,
                temperature=self.config.DEFAULT_TEMPERATURE,
                max_tokens=self.config.DEFAULT_MAX_TOKENS
            )
            
            settings_json = json.dumps(default_settings.__dict__)
            conn.execute("""
                INSERT INTO users (user_id, text_settings)
                VALUES (?, ?)
            """, (user_id, settings_json))
            
            return default_settings

    async def call_assistant_api(self, 
                               assistant_url: str, 
                               prompt: str) -> Dict[Any, Any]:
        """Call external AI assistant API with enhanced error handling"""
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(
                        assistant_url,
                        json={"message": prompt},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if not isinstance(data, dict) or 'response' not in data:
                                raise AssistantResponseError("Invalid response format from API")
                            return data
                        elif response.status == 429:
                            raise AssistantAPIError("Rate limit exceeded")
                        elif response.status >= 500:
                            raise AssistantAPIError("Assistant service unavailable")
                        else:
                            raise AssistantAPIError(f"API returned status code {response.status}")
                        
                except aiohttp.ClientConnectionError:
                    raise AssistantConnectionError("Failed to connect to assistant API")
                except aiohttp.ClientTimeout:
                    raise AssistantTimeoutError("Assistant API request timed out")
                except aiohttp.ContentTypeError:
                    raise AssistantResponseError("Invalid JSON response from API")
                
        except Exception as e:
            if isinstance(e, AssistantAPIError):
                raise e
            raise AssistantAPIError(f"Unexpected error: {str(e)}")

    async def stream_assistant_response(self,
                                      update: Update,
                                      assistant_url: str,
                                      prompt: str):
        """Handle AI assistant response with enhanced error handling"""
        response_message = await update.message.reply_text("⌛ Генерирую ответ...")
        
        try:
            response_data = await self.call_assistant_api(assistant_url, prompt)
            response_text = response_data['response']
            
            # Simulate streaming by splitting response into chunks
            chunks = response_text.split()
            collected_chunks = []
            
            for i, word in enumerate(chunks):
                collected_chunks.append(word)
                
                # Update message every 5 words or at the end
                if i % 5 == 0 or i == len(chunks) - 1:
                    current_response = ' '.join(collected_chunks)
                    try:
                        await response_message.edit_text(current_response)
                    except Exception:
                        continue
                    
                await asyncio.sleep(0.1)
            
            # Save conversation to history
            await self.save_conversation(
                update.effective_user.id,
                prompt,
                response_text,
                "assistant"  # Specify the role
            )
            
        except AssistantConnectionError:
            await response_message.edit_text("❌ Не удалось подключиться к AI ассистенту. Пожалуйста, попробуйте позже.")
        except AssistantTimeoutError:
            await response_message.edit_text("⏱️ Превышено время ожидания ответа от AI ассистента.")
        except AssistantResponseError as e:
            await response_message.edit_text(f"❌ Ошибка в ответе AI ассистента: {str(e)}")
        except AssistantAPIError as e:
            await response_message.edit_text(f"❌ Ошибка AI ассистента: {str(e)}")
        except Exception as e:
            await response_message.edit_text(f"❌ Неожиданная ошибка: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        user_id = update.effective_user.id
        text_settings = await self.get_user_settings(user_id)
        
        if text_settings.use_assistant and text_settings.assistant_url:
            # Use AI assistant mode
            await self.stream_assistant_response(
                update,
                text_settings.assistant_url,
                update.message.text
            )
        else:
            # Use OpenAI streaming mode
            await self.stream_openai_response(
                update,
                text_settings,
                update.message.text
            )

    async def get_conversation_history(self, 
                                     user_id: int, 
                                     limit: int = 10,
                                     assistant_type: Optional[str] = None) -> List[Dict]:
        """Get conversation history with optional filtering by assistant type"""
        import sqlite3
        
        with sqlite3.connect(self.message_history.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT message_text, role, timestamp, assistant_type
                FROM messages
                WHERE user_id = ?
            """
            params = [user_id]
            
            if assistant_type:
                query += " AND assistant_type = ?"
                params.append(assistant_type)
                
            query += """
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def run(self):
        """Run the bot"""
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main settings menu"""
        user_id = update.effective_user.id
        settings = await self.get_user_settings(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📝 Настройки текстовой модели", callback_data="text_settings")],
            [InlineKeyboardButton("🖼 Настройки генерации изображений", callback_data="image_settings")],
            [InlineKeyboardButton(
                f"🤖 AI Ассистент: {'Вкл' if settings.use_assistant else 'Выкл'}", 
                callback_data="toggle_assistant"
            )],
            [InlineKeyboardButton("❌ Закрыть", callback_data="cancel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "⚙️ Настройки бота:"
        
        if isinstance(update, CallbackQuery):
            await update.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return SettingsState.MAIN_MENU

    async def text_model_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show text model settings menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = await self.get_user_settings(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                f"🌐 Base URL: {settings.base_url}", 
                callback_data="set_base_url"
            )],
            [InlineKeyboardButton(
                f"🤖 Модель: {self.available_models.get(settings.model, settings.model)}", 
                callback_data="set_model"
            )],
            [InlineKeyboardButton(
                f"🌡️ Temperature: {settings.temperature}", 
                callback_data="set_temperature"
            )],
            [InlineKeyboardButton(
                f"📊 Max Tokens: {settings.max_tokens}", 
                callback_data="set_max_tokens"
            )],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Настройки текстовой модели:", reply_markup=reply_markup)
        
        return SettingsState.TEXT_MODEL

    async def handle_text_model_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text model setting selection"""
        query = update.callback_query
        await query.answer()
        
        setting = query.data.replace("set_", "")
        
        if setting == "base_url":
            await query.edit_message_text(
                "Введите новый Base URL для модели:\n"
                "Для отмены нажмите /cancel"
            )
            return SettingsState.BASE_URL
            
        elif setting == "model":
            keyboard = [
                [InlineKeyboardButton(name, callback_data=f"model_{model_id}")]
                for model_id, name in self.available_models.items()
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Выберите модель:", reply_markup=reply_markup)
            return SettingsState.MODEL_SELECTION
            
        elif setting == "temperature":
            keyboard = []
            for i in range(0, 11, 2):
                temp = i / 10
                keyboard.append([InlineKeyboardButton(f"{temp}", callback_data=f"temp_{temp}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Выберите температуру (0 - более точно, 1 - более креативно):",
                reply_markup=reply_markup
            )
            return SettingsState.TEMPERATURE
            
        elif setting == "max_tokens":
            await query.edit_message_text(
                "Введите максимальное количество токенов (минимум 150):\n"
                "Для отмены нажмите /cancel"
            )
            return SettingsState.MAX_TOKENS

    async def update_user_settings(self, user_id: int, updates: Dict[str, Any]):
        """Update user settings in database"""
        settings = await self.get_user_settings(user_id)
        
        for key, value in updates.items():
            setattr(settings, key, value)
        
        with sqlite3.connect(self.message_history.db_path) as conn:
            settings_json = json.dumps(settings.__dict__)
            conn.execute("""
                UPDATE users 
                SET text_settings = ?
                WHERE user_id = ?
            """, (settings_json, user_id))

    async def toggle_assistant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle AI assistant mode"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = await self.get_user_settings(user_id)
        
        if settings.use_assistant:
            # Disable assistant mode
            await self.update_user_settings(user_id, {
                "use_assistant": False,
                "assistant_url": None
            })
            return await self.show_settings_menu(update, context)
        else:
            # Enable assistant mode
            await query.edit_message_text(
                "Введите URL AI ассистента:\n"
                "Для отмены нажмите /cancel"
            )
            return SettingsState.ASSISTANT_URL

    async def cancel_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel settings conversation"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Настройки закрыты")
        return ConversationHandler.END

    async def image_model_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image model settings menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        settings = await self.get_image_settings(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                f"🌐 Base URL: {settings.base_url}", 
                callback_data="set_img_base_url"
            )],
            [InlineKeyboardButton(
                f"🎨 Модель: {self.available_image_models.get(settings.model, settings.model)}", 
                callback_data="set_img_model"
            )],
            [InlineKeyboardButton(
                f"📐 Размер: {self.image_sizes.get(settings.size, settings.size)}", 
                callback_data="set_img_size"
            )],
            [InlineKeyboardButton(
                f"✨ Качество: {self.image_qualities.get(settings.quality, settings.quality)}", 
                callback_data="set_img_quality"
            )],
            [InlineKeyboardButton(
                f"🎭 Стиль: {self.image_styles.get(settings.style, settings.style)}", 
                callback_data="set_img_style"
            )],
            [InlineKeyboardButton(
                f"HDR: {'Вкл' if settings.hdr else 'Выкл'}", 
                callback_data="toggle_img_hdr"
            )],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Настройки генерации изображений:", reply_markup=reply_markup)
        
        return SettingsState.IMAGE_MENU

if __name__ == "__main__":
    bot = GPTBot()
    bot.run() 