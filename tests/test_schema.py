import pytest
from app.schemas.deal import Deal, Client, SourceType, CertaintyType, Requirement, Unknown, Severity

def test_deal_default_initialization():
    deal = Deal()
    assert deal.client.name is None
    assert deal.preflight.risk_score == 0
    assert deal.preflight.status == "needs_clarification"

def test_requirement_validation():
    req = Requirement(
        id="REQ-001",
        description="Payment integration",
        source="client",
        certainty="explicit"
    )
    assert req.source == SourceType.CLIENT
    assert req.certainty == CertaintyType.EXPLICIT

def test_unknown_validation():
    unk = Unknown(
        description="Payment provider not specified",
        severity="high",
        blocks_quote=True
    )
    assert unk.severity == Severity.HIGH
    assert unk.blocks_quote is True
