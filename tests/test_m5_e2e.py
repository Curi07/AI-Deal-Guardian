import pytest
from unittest.mock import patch
from app.services.extraction import ExtractionService, AnalyzeRequest
from app.db.database import DealRepository
from app.schemas.deal import Deal
from app.schemas.analysis import ScopeImpact, ScopeDiff, MessageAnalysis, Strategy, ResponseDraft, IntentAnalysis, DealContextSummary
from app.llm.provider import OpenAIProvider
from app.db.database import DealRepository
from app.db.init_db import init_db
import json

def test_m5_e2e_flow():
    init_db()
    repo = DealRepository()
    from app.config import settings
    settings.openai_api_key = "dummy"
    provider = OpenAIProvider()
    service = ExtractionService(provider)
    
    # 1. New Deal (Analyze Brief)
    mock_preflight_data = {
        "preflight": {
            "status": "ready",
            "risk_score": 25,
            "confidence_score": 90,
            "unknowns": [],
            "blocking_unknowns": 0,
            "questions_to_ask": []
        },
        "project": {"title": "Test Project", "description": ""},
        "commercial": {"budget": 500, "currency": "USD", "payment_terms": "upon completion"},
        "timeline": {"deadline": "10 days", "deadline_type": "explicit"},
        "scope": {"deliverables": ["Landing page"], "exclusions": ["Maintenance"]},
        "decisions": [],
        "messages": []
    }
    
    with patch("app.llm.provider.OpenAIProvider.generate_structured") as mock_generate:
        mock_generate.return_value = Deal(**mock_preflight_data)
        
        analyzed_deal = service.analyze_deal(AnalyzeRequest(message="Test brief", context=""))
        assert analyzed_deal.preflight.status == "ready"
        # 2. Save Deal
        deal_id = repo.create_deal(analyzed_deal)
        assert deal_id is not None

    # 3. Retrieve Deal (Deal Memory)
    retrieved_deal = repo.get_deal(deal_id)
    assert retrieved_deal.id == deal_id

    # 4. Analyze New Message (Scope Guard & Response Intelligence)
    mock_scope_diff = ScopeDiff(
        added=["Dashboard"],
        removed=[],
        changed=[],
        conflicting=["Maintenance"],
        unchanged=[],
        classification=ScopeImpact.CONFLICT_WITH_EXCLUSION,
        evidence=["Maintenance is excluded"],
        commercial_impact={"level": "high", "reason": "...", "pricing_action": "renegotiate_scope"},
        recommended_action="Do not accept"
    )
    
    class MockPartialMessageAnalysis:
        intent = IntentAnalysis(primary="new_requirement", confidence=0.9)
        deal_context = DealContextSummary()
        
    class MockStage2Result:
        strategy = Strategy(objective="negotiate_scope", recommended_action="Action", reasoning=[], key_points=[])
        response = ResponseDraft(draft="Draft response", tone="professional", requires_review=True)

    with patch("app.llm.provider.OpenAIProvider.generate_structured") as mock_gen_msg:
        mock_gen_msg.side_effect = [
            mock_scope_diff, 
            MockPartialMessageAnalysis(), 
            MockStage2Result()
        ]
        
        resp_data = service.analyze_contextual_message(
            deal=retrieved_deal, 
            message="Add dashboard and maintenance", 
            objective="negotiate_scope", 
            tone="professional"
        )
        
        assert resp_data.message_analysis.scope_guard.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION
        assert "Maintenance" in resp_data.message_analysis.scope_guard.conflicting
        assert resp_data.response.draft == "Draft response"

