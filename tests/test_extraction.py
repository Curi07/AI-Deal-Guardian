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


def test_extraction_complex_brief_with_multiple_requirements():
    complex_deal_data = {
        "client": {"name": "Complex Client", "company": "Tech Corp"},
        "project": {
            "title": "Web with Auth, Stripe, Admin & Reports",
            "type": "web",
            "description": "Sitio web con autenticacion, dashboard admin, integracion Stripe y reportes."
        },
        "commercial": {"budget": 5000, "currency": "USD", "pricing_model": "fixed"},
        "timeline": {"deadline": "2024-09-15", "deadline_type": "explicit", "milestones": ["Week 2: Production"]},
        "scope": {
            "deliverables": ["Authentication", "Admin Dashboard", "Stripe Integration", "Reporting Module"],
            "exclusions": ["Mobile App", "Legacy DB Migration"],
            "revisions": 2,
            "assumptions": ["Client provides Stripe API credentials"]
        },
        "requirements": [
            {"id": "REQ-1", "description": "User authentication", "source": "client", "certainty": "explicit"},
            {"id": "REQ-2", "description": "Admin dashboard", "source": "client", "certainty": "explicit"},
            {"id": "REQ-3", "description": "Stripe payment integration", "source": "client", "certainty": "explicit"},
            {"id": "REQ-4", "description": "Custom reporting module", "source": "client", "certainty": "explicit"},
            {"id": "REQ-5", "description": "Production deployment by end of week 2", "source": "client", "certainty": "explicit"}
        ],
        "dependencies": [
            {"description": "Stripe account access", "status": "pending", "owner": "client"}
        ],
        "unknowns": [
            {"description": "Types of reports required", "severity": "medium", "blocks_quote": False},
            {"description": "Specific Stripe payment methods (Cards, SEPA, etc.)", "severity": "high", "blocks_quote": True}
        ],
        "risks": [
            {"description": "Tight timeline for production deployment", "category": "timeline", "severity": "high", "evidence": ["Deploy at week 2 of 3"]}
        ],
        "questions": [
            {"id": "Q-1", "question": "Which specific report formats are needed (PDF/CSV)?", "reason": "Scope clarification", "priority": "medium", "blocks_quote": False},
            {"id": "Q-2", "question": "Which Stripe features are required (Subscriptions, One-off)?", "reason": "Technical dependency", "priority": "high", "blocks_quote": True}
        ],
        "decisions": [],
        "messages": [],
        "reviews": [],
        "preflight": {}
    }

    provider = MockLLMProvider(mock_response=complex_deal_data)
    service = ExtractionService(provider)

    request = AnalyzeRequest(
        message="Necesito un sitio web con autenticación, dashboard admin, integración Stripe y reportes. Timeline 3 semanas. Requiero que todo esté en producción al final de semana 2.",
        budget=5000,
        currency="USD",
        deadline="2024-09-15"
    )

    deal = service.analyze_deal(request)

    assert len(deal.requirements) == 5
    assert len(deal.scope.deliverables) == 4
    assert deal.commercial.budget == 5000
    assert deal.commercial.currency == "USD"
    assert deal.timeline.deadline == "2024-09-15"
    assert deal.preflight.status in [PreflightStatus.NEEDS_CLARIFICATION, PreflightStatus.DO_NOT_QUOTE]
    assert deal.preflight.blocking_unknowns == 1
    assert len(deal.questions) == 2
    assert len(deal.risks) == 1
