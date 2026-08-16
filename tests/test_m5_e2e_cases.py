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

