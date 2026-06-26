"""Teste de aceite da Sprint 2 — RAG, sem LLM.

Constroi o indice e valida que a busca semantica recupera o chunk correto
para consultas por variante/gene.
"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")


@pytest.fixture(scope="module")
def indice_construido():
    from app.rag.ingest import construir_indice

    n = construir_indice()
    assert n > 0
    return n


def test_indice_tem_corpus_e_laudos(indice_construido):
    assert indice_construido >= 23


def test_busca_fto_retorna_chunk_de_fto(indice_construido):
    from app.rag.store import buscar

    res = buscar("FTO rs9939609 obesidade diabetes", k=3)
    assert res, "busca nao retornou resultados"
    genes = {r.get("gene") for r in res} | {r.get("id") for r in res}
    assert any("FTO" in str(g) for g in genes if g)


def test_busca_sinvastatina_retorna_cpic(indice_construido):
    from app.rag.store import buscar

    res = buscar("sinvastatina miopatia SLCO1B1", k=3)
    assert res
    ids = " ".join(str(r.get("id", "")) + str(r.get("gene", "")) for r in res)
    assert "SLCO1B1" in ids or "slco1b1" in ids.lower()


def test_busca_recuperacao_cardiaca(indice_construido):
    from app.rag.store import buscar

    res = buscar("recuperacao frequencia cardiaca apos exercicio risco", k=3)
    assert res
    blob = " ".join(str(r.get("id", "")) + str(r.get("texto", "")) for r in res).lower()
    assert "cardiac" in blob or "frequencia" in blob or "chrm2" in blob


def test_score_decrescente(indice_construido):
    from app.rag.store import buscar

    res = buscar("diabetes tipo 2 metformina", k=4)
    scores = [r["score"] for r in res]
    assert scores == sorted(scores, reverse=True)