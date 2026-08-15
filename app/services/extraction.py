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
        
        class PartialMessageAnalysis(BaseModel):
            intent: IntentAnalysis
            deal_context: DealContextSummary
            
        stage1_system_prompt = """
You are AI Deal Guardian. Based on a client message, extract the client's intent and isolate the relevant sections of the Deal Memory that pertain to this message.
"""
        stage1_user_prompt = f"""
=== EXISTING DEAL MEMORY ===
{deal_context}

=== NEW CLIENT MESSAGE ===
{message}

Extract the intent and relevant context.
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
