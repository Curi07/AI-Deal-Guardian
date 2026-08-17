from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# --- Enums ---
class SourceType(str, Enum):
    CLIENT = "client"
    FREELANCER = "freelancer"
    AI = "ai"
    AGREEMENT = "agreement"

class CertaintyType(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"
    CONFIRMED = "confirmed"

class PricingModel(str, Enum):
    FIXED = "fixed"
    HOURLY = "hourly"
    MILESTONE = "milestone"
    MONTHLY = "monthly"
    UNKNOWN = "unknown"

class DeadlineType(str, Enum):
    EXPLICIT = "explicit"
    ESTIMATED = "estimated"
    FLEXIBLE = "flexible"
    UNKNOWN = "unknown"

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PreflightStatus(str, Enum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    DO_NOT_QUOTE = "do_not_quote"

class RiskCategory(str, Enum):
    SCOPE = "scope"
    TIMELINE = "timeline"
    BUDGET = "budget"
    DEPENDENCY = "dependency"
    TECHNICAL = "technical"
    CLIENT_CLARITY = "client_clarity"
    REQUIREMENTS = "requirements"
    EXTERNAL = "external"
    COMMUNICATION = "communication"

class QuestionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DependencyStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    UNKNOWN = "unknown"

class ReviewStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"

class ProjectStatus(str, Enum):
    WAITING_MESSAGE = "waiting_message"
    IN_PROGRESS = "in_progress"
    REJECTED = "rejected"
    COMPLETED = "completed"

# --- Models ---
class Client(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    contact: Optional[str] = None

class Project(BaseModel):
    title: str = ""
    type: str = ""
    description: str = ""

class Commercial(BaseModel):
    budget: Optional[float] = None
    currency: Optional[str] = None
    pricing_model: Optional[PricingModel] = None

class Timeline(BaseModel):
    deadline: Optional[str] = None
    deadline_type: Optional[DeadlineType] = None
    milestones: List[str] = Field(default_factory=list)

class Scope(BaseModel):
    deliverables: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    revisions: Optional[int] = None
    assumptions: List[str] = Field(default_factory=list)

class Requirement(BaseModel):
    id: str
    description: str
    source: SourceType
    certainty: CertaintyType

class Dependency(BaseModel):
    description: str
    status: DependencyStatus = DependencyStatus.UNKNOWN
    owner: Optional[str] = "unknown"

class Unknown(BaseModel):
    title: str = ""
    description: str
    severity: Severity = Severity.MEDIUM
    blocks_quote: bool = False

class Risk(BaseModel):
    description: str
    category: RiskCategory = RiskCategory.SCOPE
    severity: Severity = Severity.MEDIUM
    evidence: List[str] = Field(default_factory=list)

class Question(BaseModel):
    id: str = ""
    question: str
    reason: Optional[str] = ""
    priority: QuestionPriority = QuestionPriority.MEDIUM
    blocks_quote: bool = False

class Decision(BaseModel):
    description: str
    source: SourceType
    timestamp: str
    status: str

class Message(BaseModel):
    id: str
    timestamp: str
    sender: str
    content: str
    analysis: Optional[Any] = None

class Preflight(BaseModel):
    status: PreflightStatus = PreflightStatus.NEEDS_CLARIFICATION
    risk_score: int = 0
    confidence: float = 0.0
    blocking_unknowns: int = 0
    generated_at: Optional[str] = None

class Review(BaseModel):
    id: str
    status: ReviewStatus
    draft: str
    timestamp: str

class Deal(BaseModel):
    id: Optional[str] = None
    status: ProjectStatus = ProjectStatus.WAITING_MESSAGE
    client: Client = Field(default_factory=Client)
    project: Project = Field(default_factory=Project)
    commercial: Commercial = Field(default_factory=Commercial)
    timeline: Timeline = Field(default_factory=Timeline)
    scope: Scope = Field(default_factory=Scope)
    requirements: List[Requirement] = Field(default_factory=list)
    dependencies: List[Dependency] = Field(default_factory=list)
    unknowns: List[Unknown] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    questions: List[Question] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    reviews: List[Review] = Field(default_factory=list)
    preflight: Preflight = Field(default_factory=Preflight)
