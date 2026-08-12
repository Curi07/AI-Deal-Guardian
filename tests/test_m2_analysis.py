import pytest
from app.schemas.deal import Deal, Scope, Project, Commercial, Timeline
from app.schemas.analysis import ScopeImpact
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService

def test_contextual_analysis_unmentioned_scope():
    # Represents Step 4 and 5 in the prompt
    mock_analysis_data = [
        {
            "added": [], "removed": [], "changed": [], "conflicting": [], "unchanged": [],
            "classification": "potentially_out_of_scope", 
            "evidence": [], 
            "commercial_impact": {"level": "high", "reason": "...", "pricing_action": "consider_additional_fee"},
            "recommended_action": "test"
        },
        {
            "intent": {"primary": "new_requirement", "confidence": 0.9},
            "deal_context": {}
        },
        {
            "strategy": {
                "objective": "negotiate_scope", 
                "recommended_action": "...", 
                "reasoning": [], 
                "key_points": []
            },
            "response": {"draft": "...", "tone": "professional", "requires_review": True}
        }
    ]
    
    provider = MockLLMProvider(mock_response=mock_analysis_data)
    service = ExtractionService(provider)
    
    deal = Deal(
        project=Project(title="E-commerce website"),
        commercial=Commercial(budget=1200),
        timeline=Timeline(deadline="30 days", deadline_type="explicit"),
        scope=Scope(deliverables=["Landing page", "Product catalog", "Contact form"], exclusions=["Maintenance"])
    )
    
    analysis = service.analyze_contextual_message(deal, "Can you also add WhatsApp integration?", objective="negotiate_scope")
    
    assert analysis.message_analysis.scope_guard.classification in [ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, ScopeImpact.UNCLEAR]

def test_contextual_analysis_explicit_exclusion():
    mock_analysis_data = [
        {
            "added": [], "removed": [], "changed": [], "conflicting": [], "unchanged": [],
            "classification": "conflict_with_exclusion",
            "evidence": ["Client requested maintenance, which is explicitly excluded."],
            "commercial_impact": {"level": "high", "reason": "...", "pricing_action": "consider_additional_fee"},
            "recommended_action": "test"
        },
        {
            "intent": {"primary": "new_requirement", "confidence": 0.9},
            "deal_context": {}
        },
        {
            "strategy": {
                "objective": "defend_price",
                "recommended_action": "...",
                "reasoning": [],
                "key_points": []
            },
            "response": {"draft": "...", "tone": "professional", "requires_review": True}
        }
    ]
    
    provider = MockLLMProvider(mock_response=mock_analysis_data)
    service = ExtractionService(provider)
    
    deal = Deal(
        scope=Scope(exclusions=["Maintenance"])
    )
    
    analysis = service.analyze_contextual_message(deal, "Can you also provide monthly maintenance?", objective="defend_price")
    
    assert analysis.message_analysis.scope_guard.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION
    assert len(analysis.message_analysis.scope_guard.evidence) > 0

def test_contextual_analysis_conflict_with_confirmed_decision():
    from app.schemas.deal import Decision, SourceType
    mock_analysis_data = [
        {
            "added": [], "removed": [], "changed": [], "conflicting": ["Payment Gateway"], "unchanged": [],
            "classification": "conflict_with_exclusion",
            "evidence": ["Client requested Stripe, but it was already confirmed to use Mercado Pago."],
            "commercial_impact": {"level": "low", "reason": "...", "pricing_action": "none"},
            "recommended_action": "test"
        },
        {
            "intent": {"primary": "request_change", "confidence": 0.9},
            "deal_context": {}
        },
        {
            "strategy": {
                "objective": "ask_clarification",
                "recommended_action": "...",
                "reasoning": [],
                "key_points": []
            },
            "response": {"draft": "...", "tone": "professional", "requires_review": True}
        }
    ]
    
    provider = MockLLMProvider(mock_response=mock_analysis_data)
    service = ExtractionService(provider)
    
    deal = Deal(
        decisions=[Decision(description="Use Mercado Pago", source=SourceType.CLIENT, timestamp="2026-08-12", status="confirmed")]
    )
    
    analysis = service.analyze_contextual_message(deal, "Can we use Stripe instead?", objective="ask_clarification")
    
    assert "Stripe" in analysis.message_analysis.scope_guard.evidence[0]

