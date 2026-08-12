import sqlite3
import json
import uuid
from typing import Optional, List, Dict, Any
from app.schemas.deal import Deal, Message

from app.config import settings

def get_connection():
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    return conn

class DealRepository:
    def create_deal(self, deal: Deal) -> str:
        deal_data = deal.model_dump_json()
        deal_id = str(uuid.uuid4())
        
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO deals (id, data) VALUES (?, ?)",
                (deal_id, deal_data)
            )
            conn.commit()
        finally:
            conn.close()
        return deal_id
        
    def get_deal(self, deal_id: str) -> Optional[Deal]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT data FROM deals WHERE id = ?", (deal_id,)).fetchone()
            if not row:
                return None
            
            deal_data = json.loads(row["data"])
            
            messages_rows = conn.execute(
                "SELECT id, sender, content, timestamp FROM messages WHERE deal_id = ? ORDER BY timestamp ASC",
                (deal_id,)
            ).fetchall()
            
            deal = Deal(**deal_data)
            deal.id = deal_id
            
            for m_row in messages_rows:
                deal.messages.append(Message(
                    id=m_row["id"],
                    timestamp=m_row["timestamp"],
                    sender=m_row["sender"],
                    content=m_row["content"]
                ))
            return deal
        finally:
            conn.close()
            
    def append_message(self, deal_id: str, sender: str, content: str) -> str:
        if not self.get_deal(deal_id):
            raise ValueError(f"Deal {deal_id} not found")
            
        msg_id = f"MSG-{uuid.uuid4().hex[:8]}"
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO messages (id, deal_id, sender, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (msg_id, deal_id, sender, content, timestamp)
            )
            conn.commit()
        finally:
            conn.close()
        return msg_id
