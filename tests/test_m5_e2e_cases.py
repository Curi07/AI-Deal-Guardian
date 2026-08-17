import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db
from app.schemas.analysis import ScopeImpact, ScopeDiff, MessageAnalysis, Strategy, ResponseDraft, IntentAnalysis, DealContextSummary
import json
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    from app.config import settings
    settings.openai_api_key = "dummy"
    yield

@patch("app.llm.provider.OpenAIProvider.generate_structured")
def test_case_a_scope_creep(mock_generate):
    # CASO A — Scope creep
    # Input: "Could you also add an admin dashboard?"
    
    # 1. Create Deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Build a website with a landing page, contact form and admin-free CMS."},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": ["Landing page", "Contact form", "Admin-free CMS"]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    deal_id = create_res.json()["deal_id"]

    # 2. Mock LLM structured response to simulate AI understanding Scope Creep
    scope_diff = ScopeDiff(
        classification=ScopeImpact.POTENTIALLY_OUT_OF_SCOPE,
        added=["Admin dashboard"],
        removed=[],
        changed=[],
        conflicting=[],
        unchanged=[],
        evidence=["Client requested an admin dashboard"],
        commercial_impact={"level": "high", "reason": "Requires backend and frontend effort", "pricing_action": "renegotiate"},
        recommended_action="Clarify scope"
    )

    class MockPartialMessageAnalysis:
        intent = IntentAnalysis(primary="add_feature", confidence=0.9, secondary=None)
        deal_context = DealContextSummary(relevant_requirements=[], relevant_exclusions=[], relevant_decisions=[], relevant_assumptions=[], relevant_messages=[])

    class MockStage2Result:
        strategy = Strategy(objective="negotiate_scope", recommended_action="Explain out of scope", reasoning=[], key_points=[])
        response = ResponseDraft(draft="We can add a dashboard but it costs more.", tone="professional", requires_review=False)

    mock_generate.side_effect = [
        scope_diff,
        MockPartialMessageAnalysis(),
        MockStage2Result()
    ]
    
    # 3. Analyze Message
    msg_payload = {
        "sender": "client",
        "content": "Could you also add an admin dashboard?",
        "objective": "negotiate_scope"
    }
    res = client.post(f"/api/deals/{deal_id}/analyze_message", json=msg_payload)
    assert res.status_code == 200
    analysis = res.json()
    
    # Assertions
    assert analysis["message_analysis"]["scope_guard"]["classification"] in ["out_of_scope", "potentially_out_of_scope"]
    assert analysis["message_analysis"]["scope_guard"]["commercial_impact"]["level"] in ["high", "critical"]
    assert analysis["response"]["requires_review"] is True # Deterministic rule applied!
    assert analysis["response"]["draft"] == "We can add a dashboard but it costs more."

@patch("app.llm.provider.OpenAIProvider.generate_structured")
def test_case_b_explicit_exclusion(mock_generate):
    # CASO B — Exclusión explícita
    # Input: "Can you also handle monthly maintenance?"
    
    # 1. Create Deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Project"},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": [], "exclusions": ["Monthly maintenance is explicitly excluded."]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    deal_id = create_res.json()["deal_id"]

    # 2. Mock LLM structured response to simulate AI understanding Exclusion Conflict
    scope_diff = ScopeDiff(
        classification=ScopeImpact.CONFLICT_WITH_EXCLUSION,
        added=[],
        removed=[],
        changed=[],
        conflicting=["Monthly maintenance"],
        unchanged=[],
        evidence=["Client requested maintenance which is excluded"],
        commercial_impact={"level": "high", "reason": "Monthly recurring cost", "pricing_action": "renegotiate"},
        recommended_action="Reject or renegotiate"
    )

    class MockPartialMessageAnalysis:
        intent = IntentAnalysis(primary="request_excluded_service", confidence=0.9, secondary=None)
        deal_context = DealContextSummary(relevant_requirements=[], relevant_exclusions=["Monthly maintenance is explicitly excluded."], relevant_decisions=[], relevant_assumptions=[], relevant_messages=[])

    class MockStage2Result:
        strategy = Strategy(objective="enforce_exclusions", recommended_action="Remind client of exclusion", reasoning=[], key_points=[])
        response = ResponseDraft(draft="Maintenance is excluded as per our agreement.", tone="professional", requires_review=False)

    mock_generate.side_effect = [
        scope_diff,
        MockPartialMessageAnalysis(),
        MockStage2Result()
    ]
    
    # 3. Analyze Message
    msg_payload = {
        "sender": "client",
        "content": "Can you also handle monthly maintenance?",
        "objective": "enforce_exclusions"
    }
    res = client.post(f"/api/deals/{deal_id}/analyze_message", json=msg_payload)
    assert res.status_code == 200
    analysis = res.json()
    
    # Assertions
    assert analysis["message_analysis"]["scope_guard"]["classification"] == "conflict_with_exclusion"
    assert "Monthly maintenance" in analysis["message_analysis"]["scope_guard"]["conflicting"]
    assert analysis["response"]["requires_review"] is True 


@patch("app.llm.provider.OpenAIProvider.generate_structured")
def test_case_c_price(mock_generate):
    # CASO C — Precio
    # Input: "Can you do it for USD 800?"
    
    # 1. Create Deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Project"},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": []},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    deal_id = create_res.json()["deal_id"]

    # 2. Mock LLM structured response to simulate AI understanding Price Negotiation
    scope_diff = ScopeDiff(
        classification=ScopeImpact.IN_SCOPE,
        added=[],
        removed=[],
        changed=[],
        conflicting=[],
        unchanged=[],
        evidence=["No scope changes"],
        commercial_impact={"level": "high", "reason": "Direct discount request", "pricing_action": "renegotiate"},
        recommended_action="Negotiate price"
    )

    class MockPartialMessageAnalysis:
        intent = IntentAnalysis(primary="price_negotiation", confidence=0.9, secondary=None)
        deal_context = DealContextSummary(relevant_requirements=[], relevant_exclusions=[], relevant_decisions=[], relevant_assumptions=[], relevant_messages=[])

    class MockStage2Result:
        strategy = Strategy(objective="hold_price", recommended_action="Reject discount", reasoning=[], key_points=[])
        response = ResponseDraft(draft="I cannot do 800.", tone="professional", requires_review=False)

    mock_generate.side_effect = [
        scope_diff,
        MockPartialMessageAnalysis(),
        MockStage2Result()
    ]
    
    # 3. Analyze Message
    msg_payload = {
        "sender": "client",
        "content": "Can you do it for USD 800?",
        "objective": "hold_price"
    }
    res = client.post(f"/api/deals/{deal_id}/analyze_message", json=msg_payload)
    assert res.status_code == 200
    analysis = res.json()
    
    # Assertions
    assert analysis["message_analysis"]["intent"]["primary"] == "price_negotiation"
    assert analysis["response"]["requires_review"] is True 


@patch("app.api.deals.get_llm_provider")
def test_case_deal_status_separation_e2e(mock_get_provider):
    from app.llm.provider import MockLLMProvider
    from app.schemas.deal import PreflightStatus, ProjectStatus
    
    # 1. Analyze Deal
    mock_deal_data = {
        "client": {},
        "project": {"title": "Plataforma clínica de turnos y pagos"},
        "commercial": {"budget": 8000, "currency": "USD"},
        "timeline": {"deadline": "2026-09-30"},
        "scope": {"deliverables": ["Turnos online", "Historias clínicas básicas", "Stripe"]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [{"title": "Integración Stripe", "description": "Detallar cuentas y comisiones", "severity": "high", "blocks_quote": True}],
        "risks": [{"description": "Seguridad de datos de pacientes", "severity": "high", "category": "technical", "evidence": []}],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {}
    }
    mock_get_provider.return_value = MockLLMProvider(mock_response=mock_deal_data)
    
    analyze_payload = {
        "message": "Necesito un sistema para gestión de turnos médicos online, historias clínicas básicas y cobro con Stripe.",
        "client_name": "Martín Fernández",
        "client_company": "Clínica NovaSalud",
        "budget": 8000,
        "currency": "USD",
        "deadline": "2026-09-30"
    }
    
    res = client.post("/api/deals/analyze", json=analyze_payload)
    assert res.status_code == 200
    deal_analyzed = res.json()["deal"]
    
    # Initial project status MUST be waiting_message, Preflight status is computed independently by RuleEngine
    assert deal_analyzed["status"] == "waiting_message"
    assert deal_analyzed["client"]["name"] == "Martín Fernández"
    assert deal_analyzed["client"]["company"] == "Clínica NovaSalud"
    assert deal_analyzed["preflight"]["status"] == "needs_clarification"
    
    # 2. Save Deal
    res_save = client.post("/api/deals", json=deal_analyzed)
    assert res_save.status_code == 200
    deal_id = res_save.json()["deal_id"]
    
    # 3. List deals in dashboard: check independent columns
    res_list = client.get("/api/deals")
    assert res_list.status_code == 200
    deals = res_list.json()
    created_deal = next(d for d in deals if d["id"] == deal_id)
    assert created_deal["status"] == "waiting_message"
    assert created_deal["preflight_status"] == "needs_clarification"
    assert created_deal["client"] == "Martín Fernández"
    assert created_deal["company"] == "Clínica NovaSalud"
    
    # 4. User manually switches project status to in_progress
    res_patch = client.patch(f"/api/deals/{deal_id}/status", json={"status": "in_progress"})
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "in_progress"
    
    # 5. Check deal memory: project status is in_progress, Preflight is STILL needs_clarification, Risk Score stays identical
    res_get = client.get(f"/api/deals/{deal_id}")
    assert res_get.status_code == 200
    deal_db = res_get.json()
    assert deal_db["status"] == "in_progress"
    assert deal_db["preflight"]["status"] == "needs_clarification"
    assert deal_db["preflight"]["risk_score"] == deal_analyzed["preflight"]["risk_score"]

 

