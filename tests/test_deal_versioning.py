import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.deal import Deal, Scope, Commercial, Timeline, Project
from app.schemas.analysis import ScopeImpact, StrategyMode
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService
from app.db.database import DealRepository

def test_deal_initial_version_and_revisions():
    repo = DealRepository()
    deal = Deal(
        project=Project(title="MVP Platform"),
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"], exclusions=["Admin dashboard"])
    )
    deal_id = repo.create_deal(deal)
    
    loaded_deal = repo.get_deal(deal_id)
    assert loaded_deal.version == "1.0"
    assert loaded_deal.revisions == []
    assert "Admin dashboard" in loaded_deal.scope.exclusions
    assert "Admin dashboard" not in loaded_deal.scope.deliverables


def test_unapproved_change_does_not_mutate_deal_memory():
    repo = DealRepository()
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"])
    )
    deal_id = repo.create_deal(deal)
    
    # Simulate analyzing a message asking for changes
    # ExtractionService should NOT mutate the Deal object or database
    scope_mock = {
        "added": ["Admin dashboard"],
        "removed": [],
        "changed": [],
        "conflicting": [],
        "unchanged": [],
        "classification": ScopeImpact.POTENTIALLY_OUT_OF_SCOPE,
        "evidence": ["New requirement"],
        "commercial_impact": {"level": "high", "reason": "New module", "pricing_action": "quote_separately"},
        "recommended_action": "Propose Phase 2"
    }
    partial_mock = {
        "intent": {"primary": "add_feature", "confidence": 0.95},
        "deal_context": {"relevant_requirements": ["Landing page"]}
    }
    stage2_mock = {
        "strategy": {"objective": "negotiate_scope", "recommended_action": "Upsell", "reasoning": [], "key_points": []},
        "response": {"draft": "Draft", "tone": "professional", "requires_review": True}
    }
    
    service = ExtractionService(MockLLMProvider(mock_response=[scope_mock, partial_mock, stage2_mock]))
    service.analyze_contextual_message(deal, "Add admin dashboard?", objective="negotiate_scope")
    
    # Reload from DB and verify Deal is unchanged at v1.0
    loaded_deal = repo.get_deal(deal_id)
    assert loaded_deal.version == "1.0"
    assert loaded_deal.scope.deliverables == ["Landing page", "Contact form"]
    assert len(loaded_deal.revisions) == 0


def test_explicit_deal_revision_increments_and_preserves_snapshot():
    repo = DealRepository()
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"], exclusions=["Admin dashboard"])
    )
    deal_id = repo.create_deal(deal)
    
    # Human action: Client accepted the change -> apply revision
    updated_deal = repo.apply_revision(
        deal_id=deal_id,
        added_deliverables=["Admin dashboard"],
        removed_exclusions=["Admin dashboard"],
        budget=1500,
        action="client_accepted_upsell",
        summary="Added Admin dashboard as Phase 2 (+500 USD)"
    )
    
    assert updated_deal.version == "1.1"
    assert "Admin dashboard" in updated_deal.scope.deliverables
    assert "Admin dashboard" not in updated_deal.scope.exclusions
    assert updated_deal.commercial.budget == 1500
    assert len(updated_deal.revisions) == 1
    
    # Verify previous version v1.0 snapshot is preserved
    rev1 = updated_deal.revisions[0]
    assert rev1.version == "1.0"
    assert rev1.action == "client_accepted_upsell"
    assert rev1.source == "human"
    assert rev1.timestamp is not None
    assert rev1.snapshot["scope"]["deliverables"] == ["Landing page", "Contact form"]
    assert rev1.snapshot["scope"]["exclusions"] == ["Admin dashboard"]
    assert rev1.snapshot["commercial"]["budget"] == 1000
    
    # Test second revision increment (v1.1 -> v1.2)
    updated_deal2 = repo.apply_revision(
        deal_id=deal_id,
        added_deliverables=["Reporting export"],
        action="client_accepted_scope_change",
        summary="Added reporting export"
    )
    assert updated_deal2.version == "1.2"
    assert len(updated_deal2.revisions) == 2
    assert updated_deal2.revisions[1].version == "1.1"
    assert "Admin dashboard" in updated_deal2.revisions[1].snapshot["scope"]["deliverables"]


def test_critical_case_v10_out_of_scope_becomes_in_scope_in_v11():
    """
    CRITICAL TEST CASE:
    Deal v1.0: Scope has Landing page, Contact form. Exclusions has Admin dashboard.
    1. Client message: "Could you also add an admin dashboard?"
       Scope Guard evaluates against v1.0 -> CONFLICT_WITH_EXCLUSION / POTENTIALLY_OUT_OF_SCOPE.
    2. User selects UPSELL -> draft generated -> client accepts change.
    3. Deal is updated to v1.1.
    4. Next client message: "Can you also improve the admin dashboard?"
       Scope Guard evaluates against v1.1 -> Evaluated as IN_SCOPE!
    """
    repo = DealRepository()
    deal_v10 = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        timeline=Timeline(deadline="2026-09-30"),
        scope=Scope(
            deliverables=["Landing page", "Contact form"],
            exclusions=["Admin dashboard"]
        )
    )
    deal_id = repo.create_deal(deal_v10)
    
    # 1. First request on v1.0 (Mock Scope Guard returning conflict / out of scope)
    scope_mock_v10 = {
        "added": ["Admin dashboard"],
        "removed": [],
        "changed": [],
        "conflicting": ["Admin dashboard"],
        "unchanged": ["Landing page", "Contact form"],
        "classification": ScopeImpact.CONFLICT_WITH_EXCLUSION,
        "evidence": ["Admin dashboard is explicitly excluded in v1.0"],
        "commercial_impact": {"level": "high", "reason": "Excluded feature requested", "pricing_action": "quote_separately"},
        "recommended_action": "Propose as Phase 2 add-on"
    }
    
    service = ExtractionService(MockLLMProvider(mock_response=[scope_mock_v10]))
    scope_diff_1 = service.analyze_scope_guard(deal_v10, "Could you also add an admin dashboard?")
    assert scope_diff_1.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION
    assert "Admin dashboard" in scope_diff_1.conflicting
    
    # 2. Human applies accepted change to v1.1
    deal_v11 = repo.apply_revision(
        deal_id=deal_id,
        added_deliverables=["Admin dashboard"],
        removed_exclusions=["Admin dashboard"],
        budget=1600,
        action="client_accepted_upsell_phase_2",
        summary="Client approved Admin dashboard Phase 2 for +$600"
    )
    assert deal_v11.version == "1.1"
    assert "Admin dashboard" in deal_v11.scope.deliverables
    assert "Admin dashboard" not in deal_v11.scope.exclusions
    
    # 3. Next request on v1.1: "Can you also improve the admin dashboard?"
    # Scope Guard now receives Deal v1.1 where "Admin dashboard" is an agreed deliverable
    scope_mock_v11 = {
        "added": [],
        "removed": [],
        "changed": [],
        "conflicting": [],
        "unchanged": ["Admin dashboard"],
        "classification": ScopeImpact.IN_SCOPE,
        "evidence": ["Admin dashboard is part of agreed scope in Deal v1.1"],
        "commercial_impact": {"level": "low", "reason": "Refinement within scope", "pricing_action": "absorb_or_refine"},
        "recommended_action": "Confirm requirement details and implement"
    }
    
    service2 = ExtractionService(MockLLMProvider(mock_response=[scope_mock_v11]))
    scope_diff_2 = service2.analyze_scope_guard(deal_v11, "Can you also improve the admin dashboard?")
    
    assert scope_diff_2.classification == ScopeImpact.IN_SCOPE
    assert "Admin dashboard" in scope_diff_2.unchanged


def test_api_revisions_endpoints():
    client = TestClient(app)
    repo = DealRepository()
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page"], exclusions=["Mobile app"])
    )
    deal_id = repo.create_deal(deal)
    
    # POST /api/deals/{deal_id}/revisions
    resp = client.post(
        f"/api/deals/{deal_id}/revisions",
        json={
            "action": "client_accepted_scope_change",
            "summary": "Added Mobile app to scope",
            "added_deliverables": ["Mobile app"],
            "removed_exclusions": ["Mobile app"],
            "budget": 2500
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.1"
    assert "Mobile app" in data["scope"]["deliverables"]
    assert "Mobile app" not in data["scope"]["exclusions"]
    assert data["commercial"]["budget"] == 2500
    assert len(data["revisions"]) == 1
    
    # GET /api/deals/{deal_id}/revisions
    resp_revs = client.get(f"/api/deals/{deal_id}/revisions")
    assert resp_revs.status_code == 200
    revs = resp_revs.json()
    assert len(revs) == 1
    assert revs[0]["version"] == "1.0"
    assert revs[0]["action"] == "client_accepted_scope_change"
