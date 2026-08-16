from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator

class ScopeImpact(str, Enum):
    IN_SCOPE = "in_scope"
    POTENTIALLY_OUT_OF_SCOPE = "potentially_out_of_scope"
    CONFLICT_WITH_EXCLUSION = "conflict_with_exclusion"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"

class IntentAnalysis(BaseModel):
    primary: str
    secondary: Optional[str] = None
    confidence: float

class CommercialAnalysis(BaseModel):
    level: str
    reason: str
    pricing_action: str

class ChangedItem(BaseModel):
    item: str
    before: str
    after: str
    evidence: List[str] = Field(default_factory=list)

class ScopeDiff(BaseModel):
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)
    changed: List[ChangedItem] = Field(default_factory=list)
    conflicting: List[str] = Field(default_factory=list)
    unchanged: List[str] = Field(default_factory=list)
    classification: ScopeImpact
    evidence: List[str] = Field(default_factory=list)
    commercial_impact: CommercialAnalysis
    recommended_action: str

class DealContextSummary(BaseModel):
    relevant_requirements: List[str] = Field(default_factory=list)
    relevant_exclusions: List[str] = Field(default_factory=list)
    relevant_decisions: List[str] = Field(default_factory=list)
    relevant_assumptions: List[str] = Field(default_factory=list)
    relevant_messages: List[str] = Field(default_factory=list)

    @field_validator("relevant_messages", mode="before")
    @classmethod
    def coerce_messages_to_str(cls, v: Any) -> List[str]:
        """Coerce list items to str. Groq may return Message objects instead of strings."""
        if not isinstance(v, list):
            return v
        result = []
        for item in v:
            if isinstance(item, dict):
                # Extract the most meaningful text field from a Message-like object
                result.append(item.get("content") or item.get("description") or str(item))
            else:
                result.append(str(item))
        return result

    @field_validator("relevant_requirements", mode="before")
    @classmethod
    def coerce_requirements_to_str(cls, v: Any) -> List[str]:
        """Coerce list items to str. Groq may return Requirement objects instead of strings."""
        if not isinstance(v, list):
            return v
        result = []
        for item in v:
            if isinstance(item, dict):
                # Extract the most meaningful text field from a Requirement-like object
                result.append(item.get("description") or item.get("content") or str(item))
            else:
                result.append(str(item))
        return result

class MessageAnalysis(BaseModel):
    intent: IntentAnalysis
    scope_guard: ScopeDiff
    deal_context: DealContextSummary

class Strategy(BaseModel):
    objective: str
    recommended_action: str
    reasoning: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)

class ResponseDraft(BaseModel):
    draft: str
    tone: str
    requires_review: bool = True

class ResponseIntelligence(BaseModel):
    message_analysis: MessageAnalysis
    strategy: Strategy
    response: ResponseDraft
