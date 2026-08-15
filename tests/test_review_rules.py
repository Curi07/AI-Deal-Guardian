import pytest

from app.rules.review import requires_human_review
from app.schemas.analysis import (
    ChangedItem,
    CommercialAnalysis,
    ScopeDiff,
    ScopeImpact,
)


def scope_diff(classification, changed=None):
    return ScopeDiff(
        changed=changed or [],
        classification=classification,
        commercial_impact=CommercialAnalysis(
            level="none",
            reason="test",
            pricing_action="none",
        ),
        recommended_action="test",
    )


def changed(item):
    return ChangedItem(item=item, before="before", after="after")


def test_minor_in_scope_change_does_not_require_review():
    assert requires_human_review(
        scope_diff(ScopeImpact.IN_SCOPE, [changed("description")])
    ) is False


def test_deadline_change_requires_review():
    assert requires_human_review(
        scope_diff(ScopeImpact.IN_SCOPE, [changed("deadline")])
    ) is True


def test_budget_change_requires_review():
    assert requires_human_review(
        scope_diff(ScopeImpact.IN_SCOPE, [changed("budget")])
    ) is True


def test_price_change_requires_review():
    assert requires_human_review(
        scope_diff(ScopeImpact.IN_SCOPE, [changed("price")])
    ) is True


@pytest.mark.parametrize(
    "classification",
    [ScopeImpact.POTENTIALLY_OUT_OF_SCOPE, ScopeImpact.CONFLICT_WITH_EXCLUSION],
)
def test_non_in_scope_classifications_require_review(classification):
    assert requires_human_review(scope_diff(classification)) is True
