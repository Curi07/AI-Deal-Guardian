import logging
from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.deal import Deal, ReviewStatus
from app.schemas.analysis import ResponseIntelligence, ScopeDiff
from app.services.extraction import AnalyzeRequest, ExtractionService
from app.llm.provider import LLMProvider, OpenAIProvider, MockLLMProvider, GeminiProvider
from app.db.database import DealRepository
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
repo = DealRepository()

def get_llm_provider() -> LLMProvider:
    provider_type = settings.llm_provider.lower()
    if provider_type == "mock":
        return MockLLMProvider({})
    elif provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "gemini":
        return GeminiProvider()
    elif provider_type == "groq":
        from app.llm.provider import GroqProvider
        return GroqProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")

class MessagePayload(BaseModel):
    sender: str
    content: str
    objective: Optional[str] = None
    tone: Optional[str] = "professional"

class ReviewPayload(BaseModel):
    status: ReviewStatus
    draft: str

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_deal(request: AnalyzeRequest):
    try:
        provider = get_llm_provider()
        service = ExtractionService(provider)
        deal = service.analyze_deal(request)
        
        return {
            "deal": deal.model_dump(),
            "preflight": deal.preflight.model_dump(),
            "risks": [r.model_dump() for r in deal.risks],
            "questions": [q.model_dump() for q in deal.questions]
        }
    except ValueError as ve:
        logger.error(f"[API /analyze] Validation/Parsing error: {ve}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Analysis validation failed: {str(ve)}")
    except Exception as e:
        logger.error(f"[API /analyze] Unexpected error during deal analysis: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Provider error: {str(e)}")

@router.post("", response_model=Dict[str, str])
async def create_deal(deal: Deal):
    try:
        deal_id = repo.create_deal(deal)
        return {"deal_id": deal_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=list[Dict[str, Any]])
async def get_all_deals():
    try:
        return repo.list_deals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{deal_id}", response_model=Deal)
async def get_deal(deal_id: str):
    deal = repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.id = deal_id
    return deal

@router.post("/{deal_id}/messages", response_model=Dict[str, str])
async def append_message(deal_id: str, payload: MessagePayload):
    try:
        msg_id = repo.append_message(deal_id, payload.sender, payload.content)
        return {"message_id": msg_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{deal_id}/scope_guard", response_model=ScopeDiff)
async def analyze_scope(deal_id: str, payload: MessagePayload):
    deal = repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    try:
        provider = get_llm_provider()
        service = ExtractionService(provider)
        scope_diff = service.analyze_scope_guard(deal, payload.content)
        return scope_diff
    except ValueError as ve:
        logger.error(f"[API /scope_guard] Validation/Parsing error for deal {deal_id}: {ve}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Scope guard validation failed: {str(ve)}")
    except Exception as e:
        logger.error(f"[API /scope_guard] LLM error for deal {deal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Provider error: {str(e)}")

@router.post("/{deal_id}/analyze_message", response_model=ResponseIntelligence)
async def analyze_message(deal_id: str, payload: MessagePayload):
    deal = repo.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    if not payload.objective:
        raise HTTPException(status_code=400, detail="objective is required for analysis")
    
    try:
        provider = get_llm_provider()
        service = ExtractionService(provider)
        analysis = service.analyze_contextual_message(
            deal=deal, 
            message=payload.content, 
            objective=payload.objective, 
            tone=payload.tone
        )
        return analysis
    except ValueError as ve:
        logger.error(f"[API /analyze_message] Validation/Parsing error for deal {deal_id}: {ve}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Message analysis validation failed: {str(ve)}")
    except Exception as e:
        logger.error(f"[API /analyze_message] LLM error for deal {deal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Provider error: {str(e)}")

@router.post("/{deal_id}/reviews", response_model=Dict[str, str])
async def add_review(deal_id: str, payload: ReviewPayload):
    try:
        review_id = repo.add_review(deal_id, payload.status, payload.draft)
        return {"review_id": review_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

