"""Testes de fundação da Sprint 0.

Confirmam que o esqueleto sobe e que o schema do paciente valida. A massa
real de testes (leitura_service determinístico, rota) vem nas Sprints 1 e 3.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Garante config válida antes de importar o app (fail-fast não deve barrar testes).
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")

from app.main import app  # noqa: E402
from app.schemas.paciente import Marcador, PacienteLaudo, RiscoDoenca  # noqa: E402


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_schema_paciente_valida():
    laudo = PacienteLaudo(
        paciente_id="ficticio_0001",
        doencas=[
            RiscoDoenca(
                doenca="Diabetes tipo 2",
                risco_percentual=50.17,
                faixa="Risco aumentado",
                marcadores=[
                    Marcador(rsid="rs7903146", gene="TCF7L2", efeito=0.00087869)
                ],
            )
        ],
    )
    assert laudo.doencas[0].risco_percentual == 50.17
    assert laudo.doencas[0].marcadores[0].rsid == "rs7903146"
