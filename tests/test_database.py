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


def test_list_deals_title_fallback_when_empty_string(tmp_path, monkeypatch):
    db_path = tmp_path / "test_fallback.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

    # Deal with empty title but populated description
    deal1 = Deal()
    deal1.project.title = ""
    deal1.project.description = "Full-stack web platform with Stripe"
    
    # Deal with empty title and empty description
    deal2 = Deal()
    deal2.project.title = ""
    deal2.project.description = ""

    repo = DealRepository()
    repo.create_deal(deal1)
    repo.create_deal(deal2)

    deals = repo.list_deals()
    assert len(deals) == 2
    # Newest deal first
    assert deals[0]["title"] == "Untitled Deal"
    assert deals[1]["title"] == "Full-stack web platform with Stripe"


def test_project_status_default_waiting_message_and_update(tmp_path, monkeypatch):
    from app.schemas.deal import ProjectStatus, PreflightStatus
    
    db_path = tmp_path / "test_status.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

    # 1. New deal starts with waiting_message
    deal = Deal()
    deal.client.name = "Martín Fernández"
    deal.client.company = "Clínica NovaSalud"
    deal.project.title = "Plataforma clínica"
    deal.preflight.status = PreflightStatus.DO_NOT_QUOTE
    deal.preflight.risk_score = 85
    assert deal.status == ProjectStatus.WAITING_MESSAGE
    
    repo = DealRepository()
    deal_id = repo.create_deal(deal)
    
    # 2. Check list_deals
    deals = repo.list_deals()
    assert len(deals) == 1
    assert deals[0]["status"] == "waiting_message"
    assert deals[0]["preflight_status"] == "do_not_quote"
    assert deals[0]["client"] == "Martín Fernández"
    assert deals[0]["company"] == "Clínica NovaSalud"
    
    # 3. Update status to in_progress
    repo.update_status(deal_id, "in_progress")
    updated = repo.get_deal(deal_id)
    assert updated.status == ProjectStatus.IN_PROGRESS
    # Preflight and risk score untouched
    assert updated.preflight.status == PreflightStatus.DO_NOT_QUOTE
    assert updated.preflight.risk_score == 85
    
    # 4. Update status to rejected
    repo.update_status(deal_id, "rejected")
    assert repo.get_deal(deal_id).status == ProjectStatus.REJECTED
    
    # 5. Update status to completed
    repo.update_status(deal_id, "completed")
    assert repo.get_deal(deal_id).status == ProjectStatus.COMPLETED


def test_legacy_deals_without_status_load_safely(tmp_path, monkeypatch):
    db_path = tmp_path / "test_legacy.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    
    # Legacy data without status or client company
    legacy_data = json.dumps({
        "project": {"title": "Legacy Project"},
        "client": {"name": "Old Client"},
        "preflight": {"status": "ready", "risk_score": 10}
    })
    conn.execute("INSERT INTO deals (id, data) VALUES ('legacy-1', ?)", (legacy_data,))
    conn.commit()
    conn.close()

    repo = DealRepository()
    deals = repo.list_deals()
    assert len(deals) == 1
    assert deals[0]["status"] == "waiting_message"
    assert deals[0]["preflight_status"] == "ready"
    assert deals[0]["client"] == "Old Client"
    assert deals[0]["company"] == ""


