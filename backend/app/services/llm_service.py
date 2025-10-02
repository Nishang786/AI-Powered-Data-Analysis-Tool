import logging
from types import SimpleNamespace
from typing import Any, List
from importlib import import_module

from app.core.config import settings
from app.models.llm_model import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.client = None
        self.config = None
        self._initialized = False
        self._genai = None
        self._types = None

    async def initialize(self, config=None):
        # lazy import so the app can still start if google-genai isn't installed
        try:
            self._genai = import_module("google.genai")
            # also import top-level package in case it's referenced
            import_module("google")
            self._types = import_module("google.genai.types")
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "google-genai package is required for Gemini LLM functionality. "
                "Install it with: pip install google-genai"
            ) from e

        self.client = self._genai.Client(api_key=settings.GEMINI_API_KEY)
        # populate a minimal config object so other services can read model and token settings
        # (visualization_service and others may expect gemini_service.config.*)
        self.config = SimpleNamespace(
            model_name=getattr(settings, "DEFAULT_GEMINI_MODEL", "gemini-2.5-flash"),
            max_tokens=getattr(settings, "DEFAULT_MAX_TOKENS", 1500),
            temperature=getattr(settings, "DEFAULT_TEMPERATURE", 0.6),
        )
        # quick ping
        _ = self.client.models.generate_content(
            model=settings.DEFAULT_GEMINI_MODEL,
            contents="ping",
            config=self._types.GenerateContentConfig(max_output_tokens=8, temperature=0.1),
        )
        self._initialized = True

    def _system_prompt(self, task: str) -> str:
        prompts = {
            "analysis": "You are an expert in EDA. Provide concise, actionable insights and statistics to compute.",
            "preprocessing": "You are a data preprocessing expert. Recommend concrete steps for missing values, outliers, scaling, encoding.",
            "visualization": "You are a visualization expert. Suggest the most informative plots based on column types and relationships.",
            "model_selection": "You are an ML expert. Recommend suitable models, metrics, and next steps given target variable and feature types.",
        }
        return prompts.get(task, prompts["analysis"])

    def _format_input(self, req: LLMRequest) -> str:
        parts = [f"Task: {req.prompt}"]
        if req.context:
            parts.append(f"Context: {req.context}")
        if req.dataset_info:
            parts.append(f"Dataset info summary: {str(req.dataset_info)[:2000]}")
        parts.append("Return bullet-pointed, specific, step-by-step suggestions.")
        return "\n\n".join(parts)

    def _parse(self, raw: Any, task: str) -> LLMResponse:
        text = getattr(raw, "text", str(raw))
        suggestions: List[str] = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("-", "*", "•")) and len(s) > 2:
                suggestions.append(s.lstrip("-*• ").strip())
        if not suggestions and text:
            suggestions = [text[:200]]
        return LLMResponse(response=text, suggestions=suggestions[:6], confidence=0.85, task_type=task)

    async def suggest(self, req: LLMRequest) -> LLMResponse:
        if not self._initialized:
            raise RuntimeError("Gemini not initialized")
        sys_prompt = self._system_prompt(req.task_type)
        user_text = self._format_input(req)
        resp = self.client.models.generate_content(
            model=settings.DEFAULT_GEMINI_MODEL,
            contents=user_text,
            config=self._types.GenerateContentConfig(
                system_instruction=sys_prompt,
                max_output_tokens=settings.DEFAULT_MAX_TOKENS,
                temperature=settings.DEFAULT_TEMPERATURE,
            ),
        )
        return self._parse(resp, req.task_type)

gemini_service = GeminiService()
