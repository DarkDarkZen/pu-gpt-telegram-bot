from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    # Telegram Bot Token
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("POSTGRES_URL", "")
    
    # Default Model Settings
    DEFAULT_TEXT_MODEL: str = "gpt-3.5-turbo"
    DEFAULT_IMAGE_MODEL: str = "dall-e-3"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 1000
    
    # AI Assistant Configuration
    AI_ASSISTANT_URL: Optional[str] = os.getenv("AI_ASSISTANT_URL")
    
    def validate(self):
        """Validate required configuration"""
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN is required")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")

config = BotConfig() 