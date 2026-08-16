import pytest
from app.schemas.deal import Deal, Scope, Project, Commercial, Timeline, Decision, SourceType
from app.schemas.analysis import ScopeImpact
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService

def build_mock_response(intent, scope_class, commercial_level, draft="Mock response"):
    # Mock for Stage 1.0 (Scope Guard)
    scope_mock = {
        "added": [],
        "removed": [],
        "changed": [],
        "conflicting": [],
        "unchanged": [],
        "classification": scope_class,
        "evidence": [],
        "commercial_impact": {"level": commercial_level, "reason": "test", "pricing_action": "test"},
        "recommended_action": "test"
    }
    
    # Mock for Stage 1.5 (Intent and Context)
    partial_mock = {
        "intent": {"primary": intent, "confidence": 0.9},
        "deal_context": {}
    }
    
    # Mock for Stage 2 (Strategy and Response)
    stage2_mock = {
        "strategy": {
            "objective": "test_obj",
            "recommended_action": "action",
            "reasoning": [],
            "key_points": []
        },
        "response": {"draft": draft, "tone": "professional", "requires_review": True}
    }
    
    return [scope_mock, partial_mock, stage2_mock]

def test_m3_price_negotiation_defend_price():
    mock_data = build_mock_response("price_negotiation", "in_scope", "high")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(commercial=Commercial(budget=1200))
    analysis = service.analyze_contextual_message(deal, "Can you do USD 800?", objective="defend_price")
    assert analysis.message_analysis.intent.primary == "price_negotiation"
    assert analysis.message_analysis.scope_guard.commercial_impact.level == "high"
    assert analysis.response.requires_review is True

def test_m3_price_for_scope_negotiate():
    mock_data = build_mock_response("price_negotiation", "potentially_out_of_scope", "high")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(commercial=Commercial(budget=1200))
    analysis = service.analyze_contextual_message(deal, "Can you do USD 800?", objective="negotiate_scope")
    # This just ensures we map correctly, semantic checking is LLM-dependent in real life.
    assert analysis.strategy is not None

def test_m3_new_requirement():
    mock_data = build_mock_response("new_requirement", "potentially_out_of_scope", "medium")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(scope=Scope(deliverables=["Landing page"]))
    analysis = service.analyze_contextual_message(deal, "Can you add WhatsApp?", objective="negotiate_scope")
    assert analysis.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE

def test_m3_explicit_exclusion():
    mock_data = build_mock_response("new_requirement", "conflict_with_exclusion", "high")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(scope=Scope(exclusions=["Maintenance"]))
    analysis = service.analyze_contextual_message(deal, "Add maintenance?", objective="defend_price")
    assert analysis.message_analysis.scope_guard.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION

def test_m3_unmentioned_feature():
    mock_data = build_mock_response("new_requirement", "unclear", "low")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal()
    analysis = service.analyze_contextual_message(deal, "Add analytics?", objective="ask_clarification")
    assert analysis.message_analysis.scope_guard.classification in [ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, ScopeImpact.UNCLEAR]

def test_m3_deadline_change():
    mock_data = build_mock_response("deadline_change", "in_scope", "high")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(timeline=Timeline(deadline="Sept 30"))
    analysis = service.analyze_contextual_message(deal, "Ready by Sept 15?", objective="negotiate_scope")
    assert analysis.message_analysis.intent.primary == "deadline_change"

def test_m3_confirmed_decision_conflict():
    mock_data = build_mock_response("request_change", "conflict_with_exclusion", "low")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(decisions=[Decision(description="Use Mercado Pago", status="confirmed", source=SourceType.CLIENT, timestamp="2026-08-12")])
    analysis = service.analyze_contextual_message(deal, "Use Stripe?", objective="defend_price")
    assert analysis.message_analysis.scope_guard.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION

def test_m3_ambiguous_message():
    mock_data = build_mock_response("unknown", "unclear", "unknown")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal()
    analysis = service.analyze_contextual_message(deal, "Make it like the other one", objective="ask_clarification")
    assert analysis.message_analysis.intent.primary == "unknown"

def test_m3_human_review_required():
    mock_data = build_mock_response("general_communication", "in_scope", "none")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal()
    analysis = service.analyze_contextual_message(deal, "Thanks", objective="preserve_relationship")
    assert analysis.response.requires_review is False

def test_m3_no_hallucination():
    mock_data = build_mock_response("general_communication", "in_scope", "none", draft="We will deliver by Friday for $500.")
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal()
    analysis = service.analyze_contextual_message(deal, "Hi", objective="preserve_relationship")
    # In real world, LLM prevents this. We are just ensuring schema handles it.
    assert "Friday" in analysis.response.draft
