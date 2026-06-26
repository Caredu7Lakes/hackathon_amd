"""Testes do leitura_service (Sprint 1) — deterministicos, sem LLM.

Cobrem: carga e validacao do laudo real, contagem do recorte cardiometabolico,
erro controlado para paciente inexistente, e listagem de pacientes.
"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")

from app.schemas.paciente import PacienteLaudo  # noqa: E402
from app.services.leitura_service import (  # noqa: E402
    LaudoNaoEncontradoError,
    carregar_laudo,
    listar_pacientes,
)

PACIENTE = "ficticio_DB_0001"


def test_carregar_laudo_valida_e_retorna_paciente():
    laudo = carregar_laudo(PACIENTE)
    assert isinstance(laudo, PacienteLaudo)
    assert laudo.paciente_id == PACIENTE


def test_recorte_cardiometabolico_completo():
    laudo = carregar_laudo(PACIENTE)
    assert len(laudo.doencas) == 2
    assert len(laudo.farma) == 5
    assert len(laudo.fit) == 4


def test_diabetes_tem_risco_e_marcadores():
    laudo = carregar_laudo(PACIENTE)
    dm2 = next(d for d in laudo.doencas if "Diabetes" in d.doenca)
    assert dm2.risco_percentual == 50.17
    assert dm2.faixa == "Risco aumentado"
    assert len(dm2.marcadores) == 10
    assert any(m.rsid == "rs7903146" for m in dm2.marcadores)


def test_conectores_fit_fto_e_chrm2_presentes():
    laudo = carregar_laudo(PACIENTE)
    genes_fit = {m.gene for t in laudo.fit for m in t.marcadores}
    assert "FTO" in genes_fit
    assert "CHRM2" in genes_fit


def test_paciente_inexistente_levanta_erro():
    with pytest.raises(LaudoNaoEncontradoError):
        carregar_laudo("nao_existe_999")


def test_listar_pacientes_inclui_o_ficticio():
    ids = listar_pacientes()
    assert PACIENTE in ids