from fastapi import APIRouter, HTTPException
from app.models.llm_model import LLMRequest, LLMResponse
from app.services.llm_service import gemini_service

router = APIRouter(prefix="/llm", tags=["llm"])

@router.post("/suggestions", response_model=LLMResponse)
async def suggestions(req: LLMRequest):
    if not gemini_service._initialized:
        raise HTTPException(status_code=503, detail="LLM not initialized")
    return await gemini_service.suggest(req)

@router.get("/status")
async def status():
    return {
        "initialized": gemini_service._initialized,
        "model": "gemini-2.5-flash"
    }
