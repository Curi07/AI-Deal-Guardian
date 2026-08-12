import sqlite3
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def init_db():
    db_path = settings.database_path
    logger.info(f"Initializing SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS deals (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(deal_id) REFERENCES deals(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialization complete.")

if __name__ == "__main__":
    init_db()
