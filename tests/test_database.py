import pytest
import sqlite3
import json
from app.db.database import DealRepository, get_connection
from app.schemas.deal import Deal

def test_list_deals_extracts_client_correctly(tmp_path, monkeypatch):
    # Setup test database
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    # Init schema
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

    # Create a deal with proper schema
    deal = Deal()
    deal.client.name = "Acme Corp"
    deal.project.title = "Redesign"
    
    repo = DealRepository()
    repo.create_deal(deal)
    
    # Verify list_deals
    deals = repo.list_deals()
    assert len(deals) == 1
    assert deals[0]["client"] == "Acme Corp"
    assert deals[0]["title"] == "Redesign"
