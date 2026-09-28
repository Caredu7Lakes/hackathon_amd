"""Aplicacao FastAPI.

Registra a rota de leitura cruzada (Sprint 3). LLM via API Anthropic direta (camada core/llm.py, selecionada por LLM_PROVIDER).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# CORS: libera o frontend (origens vindas de CORS_ORIGINS, separadas por virgula).
origens = [o.strip() for o in get_settings().CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(leitura_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}