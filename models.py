from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class TextModelSettings:
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    assistant_url: Optional[str] = None
    use_assistant: bool = False

@dataclass
class ImageModelSettings:
    base_url: str
    model: str
    size: str = "1024x1024"
    quality: str = "standard"
    style: str = "natural"
    hdr: bool = False

@dataclass
class UserMessage:
    user_id: int
    message_text: str
    timestamp: datetime
    role: str = "user"

@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    text_settings: TextModelSettings
    image_settings: ImageModelSettings
    created_at: datetime = datetime.now()

class MessageHistory:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize database tables with enhanced schema"""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    text_settings TEXT,
                    image_settings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    role TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assistant_type TEXT DEFAULT 'gpt',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_timestamp 
                ON messages(user_id, timestamp)
            """) 