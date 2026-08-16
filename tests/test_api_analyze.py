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
