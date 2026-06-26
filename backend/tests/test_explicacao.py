"""Testes da Sprint 3 — explicacao_service e rota, com LLM MOCKADA.

Nenhum teste chama a API real. O mock implementa o contrato gerar_json.
"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "dev")

from app.core.disclaimer import DISCLAIMER_OBRIGATORIO  # noqa: E402
from app.services.explicacao_service import gerar_leitura  # noqa: E402

PACIENTE = "ficticio_DB_0001"


class LLMMockOk:
    def gerar_json(self, system: str, user: str) -> dict:
        return {
            "resumo": "Risco aumentado para diabetes tipo 2 com boa resposta a metformina.",
            "cruzamentos": [
                {
                    "afirmacao": "FTO conecta predisposicao a obesidade com risco de diabetes.",
                    "fontes": ["fto_dm2_scandinavian"],
                    "confianca": "alta",
                }
            ],
            "evidencia_insuficiente": [],
        }


class LLMMockSemFonte:
    def gerar_json(self, system: str, user: str) -> dict:
        return {
            "resumo": "x",
            "cruzamentos": [{"afirmacao": "afirmacao sem fonte", "fontes": [], "confianca": "alta"}],
            "evidencia_insuficiente": [],
        }


class LLMMockContratoQuebrado:
    def gerar_json(self, system: str, user: str) -> dict:
        return {"resumo": "so resumo, sem cruzamentos"}


def test_caminho_feliz_retorna_leitura_com_fontes():
    r = gerar_leitura(PACIENTE, llm=LLMMockOk())
    assert r["paciente_id"] == PACIENTE
    assert r["cruzamentos"][0]["fontes"]
    assert r["disclaimer"] == DISCLAIMER_OBRIGATORIO


def test_disclaimer_sempre_presente():
    r = gerar_leitura(PACIENTE, llm=LLMMockOk())
    assert "disclaimer" in r and r["disclaimer"]


def test_grounding_rejeita_cruzamento_sem_fonte():
    with pytest.raises(ValueError, match="grounding"):
        gerar_leitura(PACIENTE, llm=LLMMockSemFonte())


def test_contrato_rejeita_saida_incompleta():
    with pytest.raises(ValueError, match="campo obrigatorio"):
        gerar_leitura(PACIENTE, llm=LLMMockContratoQuebrado())


def test_rota_leitura_fim_a_fim(monkeypatch):
    import app.api.v1.leitura as rota

    def fake_gerar(paciente_id):
        return gerar_leitura(paciente_id, llm=LLMMockOk())

    monkeypatch.setattr(rota, "gerar_leitura", fake_gerar)

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.get(f"/api/v1/leitura/{PACIENTE}")
    assert resp.status_code == 200
    assert resp.json()["paciente_id"] == PACIENTE
    assert "disclaimer" in resp.json()