from pydantic import BaseModel
from typing import Optional
from app.llm.provider import LLMProvider
from app.schemas.deal import Deal
from app.rules.engine import RuleEngine
from app.rules.review import requires_human_review

class AnalyzeRequest(BaseModel):
    message: str
    budget: Optional[float] = None
    currency: Optional[str] = None
    deadline: Optional[str] = None

class ExtractionService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.rule_engine = RuleEngine()

    def analyze_deal(self, request: AnalyzeRequest) -> Deal:
        system_prompt = """
You are AI Deal Guardian, an expert technical architect and project manager.
Your task is to analyze a freelance project brief and extract structured data to populate a Deal object.

CRITICAL INSTRUCTIONS:
1. Extract only what is supported by the source message.
2. Distinguish explicit facts from inference (use the `source` and `certainty` fields).
3. Never invent missing information.
4. Flag ambiguity as Unknowns.
5. Identify technical and commercial dependencies.
6. Explain risk using evidence.
7. Generate actionable, specific questions to resolve unknowns.
8. Preserve uncertainty. Never convert an inference into a confirmed requirement.
9. Prefer "unknown" over hallucination.
10. Keep requirement descriptions, unknowns, risks, and questions concise, clear, and direct (1-2 sentences maximum per item).
11. Leave decisions, messages, and reviews as empty lists in initial deal extraction.
12. Always generate a clear, concise project title in project.title summarizing the core deliverable (e.g., 'Web App with Auth, Stripe & Admin').

If a requirement is explicitly stated by the client, source="client", certainty="explicit".
If you believe a requirement is necessary but not stated, source="ai", certainty="inferred".
"""
        
        user_prompt = f"""
Client Message:
{request.message}

Additional Context Provided by User:
- Budget: {request.budget or 'Not provided'}
- Currency: {request.currency or 'Not provided'}
- Deadline: {request.deadline or 'Not provided'}

Please extract the deal details according to the schema.
"""
        
        extracted_deal = self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Deal
        )
        
        if request.budget:
            extracted_deal.commercial.budget = request.budget
        if request.currency:
            extracted_deal.commercial.currency = request.currency
        if request.deadline and not extracted_deal.timeline.deadline:
            extracted_deal.timeline.deadline = request.deadline
            
        final_deal = self.rule_engine.evaluate(extracted_deal)
        
        return final_deal

    def analyze_scope_guard(self, deal: Deal, message: str):
        from app.schemas.analysis import ScopeDiff
        import json
        
        deal_context = deal.model_dump_json(indent=2)
        
        system_prompt = """
You are AI Deal Guardian - Scope Guard Layer.
Your task is to strictly compare the ORIGINAL DEAL with a NEW CLIENT REQUEST and output a ScopeDiff.

CRITICAL INSTRUCTIONS:
1. "added": Request for work not in the original scope. Classify as 'potentially_out_of_scope' unless conflicting.
2. "changed": Modifying an existing requirement (e.g., quantity, deadline, revisions). Provide before/after.
3. "conflicting": Directly contradicts an explicit exclusion or confirmed decision. Classify as 'conflict_with_exclusion'.
4. "unchanged": Re-affirming an existing inclusion without modifying it. Classify as 'in_scope'.
5. "unmentioned != out_of_scope": If a request was never mentioned, it is 'potentially_out_of_scope' or 'unclear'.
6. Do NOT automatically classify something as a contractual violation unless there's evidence.
7. Assess commercial impact (none, low, medium, high).
8. Recommend an action for the freelancer based on the diff.
"""
        user_prompt = f"""
=== ORIGINAL DEAL MEMORY ===
{deal_context}

=== NEW CLIENT MESSAGE ===
{message}

Analyze the scope diff according to the schema.
"""
        scope_diff = self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ScopeDiff
        )
        return scope_diff

    def analyze_contextual_message(self, deal: Deal, message: str, objective: str, tone: str = "professional"):
        from app.schemas.analysis import MessageAnalysis, Strategy, ResponseDraft, ResponseIntelligence, IntentAnalysis, DealContextSummary
        from pydantic import BaseModel
        import json
        
        deal_context = deal.model_dump_json(indent=2)
        
        scope_guard_result = self.analyze_scope_guard(deal, message)
        
        # Build a flat text representation of the Deal for Stage 1.
        # Passing deal.model_dump_json() exposes rich objects (Message with id/timestamp/sender,
        # Requirement with id/description/source/certainty). Groq reproduces those objects in
        # List[str] fields, causing HTTP 400 tool call validation failures.
        # A flat text summary removes the structural temptation entirely.
        lines = []
        lines.append("PROJECT:")
        lines.append(f"  Title: {deal.project.title or 'N/A'}")
        lines.append(f"  Type: {deal.project.type or 'N/A'}")
        lines.append(f"  Description: {deal.project.description or 'N/A'}")
        lines.append("")
        lines.append("COMMERCIAL:")
        lines.append(f"  Budget: {deal.commercial.budget} {deal.commercial.currency or ''}")
        lines.append(f"  Deadline: {deal.timeline.deadline or 'N/A'}")
        lines.append("")
        lines.append("AGREED SCOPE (Deliverables):")
        for d in deal.scope.deliverables:
            lines.append(f"  - {d}")
        lines.append("")
        lines.append("EXPLICIT EXCLUSIONS:")
        for e in deal.scope.exclusions:
            lines.append(f"  - {e}")
        lines.append("")
        lines.append("REQUIREMENTS:")
        for r in deal.requirements:
            certainty = r.certainty.value if hasattr(r.certainty, 'value') else r.certainty
            source = r.source.value if hasattr(r.source, 'value') else r.source
            lines.append(f"  - [{source}/{certainty}] {r.description}")
        lines.append("")
        lines.append("CONVERSATION HISTORY:")
        for m in deal.messages:
            lines.append(f"  - {m.sender}: {m.content}")
        lines.append("")
        lines.append("DECISIONS:")
        for dec in deal.decisions:
            lines.append(f"  - {dec.description}")
        lines.append("")
        lines.append("ASSUMPTIONS:")
        for a in deal.scope.assumptions:
            lines.append(f"  - {a}")
        
        flat_deal_context = "\n".join(lines)
        
        class PartialMessageAnalysis(BaseModel):
            intent: IntentAnalysis
            deal_context: DealContextSummary
            
        stage1_system_prompt = """\
You are AI Deal Guardian. Based on a client message, extract the client's intent and isolate \
the relevant sections of the Deal Memory that pertain to this message.

CRITICAL OUTPUT RULES:
- relevant_requirements: list of PLAIN TEXT STRINGS describing each relevant requirement. \
Do NOT return objects, IDs, dicts or nested structures. Each item must be a simple string.
- relevant_exclusions: list of PLAIN TEXT STRINGS describing each relevant exclusion. \
Do NOT return objects, IDs, dicts or nested structures.
- relevant_decisions: list of PLAIN TEXT STRINGS. Do NOT return objects.
- relevant_assumptions: list of PLAIN TEXT STRINGS. Do NOT return objects.
- relevant_messages: list of PLAIN TEXT STRINGS quoting each relevant conversation line \
(e.g. "Client: Can you add a dashboard?"). Do NOT return objects, IDs, timestamps, sender \
metadata, or nested structures. Each item must be a simple string.

Every field in deal_context MUST contain ONLY plain text strings. Never include dicts or objects.
"""
        stage1_user_prompt = f"""
=== EXISTING DEAL MEMORY ===
{flat_deal_context}

=== NEW CLIENT MESSAGE ===
{message}

Extract the intent and relevant context. Remember: all relevant_* fields must be plain text strings only.
"""
        partial_analysis = self.provider.generate_structured(
            system_prompt=stage1_system_prompt,
            user_prompt=stage1_user_prompt,
            response_model=PartialMessageAnalysis
        )
        
        message_analysis = MessageAnalysis(
            intent=partial_analysis.intent,
            scope_guard=scope_guard_result,
            deal_context=partial_analysis.deal_context
        )
        
        class Stage2Result(BaseModel):
            strategy: Strategy
            response: ResponseDraft
            
        stage2_system_prompt = """
You are AI Deal Guardian. Based on a structured analysis of a client message and the user's objective, generate a recommended strategy and a draft response.

CRITICAL INSTRUCTIONS:
1. The user's objective is AUTHORITATIVE. Generate a strategy that fulfills the objective (e.g., if objective is 'defend_price', do not propose a discount).
2. The generated response must be SURGICAL: one clear objective, no unnecessary info, grounded in the Deal.
3. NO HALLUCINATION: Never invent prices, deadlines, deliverables, or agreements. If missing, recommend asking for clarification.
4. Do NOT silently resolve conflicts with confirmed decisions. Recommend clarification/renegotiation.
"""
        stage2_user_prompt = f"""
=== STRUCTURED ANALYSIS ===
{message_analysis.model_dump_json(indent=2)}

=== USER OBJECTIVE ===
{objective}

=== REQUESTED TONE ===
{tone}

Generate the strategy and draft response based on the structured analysis, matching the objective and tone.
"""
        stage2_result = self.provider.generate_structured(
            system_prompt=stage2_system_prompt,
            user_prompt=stage2_user_prompt,
            response_model=Stage2Result
        )
        
        intelligence = ResponseIntelligence(
            message_analysis=message_analysis,
            strategy=stage2_result.strategy,
            response=stage2_result.response
        )
        
        intelligence.response.requires_review = requires_human_review(
            intelligence.message_analysis.scope_guard
        )
            
        return intelligence
