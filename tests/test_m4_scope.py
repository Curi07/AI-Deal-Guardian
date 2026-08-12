import pytest
from app.schemas.deal import Deal, Scope, Project, Commercial, Timeline, Decision, SourceType
from app.schemas.analysis import ScopeImpact
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService

def build_mock_scope_diff(added=None, removed=None, changed=None, conflicting=None, unchanged=None, classification=ScopeImpact.IN_SCOPE, commercial_level="low", recommended_action="ask"):
    return {
        "added": added or [],
        "removed": removed or [],
        "changed": changed or [],
        "conflicting": conflicting or [],
        "unchanged": unchanged or [],
        "classification": classification,
        "evidence": ["test evidence"],
        "commercial_impact": {"level": commercial_level, "reason": "test", "pricing_action": "test"},
        "recommended_action": recommended_action
    }

def test_m4_new_feature():
    mock = build_mock_scope_diff(added=["WhatsApp"], classification=ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, commercial_level="medium")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["Landing page", "Contact form"]))
    diff = service.analyze_scope_guard(deal, "Can you also add WhatsApp?")
    assert "WhatsApp" in diff.added
    assert diff.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert diff.commercial_impact.level == "medium"

def test_m4_existing_feature():
    mock = build_mock_scope_diff(unchanged=["Contact form"], classification=ScopeImpact.IN_SCOPE, commercial_level="none")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["Contact form"]))
    diff = service.analyze_scope_guard(deal, "Can we keep the contact form as planned?")
    assert "Contact form" in diff.unchanged
    assert diff.classification == ScopeImpact.IN_SCOPE
    assert diff.commercial_impact.level == "none"

def test_m4_explicit_exclusion():
    mock = build_mock_scope_diff(conflicting=["Maintenance"], classification=ScopeImpact.CONFLICT_WITH_EXCLUSION, commercial_level="high")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(exclusions=["Maintenance"]))
    diff = service.analyze_scope_guard(deal, "Can you include monthly maintenance?")
    assert "Maintenance" in diff.conflicting
    assert diff.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION
    assert diff.commercial_impact.level == "high"

def test_m4_unmentioned_feature():
    mock = build_mock_scope_diff(added=["Analytics"], classification=ScopeImpact.UNCLEAR, commercial_level="low")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["Landing page"]))
    diff = service.analyze_scope_guard(deal, "Can you add analytics?")
    assert diff.classification in [ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, ScopeImpact.UNCLEAR]
    assert diff.classification != ScopeImpact.CONFLICT_WITH_EXCLUSION

def test_m4_changed_quantity():
    mock_changed = [{"item": "sections", "before": "5", "after": "10", "evidence": []}]
    mock = build_mock_scope_diff(changed=mock_changed, classification=ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, commercial_level="medium")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["5 website sections"]))
    diff = service.analyze_scope_guard(deal, "I'd like 10 sections instead.")
    assert len(diff.changed) == 1
    assert diff.changed[0].before == "5"
    assert diff.changed[0].after == "10"

def test_m4_deadline_change():
    mock_changed = [{"item": "deadline", "before": "September 30", "after": "September 15", "evidence": []}]
    mock = build_mock_scope_diff(changed=mock_changed, classification=ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, commercial_level="high")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(timeline=Timeline(deadline="September 30"))
    diff = service.analyze_scope_guard(deal, "I need everything by September 15.")
    assert len(diff.changed) == 1
    assert diff.changed[0].item == "deadline"

def test_m4_revision_change():
    mock_changed = [{"item": "revisions", "before": "2", "after": "unlimited", "evidence": []}]
    mock = build_mock_scope_diff(changed=mock_changed, classification=ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, commercial_level="high")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["2 revisions"]))
    diff = service.analyze_scope_guard(deal, "Can we have unlimited revisions?")
    assert diff.changed[0].after == "unlimited"
    assert diff.commercial_impact.level == "high"

def test_m4_confirmed_decision_conflict():
    mock = build_mock_scope_diff(conflicting=["Stripe"], classification=ScopeImpact.CONFLICT_WITH_EXCLUSION)
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(decisions=[Decision(description="Use Mercado Pago", status="confirmed", source=SourceType.CLIENT, timestamp="2026-08-12")])
    diff = service.analyze_scope_guard(deal, "Let's use Stripe instead.")
    assert "Stripe" in diff.conflicting
    assert diff.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION

def test_m4_ambiguous_request():
    mock = build_mock_scope_diff(classification=ScopeImpact.UNCLEAR, recommended_action="ask_clarification")
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal(scope=Scope(deliverables=["Landing page"]))
    diff = service.analyze_scope_guard(deal, "Can you make it more like the other one?")
    assert diff.classification == ScopeImpact.UNCLEAR
    assert diff.recommended_action == "ask_clarification"

def test_m4_multiple_changes():
    mock_changed = [{"item": "deadline", "before": "September 30", "after": "September 15", "evidence": []}]
    mock = build_mock_scope_diff(
        added=["Admin dashboard"],
        conflicting=["Maintenance"],
        changed=mock_changed,
        classification=ScopeImpact.CONFLICT_WITH_EXCLUSION,
        commercial_level="high"
    )
    service = ExtractionService(MockLLMProvider(mock_response=mock))
    deal = Deal()
    diff = service.analyze_scope_guard(deal, "Can you add an admin dashboard and maintenance? Also, I need it by September 15.")
    assert "Admin dashboard" in diff.added
    assert "Maintenance" in diff.conflicting
    assert diff.changed[0].item == "deadline"
    assert diff.commercial_impact.level == "high"
