import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.schemas.deal import PreflightStatus

client = TestClient(app)

@patch("app.api.deals.get_llm_provider")
def test_api_analyze_complex_brief(mock_get_provider):
    from app.llm.provider import MockLLMProvider
    
    mock_deal_data = {
        "client": {"name": "Demo Client", "company": "CoderCup Inc"},
        "project": {
            "title": "Sitio web con Auth, Stripe, Admin & Reportes",
            "type": "web",
            "description": "Full platform development"
        },
        "commercial": {"budget": 5000, "currency": "USD", "pricing_model": "fixed"},
        "timeline": {"deadline": "2024-09-15", "deadline_type": "explicit", "milestones": ["Week 2 deploy"]},
        "scope": {
            "deliverables": ["Authentication", "Dashboard Admin", "Stripe", "Reports"],
            "exclusions": ["iOS App"],
            "revisions": 2,
            "assumptions": []
        },
        "requirements": [
            {"id": "REQ-1", "description": "Auth system", "source": "client", "certainty": "explicit"},
            {"id": "REQ-2", "description": "Admin dashboard", "source": "client", "certainty": "explicit"},
            {"id": "REQ-3", "description": "Stripe payments", "source": "client", "certainty": "explicit"},
            {"id": "REQ-4", "description": "Reporting module", "source": "client", "certainty": "explicit"}
        ],
        "dependencies": [
            {"description": "Stripe credentials", "status": "pending", "owner": "client"}
        ],
        "unknowns": [
            {"description": "Report export format", "severity": "medium", "blocks_quote": False},
            {"description": "Payment methods in Stripe", "severity": "high", "blocks_quote": True}
        ],
        "risks": [
            {"description": "Aggressive timeline", "category": "timeline", "severity": "high", "evidence": ["Week 2 prod"]}
        ],
        "questions": [
            {"id": "Q-1", "question": "Which payment methods?", "reason": "Technical", "priority": "high", "blocks_quote": True}
        ],
        "decisions": [],
        "messages": [],
        "reviews": [],
        "preflight": {}
    }
    
    mock_get_provider.return_value = MockLLMProvider(mock_response=mock_deal_data)
    
    payload = {
        "message": "Necesito un sitio web con autenticación, dashboard admin, integración Stripe y reportes. Timeline 3 semanas. Requiero que todo esté en producción al final de semana 2.",
        "budget": 5000,
        "currency": "USD",
        "deadline": "2024-09-15"
    }
    
    response = client.post("/api/deals/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "deal" in data
    assert "preflight" in data
    assert "risks" in data
    assert "questions" in data
    assert data["deal"]["commercial"]["budget"] == 5000
    assert data["deal"]["commercial"]["currency"] == "USD"
    assert len(data["deal"]["requirements"]) == 4
    assert data["preflight"]["blocking_unknowns"] == 1


@patch("app.api.deals.get_llm_provider")
def test_api_analyze_llm_failure_handling(mock_get_provider):
    class FailingProvider:
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("LLM API rate limit exceeded")
            
    mock_get_provider.return_value = FailingProvider()
    
    payload = {
        "message": "Simple brief",
        "budget": 1000
    }
    
    response = client.post("/api/deals/analyze", json=payload)
    assert response.status_code == 502
    assert "LLM Provider error" in response.json()["detail"]


@patch("app.api.deals.get_llm_provider")
def test_api_analyze_with_client_fields(mock_get_provider):
    from app.llm.provider import MockLLMProvider
    
    mock_deal_data = {
        "client": {},
        "project": {"title": "Clínica Web"},
        "preflight": {}
    }
    mock_get_provider.return_value = MockLLMProvider(mock_response=mock_deal_data)
    
    payload = {
        "message": "Crear sitio web médico",
        "client_name": "Martín Fernández",
        "client_company": "Clínica NovaSalud"
    }
    
    response = client.post("/api/deals/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["deal"]["client"]["name"] == "Martín Fernández"
    assert data["deal"]["client"]["company"] == "Clínica NovaSalud"
    assert data["deal"]["status"] == "waiting_message"


def test_api_patch_deal_status(tmp_path, monkeypatch):
    from app.db.database import get_connection, DealRepository
    from app.schemas.deal import Deal, PreflightStatus
    
    db_path = tmp_path / "test_api_patch.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

    deal = Deal()
    deal.client.name = "Martín Fernández"
    deal.preflight.status = PreflightStatus.DO_NOT_QUOTE
    deal.preflight.risk_score = 90
    
    repo = DealRepository()
    deal_id = repo.create_deal(deal)
    
    # 1. Update to in_progress
    resp = client.patch(f"/api/deals/{deal_id}/status", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    
    deal_db = repo.get_deal(deal_id)
    assert deal_db.status.value == "in_progress"
    # Preflight and risk score stay identical
    assert deal_db.preflight.status == PreflightStatus.DO_NOT_QUOTE
    assert deal_db.preflight.risk_score == 90
    
    # 2. Update to invalid status -> 422
    resp_invalid = client.patch(f"/api/deals/{deal_id}/status", json={"status": "invalid_status"})
    assert resp_invalid.status_code == 422


def test_api_delete_deal_and_404_handling(tmp_path, monkeypatch):
    from app.db.database import get_connection, DealRepository
    from app.schemas.deal import Deal
    
    db_path = tmp_path / "test_api_delete.db"
    monkeypatch.setattr("app.db.database.settings", type('Settings', (), {'database_path': str(db_path)})())
    
    conn = get_connection()
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, data TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, deal_id TEXT, sender TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

    deal = Deal()
    deal.client.name = "Cliente para borrar"
    repo = DealRepository()
    deal_id = repo.create_deal(deal)

    # 1. Delete deal via API
    resp_delete = client.delete(f"/api/deals/{deal_id}")
    assert resp_delete.status_code == 200
    assert resp_delete.json()["id"] == deal_id

    # 2. Querying deleted deal returns 404
    resp_get = client.get(f"/api/deals/{deal_id}")
    assert resp_get.status_code == 404

    # 3. Deleting non-existent deal returns 404
    resp_del_again = client.delete(f"/api/deals/{deal_id}")
    assert resp_del_again.status_code == 404


