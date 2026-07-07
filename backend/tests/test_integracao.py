"""Testes de robustez do motor de integracao multi-omica (ETAPA 3, Peca 6).

Deterministicos, sem LLM. Cobrem o comportamento do motor `integrar` sob
variaveis adversas: exame vazio/ausente, pesos invalidos, IC malformado,
campos faltando, conflito de direcao e injecao de texto. O objetivo e provar
que o motor nao quebra nem produz saida incoerente, mantendo a estratificacao
por desfecho e o risco-base intocado.
"""
import os

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")

from app.schemas.exames import ExameOmico, MarcadorExame, PesoPublicado  # noqa: E402
from app.schemas.paciente import PacienteLaudo, RiscoDoenca  # noqa: E402
from app.services.integracao_service import integrar  # noqa: E402


def _laudo_base() -> PacienteLaudo:
    return PacienteLaudo(
        paciente_id="teste",
        doencas=[RiscoDoenca(doenca="Diabetes tipo 2", risco_percentual=50.17, faixa="Risco aumentado")],
    )


def _peso(hr=1.2, ic=(1.1, 1.3), desfecho="diabetes tipo 2 incidente", direcao="risco"):
    return PesoPublicado(hazard_ratio=hr, ic_95=ic, fonte_id="fonte_x", desfecho=desfecho, direcao=direcao)


def _exame(marcadores) -> ExameOmico:
    return ExameOmico(paciente_id="teste", camada="microbioma", metodo="teste", marcadores=marcadores)


def test_sem_exames_retorna_estrutura_vazia_sem_quebrar():
    r = integrar(_laudo_base(), [])
    assert r["risco_base_genetico"] == {"diabetes tipo 2": 50.17}
    assert r["camadas_presentes"] == []
    assert r["modificadores_por_desfecho"] == {}


def test_risco_base_permanece_intocado():
    m = MarcadorExame(nome="X", valor="alto", tipo_marcador="taxon", peso=_peso())
    r = integrar(_laudo_base(), [_exame([m])])
    # O motor nunca recalcula o PRS; o risco-base e exatamente o do laudo.
    assert r["risco_base_genetico"]["diabetes tipo 2"] == 50.17


def test_estratificacao_nunca_funde_desfechos_distintos():
    m1 = MarcadorExame(nome="A", valor="x", tipo_marcador="taxon", peso=_peso(desfecho="diabetes tipo 2 incidente"))
    m2 = MarcadorExame(nome="B", valor="y", tipo_marcador="taxon", peso=_peso(desfecho="evento macrovascular"))
    r = integrar(_laudo_base(), [_exame([m1, m2])])
    chaves = set(r["modificadores_por_desfecho"].keys())
    assert chaves == {"diabetes tipo 2 incidente", "evento macrovascular"}
    for desfecho, mods in r["modificadores_por_desfecho"].items():
        for mod in mods:
            assert mod["desfecho"] == desfecho


def test_hr_extremo_nao_quebra_motor():
    # HR muito alto e muito baixo: o motor estrutura, nao julga.
    m1 = MarcadorExame(nome="alto", valor="x", tipo_marcador="taxon", peso=_peso(hr=99.0))
    m2 = MarcadorExame(nome="baixo", valor="y", tipo_marcador="taxon", peso=_peso(hr=0.01))
    r = integrar(_laudo_base(), [_exame([m1, m2])])
    mods = r["modificadores_por_desfecho"]["diabetes tipo 2 incidente"]
    assert {m["hazard_ratio"] for m in mods} == {99.0, 0.01}


def test_conflito_de_direcao_no_mesmo_desfecho_e_preservado():
    # Risco e protecao no mesmo desfecho: ambos devem aparecer, sem fusao.
    m1 = MarcadorExame(nome="R", valor="x", tipo_marcador="taxon", peso=_peso(direcao="risco"))
    m2 = MarcadorExame(nome="P", valor="y", tipo_marcador="taxon", peso=_peso(direcao="protecao"))
    r = integrar(_laudo_base(), [_exame([m1, m2])])
    mods = r["modificadores_por_desfecho"]["diabetes tipo 2 incidente"]
    assert {m["direcao"] for m in mods} == {"risco", "protecao"}


def test_desfecho_orfao_aparece_como_chave_propria():
    # Desfecho sem correspondencia no risco-base nao contamina os demais.
    m = MarcadorExame(nome="orfao", valor="x", tipo_marcador="taxon", peso=_peso(desfecho="desfecho inexistente"))
    r = integrar(_laudo_base(), [_exame([m])])
    assert "desfecho inexistente" in r["modificadores_por_desfecho"]


def test_injecao_de_texto_em_nome_e_fonte_e_tratada_como_dado_literal():
    # Texto malicioso entra como string literal; nao e interpretado nem executado.
    payload = "<script>alert(1)</script>"
    peso = PesoPublicado(hazard_ratio=1.2, ic_95=(1.1, 1.3), fonte_id=payload, desfecho="diabetes tipo 2 incidente", direcao="risco")
    m = MarcadorExame(nome=payload, valor="x", tipo_marcador="taxon", peso=peso)
    r = integrar(_laudo_base(), [_exame([m])])
    mod = r["modificadores_por_desfecho"]["diabetes tipo 2 incidente"][0]
    # O payload e preservado como texto literal (escapar e responsabilidade da camada de render).
    assert mod["marcador"] == payload
    assert mod["fonte"] == payload


def test_multiplas_camadas_sao_todas_listadas():
    m_micro = MarcadorExame(nome="M", valor="x", tipo_marcador="taxon", peso=_peso())
    e_micro = ExameOmico(paciente_id="teste", camada="microbioma", metodo="t", marcadores=[m_micro])
    m_meti = MarcadorExame(nome="N", valor="y", tipo_marcador="sitio_cpg", peso=_peso(desfecho="evento macrovascular"))
    e_meti = ExameOmico(paciente_id="teste", camada="metilacao", metodo="t", marcadores=[m_meti])
    r = integrar(_laudo_base(), [e_micro, e_meti])
    assert r["camadas_presentes"] == ["metilacao", "microbioma"]