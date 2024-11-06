from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

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

class DBUser(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    text_settings = Column(Text)
    image_settings = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class DBMessage(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    message_text = Column(Text)
    role = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    assistant_type = Column(String, default='gpt')

class MessageHistory:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        return self.SessionLocal()