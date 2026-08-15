import pytest
from app.services.extraction import ExtractionService
from app.schemas.deal import Deal, Timeline, Commercial, Scope
from app.schemas.analysis import ScopeImpact
from app.llm.provider import LLMProvider
from typing import Type, Any

class ScenarioMockProvider(LLMProvider):
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.call_count = 0

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[Any]) -> Any:
        self.call_count += 1
        model_name = response_model.__name__

        if model_name == "ScopeDiff":
            if self.scenario == "IN_SCOPE":
                return response_model(**{
                    "added": [], "removed": [], "changed": [{"item": "hero text", "before": "old", "after": "new"}],
                    "conflicting": [], "unchanged": ["Landing page", "Contact form", "Responsive design"],
                    "classification": "in_scope",
                    "commercial_impact": {"level": "none", "reason": "Minor copy change", "pricing_action": "none"},
                    "recommended_action": "Accept the changes", "evidence": []
                })
            elif self.scenario == "OUT_OF_SCOPE":
                return response_model(**{
                    "added": ["Dashboard for logged-in users"], "removed": [], "changed": [],
                    "conflicting": [], "unchanged": [],
                    "classification": "potentially_out_of_scope",
                    "commercial_impact": {"level": "medium", "reason": "Requires backend", "pricing_action": "increase"},
                    "recommended_action": "Renegotiate", "evidence": []
                })
            elif self.scenario == "OUT_OF_SCOPE_RECURRING":
                return response_model(**{
                    "added": ["Dashboard", "Monthly maintenance"], "removed": [], "changed": [],
                    "conflicting": [], "unchanged": [],
                    "classification": "potentially_out_of_scope",
                    "commercial_impact": {"level": "high", "reason": "Recurring work", "pricing_action": "retainer"},
                    "recommended_action": "Renegotiate budget", "evidence": []
                })
            elif self.scenario == "DEADLINE_CHANGE":
                return response_model(**{
                    "added": [], "removed": [], "changed": [{"item": "deadline", "before": "10 days", "after": "5 days"}],
                    "conflicting": [], "unchanged": [],
                    "classification": "potentially_out_of_scope",
                    "commercial_impact": {"level": "high", "reason": "Rush delivery", "pricing_action": "rush_fee"},
                    "recommended_action": "Review timeline", "evidence": []
                })
            elif self.scenario == "BUDGET_REDUCTION":
                return response_model(**{
                    "added": [], "removed": [], "changed": [{"item": "budget", "before": "$500", "after": "$300"}],
                    "conflicting": [], "unchanged": [],
                    "classification": "potentially_out_of_scope",
                    "commercial_impact": {"level": "high", "reason": "Budget reduced", "pricing_action": "decrease_scope"},
                    "recommended_action": "Renegotiate scope", "evidence": []
                })
            elif self.scenario == "AMBIGUOUS_REQUEST":
                return response_model(**{
                    "added": ["More advanced features"], "removed": [], "changed": [],
                    "conflicting": [], "unchanged": [],
                    "classification": "unclear",
                    "commercial_impact": {"level": "unknown", "reason": "Unclear request", "pricing_action": "clarify"},
                    "recommended_action": "Ask for clarification", "evidence": []
                })
            elif self.scenario == "MULTIPLE_CHANGES":
                return response_model(**{
                    "added": ["Dashboard", "Monthly maintenance"], "removed": [], 
                    "changed": [{"item": "deadline", "before": "10 days", "after": "5 days"}, {"item": "budget", "before": "$500", "after": "$400"}],
                    "conflicting": [], "unchanged": [],
                    "classification": "potentially_out_of_scope",
                    "commercial_impact": {"level": "high", "reason": "Multiple major changes", "pricing_action": "renegotiate_all"},
                    "recommended_action": "Renegotiate everything", "evidence": []
                })
            elif self.scenario == "NO_MATERIAL_CHANGE":
                return response_model(**{
                    "added": [], "removed": [], "changed": [],
                    "conflicting": [], "unchanged": [],
                    "classification": "not_applicable",
                    "commercial_impact": {"level": "none", "reason": "Just acknowledging", "pricing_action": "none"},
                    "recommended_action": "Acknowledge", "evidence": []
                })
            elif self.scenario == "EXCLUSION_CONFLICT":
                return response_model(**{
                    "added": ["Monthly maintenance"], "removed": [], "changed": [],
                    "conflicting": ["Maintenance"], "unchanged": [],
                    "classification": "conflict_with_exclusion",
                    "commercial_impact": {"level": "high", "reason": "Requested explicitly excluded item", "pricing_action": "new_contract"},
                    "recommended_action": "Reject or renegotiate", "evidence": []
                })
        
        elif model_name == "PartialMessageAnalysis":
            return response_model(**{
                "intent": {"primary": "update", "confidence": 0.9},
                "deal_context": {"relevant_requirements": [], "relevant_exclusions": [], "relevant_decisions": [], "relevant_assumptions": [], "relevant_messages": []}
            })
            
        elif model_name == "Stage2Result":
            return response_model(**{
                "strategy": {"objective": "handle_request", "recommended_action": "reply", "reasoning": [], "key_points": []},
                "response": {"draft": "Here is a response.", "tone": "professional", "requires_review": True}
            })
        
        return response_model()

@pytest.fixture
def base_deal():
    return Deal(
        commercial=Commercial(budget=500.0, currency="USD"),
        timeline=Timeline(deadline="10 days"),
        scope=Scope(deliverables=["Landing page", "Contact form", "Responsive design"], exclusions=[], assumptions=[])
    )

def test_in_scope(base_deal):
    service = ExtractionService(ScenarioMockProvider("IN_SCOPE"))
    result = service.analyze_contextual_message(base_deal, "Can you change the text in the hero section and update the contact email?", "reply")
    assert result.message_analysis.scope_guard.classification == ScopeImpact.IN_SCOPE
    assert result.message_analysis.scope_guard.commercial_impact.level == "none"

def test_out_of_scope(base_deal):
    service = ExtractionService(ScenarioMockProvider("OUT_OF_SCOPE"))
    result = service.analyze_contextual_message(base_deal, "Can you also add a dashboard for logged-in users?", "reply")
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert "Dashboard for logged-in users" in result.message_analysis.scope_guard.added
    assert result.message_analysis.scope_guard.commercial_impact.level in ["medium", "high"]
    assert result.response.requires_review is True

def test_out_of_scope_recurring(base_deal):
    service = ExtractionService(ScenarioMockProvider("OUT_OF_SCOPE_RECURRING"))
    result = service.analyze_contextual_message(base_deal, "Can you also add a dashboard and provide monthly maintenance?", "reply")
    assert "Dashboard" in result.message_analysis.scope_guard.added
    assert "Monthly maintenance" in result.message_analysis.scope_guard.added
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert result.message_analysis.scope_guard.commercial_impact.level == "high"
    assert result.response.requires_review is True

def test_deadline_change(base_deal):
    service = ExtractionService(ScenarioMockProvider("DEADLINE_CHANGE"))
    result = service.analyze_contextual_message(base_deal, "Can you deliver it in 5 days instead of 10?", "reply")
    assert any(c.item == "deadline" for c in result.message_analysis.scope_guard.changed)
    assert result.message_analysis.scope_guard.commercial_impact.level == "high"
    assert result.response.requires_review is True

def test_budget_reduction(base_deal):
    service = ExtractionService(ScenarioMockProvider("BUDGET_REDUCTION"))
    result = service.analyze_contextual_message(base_deal, "I need everything we discussed, but my maximum budget is now $300.", "reply")
    assert any(c.item == "budget" for c in result.message_analysis.scope_guard.changed)
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert result.message_analysis.scope_guard.commercial_impact.level == "high"

def test_ambiguous_request(base_deal):
    service = ExtractionService(ScenarioMockProvider("AMBIGUOUS_REQUEST"))
    result = service.analyze_contextual_message(base_deal, "Can you make it more advanced?", "reply")
    assert result.message_analysis.scope_guard.classification == ScopeImpact.UNCLEAR

def test_multiple_changes(base_deal):
    service = ExtractionService(ScenarioMockProvider("MULTIPLE_CHANGES"))
    result = service.analyze_contextual_message(base_deal, "I'd like a dashboard, monthly maintenance, delivery in 5 days, and my maximum budget is $400.", "reply")
    assert len(result.message_analysis.scope_guard.added) == 2
    assert len(result.message_analysis.scope_guard.changed) == 2
    assert result.message_analysis.scope_guard.commercial_impact.level == "high"
    assert result.response.requires_review is True

def test_no_material_change(base_deal):
    service = ExtractionService(ScenarioMockProvider("NO_MATERIAL_CHANGE"))
    result = service.analyze_contextual_message(base_deal, "Thanks, everything looks good. I'll review the proposal and get back to you.", "reply")
    assert result.message_analysis.scope_guard.classification == ScopeImpact.NOT_APPLICABLE
    assert result.message_analysis.scope_guard.commercial_impact.level == "none"

def test_exclusion_conflict(base_deal):
    base_deal.scope.exclusions = ["Maintenance"]
    service = ExtractionService(ScenarioMockProvider("EXCLUSION_CONFLICT"))
    result = service.analyze_contextual_message(base_deal, "Can you provide monthly maintenance after launch?", "reply")
    assert result.message_analysis.scope_guard.classification == ScopeImpact.CONFLICT_WITH_EXCLUSION
    assert "Maintenance" in result.message_analysis.scope_guard.conflicting
    assert result.message_analysis.scope_guard.commercial_impact.level == "high"
