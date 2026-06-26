"""rag/store.py — busca semantica sobre o indice FAISS.

Carrega o indice construido por ingest.py e expoe `buscar(query, k)`.
Sem LLM: retorna os chunks mais proximos da query. Coracao do teste
de aceite da Sprint 2 (busca por variante retorna o trecho certo).
"""

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class IndiceNaoConstruidoError(Exception):
    """Disparado quando o indice FAISS ainda nao foi construido."""


@lru_cache
def _carregar():
    import faiss
    from sentence_transformers import SentenceTransformer

    from app.rag.ingest import MODELO_EMBEDDING

    settings = get_settings()
    out = Path(settings.FAISS_INDEX_PATH)
    idx_path = out / "index.faiss"
    chunks_path = out / "chunks.json"
    if not idx_path.exists() or not chunks_path.exists():
        raise IndiceNaoConstruidoError(
            f"Indice nao encontrado em {out}. Rode ingest.construir_indice() antes."
        )
    indice = faiss.read_index(str(idx_path))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    modelo = SentenceTransformer(MODELO_EMBEDDING)
    return modelo, indice, chunks


def buscar(query: str, k: int = 4) -> list[dict]:
    import numpy as np

    modelo, indice, chunks = _carregar()
    vq = modelo.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    vq = np.asarray(vq, dtype="float32")
    scores, idxs = indice.search(vq, min(k, len(chunks)))
    resultados = []
    for score, i in zip(scores[0], idxs[0]):
        if i < 0:
            continue
        item = dict(chunks[i])
        item["score"] = float(score)
        resultados.append(item)
    return resultados