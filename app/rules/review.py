from app.schemas.analysis import ScopeDiff, ScopeImpact


MATERIAL_CHANGE_ITEMS = {
    "deadline",
    "budget",
    "price",
}


def requires_human_review(scope_diff: ScopeDiff) -> bool:
    """Return the deterministic human-review requirement for a scope diff."""
    if scope_diff.classification in {
        ScopeImpact.POTENTIALLY_OUT_OF_SCOPE,
        ScopeImpact.CONFLICT_WITH_EXCLUSION,
    }:
        return True

    if scope_diff.classification != ScopeImpact.IN_SCOPE:
        return False

    return any(
        any(material in changed.item.lower() for material in MATERIAL_CHANGE_ITEMS)
        for changed in scope_diff.changed
    )
