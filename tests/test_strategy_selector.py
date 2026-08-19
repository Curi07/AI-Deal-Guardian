import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.deal import Deal, Scope, Commercial
from app.schemas.analysis import ScopeImpact, StrategyMode
from app.llm.provider import MockLLMProvider
from app.services.extraction import ExtractionService
from app.db.database import DealRepository

def build_mock_response_for_strategy(strategy_mode: str, recommended_action: str, draft: str):
    # Mock for Stage 1.0 (Scope Guard)
    scope_mock = {
        "added": ["Admin Dashboard"],
        "removed": [],
        "changed": [],
        "conflicting": [],
        "unchanged": [],
        "classification": ScopeImpact.POTENTIALLY_OUT_OF_SCOPE,
        "evidence": ["Client requested admin dashboard not in original scope"],
        "commercial_impact": {
            "level": "high",
            "reason": "Significant new module requiring backend and UI work",
            "pricing_action": "quote_separately"
        },
        "recommended_action": "Propose as Phase 2 or separate quote"
    }
    
    # Mock for Stage 1.5 (Intent and Context)
    partial_mock = {
        "intent": {"primary": "add_feature", "confidence": 0.95},
        "deal_context": {
            "relevant_requirements": ["Deliverables: Landing page, Contact form"],
            "relevant_exclusions": [],
            "relevant_decisions": [],
            "relevant_assumptions": [],
            "relevant_messages": []
        }
    }
    
    # Mock for Stage 2 (Strategy and Response)
    stage2_mock = {
        "strategy": {
            "objective": "negotiate_scope",
            "recommended_action": recommended_action,
            "strategy_mode": strategy_mode,
            "reasoning": [f"Follow {strategy_mode} approach strictly"],
            "key_points": ["Budget adjustment", "Timeline impact"]
        },
        "response": {
            "draft": draft,
            "tone": "professional",
            "requires_review": True
        }
    }
    
    return [scope_mock, partial_mock, stage2_mock]


def test_strategy_selector_upsell():
    mock_data = build_mock_response_for_strategy(
        strategy_mode="upsell",
        recommended_action="Propose incorporating Admin Dashboard as Phase 2 / Add-on module.",
        draft="Podemos sumar el Admin Dashboard como una Fase 2 con presupuesto y plazo adicionales."
    )
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"])
    )
    
    result = service.analyze_contextual_message(
        deal=deal,
        message="Could you also add an admin dashboard?",
        objective="negotiate_scope",
        strategy_mode=StrategyMode.UPSELL
    )
    
    assert result.strategy.strategy_mode == StrategyMode.UPSELL
    assert "Fase 2" in result.strategy.recommended_action or "Phase 2" in result.strategy.recommended_action
    assert "Fase 2" in result.response.draft or "presupuesto" in result.response.draft
    # Scope Guard must remain strictly intact
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert result.response.requires_review is True


def test_strategy_selector_tradeoff():
    mock_data = build_mock_response_for_strategy(
        strategy_mode="tradeoff",
        recommended_action="Propose incorporating Admin Dashboard by removing or postponing another scope item.",
        draft="Podemos incluir el Admin Dashboard si retiramos o simplificamos el formulario de contacto para mantener el presupuesto."
    )
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"])
    )
    
    result = service.analyze_contextual_message(
        deal=deal,
        message="Could you also add an admin dashboard?",
        objective="negotiate_scope",
        strategy_mode=StrategyMode.TRADEOFF
    )
    
    assert result.strategy.strategy_mode == StrategyMode.TRADEOFF
    assert "tradeoff" in result.strategy.reasoning[0] or "trade-off" in result.strategy.recommended_action.lower()
    # Scope Guard must remain strictly intact
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert result.response.requires_review is True


def test_strategy_selector_firm_boundary():
    mock_data = build_mock_response_for_strategy(
        strategy_mode="firm_boundary",
        recommended_action="Decline new module to preserve agreed delivery date and budget.",
        draft="Para cumplir con la fecha de entrega y presupuesto acordados, debemos mantener el alcance original."
    )
    service = ExtractionService(MockLLMProvider(mock_response=mock_data))
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"])
    )
    
    result = service.analyze_contextual_message(
        deal=deal,
        message="Could you also add an admin dashboard?",
        objective="defend_price",
        strategy_mode=StrategyMode.FIRM_BOUNDARY
    )
    
    assert result.strategy.strategy_mode == StrategyMode.FIRM_BOUNDARY
    # Scope Guard must remain strictly intact
    assert result.message_analysis.scope_guard.classification == ScopeImpact.POTENTIALLY_OUT_OF_SCOPE
    assert result.response.requires_review is True


@patch("app.api.deals.get_llm_provider")
def test_api_analyze_message_with_strategy_modes(mock_get_provider):
    repo = DealRepository()
    deal = Deal(
        commercial=Commercial(budget=1000, currency="USD"),
        scope=Scope(deliverables=["Landing page", "Contact form"])
    )
    deal_id = repo.create_deal(deal)
    
    client = TestClient(app)
    
    # Test with each strategy mode
    for mode in ["upsell", "tradeoff", "firm_boundary"]:
        mock_data = build_mock_response_for_strategy(
            strategy_mode=mode,
            recommended_action=f"Action for {mode}",
            draft=f"Draft for {mode}"
        )
        mock_get_provider.return_value = MockLLMProvider(mock_response=mock_data)
        
        response = client.post(
            f"/api/deals/{deal_id}/analyze_message",
            json={
                "sender": "client",
                "content": "Can you also build an admin panel?",
                "objective": "negotiate_scope",
                "strategy_mode": mode
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "strategy" in data
        assert "response" in data
        assert data["strategy"]["strategy_mode"] == mode
        assert "message_analysis" in data
        assert data["message_analysis"]["scope_guard"]["classification"] is not None
