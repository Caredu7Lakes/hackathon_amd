"""Aplicacao FastAPI.

Registra a rota de leitura cruzada (Sprint 3). LLM via API Anthropic direta (camada core/llm.py, selecionada por LLM_PROVIDER).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.leitura import router as leitura_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Subindo hackathon_amd em ambiente=%s", settings.ENVIRONMENT.value)
    yield
    logger.info("Encerrando hackathon_amd")


app = FastAPI(title="GenRisk", version="0.3.0", lifespan=lifespan)
app.include_router(leitura_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}