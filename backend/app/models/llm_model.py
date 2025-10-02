from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum

class LLMProvider(str, Enum):
    gemini = "gemini"

class LLMRequest(BaseModel):
    prompt: str
    task_type: str  # "analysis" | "preprocessing" | "visualization" | "model_selection"
    context: Optional[str] = None
    dataset_info: Optional[Dict[str, Any]] = None

class LLMResponse(BaseModel):
    response: str
    suggestions: List[str]
    confidence: float
    task_type: str
