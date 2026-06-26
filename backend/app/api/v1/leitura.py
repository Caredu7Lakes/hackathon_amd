"""api/v1/leitura.py — rota da leitura cruzada.

GET /api/v1/leitura/{paciente_id} -> leitura cruzada com fontes e disclaimer.
Erros controlados: paciente inexistente (404), falha de contrato/LLM (502).
"""

from fastapi import APIRouter, HTTPException

from app.core.logging_config import get_logger
from app.services.explicacao_service import gerar_leitura
from app.services.leitura_service import LaudoNaoEncontradoError, listar_pacientes

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["leitura"])

@router.get("/pacientes")
def pacientes() -> dict:
    """Lista os paciente_id canonicos disponiveis (sem o prefixo de arquivo)."""
    return {"pacientes": listar_pacientes()}


@router.get("/leitura/{paciente_id}")
def leitura(paciente_id: str) -> dict:
    try:
        return gerar_leitura(paciente_id)
    except LaudoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Falha de contrato na leitura de %s: %s", paciente_id, e)
        raise HTTPException(status_code=502, detail="Falha ao gerar leitura valida") from e