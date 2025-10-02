from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import os

from app.core.config import settings
from app.controllers import upload_controller, llm_controller
from app.controllers import analysis_controller  
from app.services.llm_service import gemini_service
from app.controllers import preprocessing_controller  
from app.controllers import visualization_controller



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
    if settings.GEMINI_API_KEY:
        try:
            await gemini_service.initialize()
            if gemini_service._initialized:
                logger.info("Gemini initialized")
            else:
                logger.warning("Gemini failed to initialize; LLM features disabled")
        except Exception as e:
            # Initialization should never crash app startup; log and continue with LLM disabled
            logger.exception("Exception while initializing Gemini: %s", e)
    else:
        logger.warning("GEMINI_API_KEY missing; LLM disabled")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_controller.router, prefix=settings.API_PREFIX)
app.include_router(llm_controller.router, prefix=settings.API_PREFIX)
app.include_router(analysis_controller.router, prefix=settings.API_PREFIX)
app.include_router(preprocessing_controller.router, prefix=settings.API_PREFIX)
app.include_router(visualization_controller.router, prefix=settings.API_PREFIX)


uploads_dir = Path(settings.UPLOAD_DIR)
if uploads_dir.exists():
    app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")

@app.get("/")
async def root():
    return {"message": "DS Platform (Gemini)", "version": settings.VERSION}

@app.get("/health")
async def health():
    ok = Path(settings.UPLOAD_DIR).exists() and os.access(settings.UPLOAD_DIR, os.W_OK)
    return {"status": "ok" if ok else "degraded", "llm": gemini_service._initialized}

@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
