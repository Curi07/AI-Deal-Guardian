from typing import Any, Type

from app.llm.provider import LLMProvider
from app.schemas.deal import Commercial, Deal, Scope, Timeline
from app.services.extraction import ExtractionService


class MaterialProvider(LLMProvider):
    def __init__(self, item: str):
        self.item = item

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[Any]) -> Any:
        name = response_model.__name__
        if name == "ScopeDiff":
            return response_model(
                added=[], removed=[],
                changed=[{"item": self.item, "before": "old", "after": "new"}],
                conflicting=[], unchanged=[], classification="in_scope", evidence=[],
                commercial_impact={"level": "high", "reason": "material", "pricing_action": "review"},
                recommended_action="Review the change",
            )
        if name == "PartialMessageAnalysis":
            return response_model(
                intent={"primary": "update", "confidence": 0.9},
                deal_context={"relevant_requirements": [], "relevant_exclusions": [], "relevant_decisions": [], "relevant_assumptions": [], "relevant_messages": []},
            )
        if name == "Stage2Result":
            return response_model(
                strategy={"objective": "handle_request", "recommended_action": "reply", "reasoning": [], "key_points": []},
                response={"draft": "Here is a response.", "tone": "professional", "requires_review": False},
            )
        return response_model()


def deal():
    return Deal(
        commercial=Commercial(budget=500.0, currency="USD"),
        timeline=Timeline(deadline="10 days"),
        scope=Scope(deliverables=["Landing page"], exclusions=[], assumptions=[]),
    )


def check(item: str):
    service = ExtractionService(MaterialProvider(item))
    return service.analyze_contextual_message(deal(), "Please change this value.", "reply")


def test_deadline_change_requires_review():
    assert check("deadline").response.requires_review is True


def test_budget_change_requires_review():
    assert check("budget").response.requires_review is True


def test_price_change_requires_review():
    assert check("price").response.requires_review is True


def test_delivery_date_alias_requires_review():
    assert check("delivery date").response.requires_review is True


def test_minor_change_does_not_require_review():
    assert check("hero text").response.requires_review is False
