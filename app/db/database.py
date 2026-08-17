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

    def list_deals(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, data FROM deals ORDER BY rowid DESC").fetchall()
            deals = []
            for row in rows:
                data = json.loads(row["data"])
                
                # Extract summary info safely
                project = data.get("project", {})
                title = (project.get("title") or "").strip() or (project.get("description") or "").strip() or (project.get("type") or "").strip() or "Untitled Deal"
                client_obj = data.get("client", {})
                client = client_obj.get("name") or "Unknown"
                company = client_obj.get("company") or ""
                
                commercial = data.get("commercial", {})
                budget = commercial.get("budget", 0)
                currency = commercial.get("currency", "USD")
                
                timeline = data.get("timeline", {})
                deadline = timeline.get("deadline", "TBD")
                
                # Independent project status and preflight status
                project_status = data.get("status") or "waiting_message"
                preflight = data.get("preflight", {})
                preflight_status = preflight.get("status", "needs_clarification")
                
                deals.append({
                    "id": row["id"],
                    "title": title,
                    "client": client,
                    "company": company,
                    "budget": budget,
                    "currency": currency,
                    "deadline": deadline,
                    "status": project_status,
                    "preflight_status": preflight_status
                })
            return deals
        finally:
            conn.close()

    def update_status(self, deal_id: str, status: str) -> None:
        deal = self.get_deal(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
            
        from datetime import datetime, timezone
        from app.schemas.deal import ProjectStatus
        
        deal.status = ProjectStatus(status)
        
        deal_data = deal.model_dump_json()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE deals SET data = ?, updated_at = ? WHERE id = ?",
                (deal_data, timestamp, deal_id)
            )
            conn.commit()
        finally:
            conn.close()

    def add_review(self, deal_id: str, status: str, draft: str) -> str:
        deal = self.get_deal(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
            
        from datetime import datetime, timezone
        from app.schemas.deal import Review, ReviewStatus
        
        review_id = f"REV-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        review = Review(
            id=review_id,
            status=ReviewStatus(status),
            draft=draft,
            timestamp=timestamp
        )
        
        deal.reviews.append(review)
        
        deal_data = deal.model_dump_json()
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE deals SET data = ?, updated_at = ? WHERE id = ?",
                (deal_data, timestamp, deal_id)
            )
            conn.commit()
        finally:
            conn.close()
            
        return review_id

    def delete_deal(self, deal_id: str) -> bool:
        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM deals WHERE id = ?", (deal_id,)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM messages WHERE deal_id = ?", (deal_id,))
            conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
            conn.commit()
            return True
        finally:
            conn.close()

