import pytest
from app.schemas.deal import Deal, PreflightStatus, Unknown, Risk, RiskCategory, Severity
from app.rules.engine import RuleEngine

def test_rule_engine_clean_deal():
    engine = RuleEngine()
    deal = Deal()
    processed_deal = engine.evaluate(deal)
    # A completely empty deal has no unknowns/risks but we expect READY
    # Since confidence drops only on unknowns/dependencies, it should be 1.0
    assert processed_deal.preflight.status == PreflightStatus.READY
    assert processed_deal.preflight.risk_score == 0
    assert processed_deal.preflight.confidence == 1.0
    assert processed_deal.preflight.blocking_unknowns == 0

def test_rule_engine_with_blocking_unknown():
    engine = RuleEngine()
    deal = Deal()
    deal.unknowns.append(Unknown(
        description="Missing budget constraints",
        severity=Severity.HIGH,
        blocks_quote=True
    ))
    processed_deal = engine.evaluate(deal)
    # 1 blocking unknown means NEEDS_CLARIFICATION
    assert processed_deal.preflight.status == PreflightStatus.NEEDS_CLARIFICATION
    assert processed_deal.preflight.blocking_unknowns == 1
    assert processed_deal.preflight.risk_score >= 15

def test_rule_engine_with_multiple_blocking_unknowns():
    engine = RuleEngine()
    deal = Deal()
    deal.unknowns.append(Unknown(
        description="Unknown timeline",
        severity=Severity.HIGH,
        blocks_quote=True
    ))
    deal.unknowns.append(Unknown(
        description="Unknown technical stack",
        severity=Severity.HIGH,
        blocks_quote=True
    ))
    processed_deal = engine.evaluate(deal)
    # >1 blocking unknown means DO_NOT_QUOTE
    assert processed_deal.preflight.status == PreflightStatus.DO_NOT_QUOTE
    assert processed_deal.preflight.blocking_unknowns == 2
