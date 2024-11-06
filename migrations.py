from models import Base
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
        
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully") 