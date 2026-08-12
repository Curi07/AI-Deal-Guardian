import pytest
from app.schemas.deal import Deal, PreflightStatus
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService, AnalyzeRequest

def test_extraction_service_with_mock():
    mock_deal_data = {
        "client": {"name": "Test Client"},
        "project": {"title": "E-commerce", "type": "web", "description": "Needs a store"},
        "commercial": {"budget": 5000, "currency": "USD", "pricing_model": "fixed"},
        "timeline": {"deadline": "2026-08-30", "deadline_type": "explicit", "milestones": []},
        "scope": {"deliverables": ["Store"], "exclusions": [], "revisions": 2, "assumptions": []},
        "requirements": [],
        "dependencies": [],
        "unknowns": [
            {
                "description": "Payment gateway not specified",
                "severity": "high",
                "blocks_quote": True
            }
        ],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {}
    }
    
    provider = MockLLMProvider(mock_response=mock_deal_data)
    service = ExtractionService(provider)
    
    request = AnalyzeRequest(
        message="I need a store by August.",
        budget=1000 # Should override 5000
    )
    
    deal = service.analyze_deal(request)
    
    # Verify parsing works
    assert deal.client.name == "Test Client"
    
    # Verify request overrides
    assert deal.commercial.budget == 1000
    
    # Verify rule engine ran (1 blocking unknown -> NEEDS_CLARIFICATION)
    assert deal.preflight.status == PreflightStatus.NEEDS_CLARIFICATION
    assert deal.preflight.blocking_unknowns == 1
