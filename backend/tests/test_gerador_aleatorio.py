"""Teste de robustez em escala (ETAPA 3) — gerador de pacientes ficticios.

Gera N pacientes aleatorios combinando marcadores REAIS (pesos vindos da
literatura do corpus) em perfis sorteados, e roda o motor `integrar` em cada
um. Aleatoriza-se o PERFIL do paciente (quais marcadores, quais faixas), nunca
os hazard ratios. Asserta invariantes que devem valer para todo paciente:
risco-base intocado, estratificacao sem fusao de desfecho, ausencia de NaN,
e coerencia estrutural da saida.
"""
import math
import os
import random

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")

from app.schemas.exames import ExameOmico, MarcadorExame, PesoPublicado  # noqa: E402
from app.schemas.paciente import PacienteLaudo, RiscoDoenca  # noqa: E402
from app.services.integracao_service import integrar  # noqa: E402

# Pool de marcadores reais: (camada, nome, hr, ic, fonte, desfecho, direcao).
# Pesos ancorados na literatura ja indexada no corpus.
POOL = [
    ("clinico", "Tabagismo (ex-fumante)", 1.14, (1.10, 1.18), "tabagismo_dm2", "diabetes tipo 2 incidente", "risco"),
    ("clinico", "IMC (sobrepeso)", 2.99, (2.42, 3.72), "imc_dm2", "diabetes tipo 2 incidente", "risco"),
    ("clinico", "Alcool (leve-moderado)", 0.82, (0.73, 0.95), "alcool_dm2", "diabetes tipo 2 incidente", "protecao"),
    ("clinico", "Asma", 1.37, (1.20, 1.57), "respiratorio_dm2", "diabetes tipo 2 incidente", "risco"),
    ("microbioma", "Razao F/B", 1.20, (1.11, 1.30), "liu_2024_microbiome", "diabetes tipo 2 incidente", "risco"),
    ("microbioma", "Diversidade alfa", 0.89, (0.82, 0.96), "liu_2024_microbiome", "diabetes tipo 2 incidente", "risco"),
    ("microbioma", "Proteobacteria", 1.15, (1.05, 1.26), "gmfh_2026_cardiometabolico", "resistência à insulina", "risco"),
    ("metilacao", "MRS 87 sitios", 2.10, (1.70, 2.60), "cellrepmed_2025_mrs", "evento macrovascular em diabetes tipo 2", "risco"),
    ("metilacao", "cg05575921", 1.40, (1.20, 1.63), "cellrepmed_2025_mrs", "evento macrovascular em diabetes tipo 2", "risco"),
    ("metilacao", "EpiScore DM2", 1.85, (1.50, 2.28), "natureaging_2023_dm2_methylation", "diabetes tipo 2 incidente (10 anos)", "risco"),
]


def _paciente_aleatorio(rng: random.Random):
    """Monta laudo + exames de um paciente sorteado a partir do pool real."""
    risco_base = round(rng.uniform(10.0, 90.0), 2)
    laudo = PacienteLaudo(
        paciente_id="aleatorio",
        doencas=[RiscoDoenca(doenca="Diabetes tipo 2", risco_percentual=risco_base, faixa="sorteado")],
    )
    # Sorteia um subconjunto do pool (pode ser vazio).
    escolhidos = [m for m in POOL if rng.random() < 0.6]
    por_camada: dict[str, list] = {}
    for camada, nome, hr, ic, fonte, desfecho, direcao in escolhidos:
        peso = PesoPublicado(hazard_ratio=hr, ic_95=ic, fonte_id=fonte, desfecho=desfecho, direcao=direcao)
        m = MarcadorExame(nome=nome, valor="sorteado", tipo_marcador="aleatorio", peso=peso)
        por_camada.setdefault(camada, []).append(m)
    exames = [
        ExameOmico(paciente_id="aleatorio", camada=cam, metodo="gerado", marcadores=ms)
        for cam, ms in por_camada.items()
    ]
    return laudo, exames, risco_base


def test_robustez_em_escala_200_pacientes():
    rng = random.Random(42)  # seed fixa: teste reproduzivel
    for _ in range(200):
        laudo, exames, risco_base = _paciente_aleatorio(rng)
        r = integrar(laudo, exames)

        # Invariante 1: risco-base genetico nunca e recalculado.
        assert r["risco_base_genetico"]["diabetes tipo 2"] == risco_base

        # Invariante 2: estrutura de saida sempre presente e coerente.
        assert isinstance(r["camadas_presentes"], list)
        assert isinstance(r["modificadores_por_desfecho"], dict)

        # Invariante 3: cada modificador esta na chave do seu proprio desfecho.
        for desfecho, mods in r["modificadores_por_desfecho"].items():
            for mod in mods:
                assert mod["desfecho"] == desfecho
                # Invariante 4: nenhum HR e NaN/infinito.
                assert math.isfinite(mod["hazard_ratio"])
                # Invariante 5: IC bem-formado (inferior <= superior).
                assert mod["ic_95"][0] <= mod["ic_95"][1]
                # Invariante 6: direcao sempre valida.
                assert mod["direcao"] in ("risco", "protecao")

        # Invariante 7: toda camada presente gerou ao menos um modificador.
        desfechos_camadas = {m["camada"] for mods in r["modificadores_por_desfecho"].values() for m in mods}
        assert desfechos_camadas == set(r["camadas_presentes"])


def test_paciente_sem_marcadores_degrada_limpo():
    rng = random.Random(1)
    laudo = PacienteLaudo(paciente_id="vazio", doencas=[RiscoDoenca(doenca="Diabetes tipo 2", risco_percentual=50.0)])
    r = integrar(laudo, [])
    assert r["camadas_presentes"] == []
    assert r["modificadores_por_desfecho"] == {}
    assert r["risco_base_genetico"]["diabetes tipo 2"] == 50.0