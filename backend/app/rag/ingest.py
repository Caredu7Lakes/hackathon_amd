"""rag/ingest.py — ingestao do corpus para o indice FAISS.

Le o corpus cientifico (data/corpus/*.json) e os laudos (data/laudos/*.json),
transforma cada um em chunks de texto com metadados, gera embeddings com um
modelo local (sentence-transformers, offline) e persiste um indice FAISS.

Decisoes: embeddings 100% locais (sem API), FAISS local em arquivo.
Sem LLM neste modulo — so recuperacao.
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def _detectar_dispositivo() -> str:
    """Detecta o melhor dispositivo disponível para embeddings.

    Ordem: GPU AMD (ROCm) -> GPU NVIDIA (CUDA) -> CPU. O PyTorch com ROCm
    expõe a GPU AMD pela mesma API 'cuda' (torch.cuda.is_available()), entao
    a deteccao cobre ambas. Fallback para CPU e transparente: o sistema roda
    igual ao estado atual quando nenhuma GPU esta presente.
    """
    try:
        import torch

        if torch.cuda.is_available():
            nome = torch.cuda.get_device_name(0)
            # ROCm reporta o nome da GPU AMD (ex.: 'AMD Instinct MI300X').
            backend = "ROCm/HIP" if getattr(torch.version, "hip", None) else "CUDA"
            logger.info("GPU detectada: %s (backend %s)", nome, backend)
            return "cuda"
    except Exception as e:  # noqa: BLE001
        logger.info("Sem GPU utilizavel (%s); usando CPU.", e)
    logger.info("Usando CPU para embeddings.")
    return "cpu"


def _chunks_do_corpus(corpus_dir: Path) -> list[dict]:
    chunks = []
    for arq in sorted(corpus_dir.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        texto = f"{d.get('titulo', '')}. {d.get('texto', '')}"
        chunks.append(
            {
                "texto": texto,
                "tipo": "corpus",
                "id": d.get("id"),
                "fonte": d.get("fonte"),
                "gene": d.get("gene"),
                "rsid": d.get("rsid"),
                "evidencia": d.get("evidencia"),
            }
        )
    return chunks


def _chunks_dos_laudos(laudos_dir: Path) -> list[dict]:
    chunks = []
    for arq in sorted(laudos_dir.glob("paciente_*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        pid = d.get("paciente_id")
        for doenca in d.get("doencas", []):
            rsids = ", ".join(m["rsid"] for m in doenca.get("marcadores", []))
            genes = ", ".join(sorted({m.get("gene", "") for m in doenca.get("marcadores", [])}))
            texto = (
                f"Doenca: {doenca['doenca']}. Risco: {doenca['risco_percentual']}% "
                f"({doenca.get('faixa', '')}). Genes: {genes}. Marcadores: {rsids}."
            )
            chunks.append({"texto": texto, "tipo": "laudo_doenca", "paciente_id": pid, "id": doenca["doenca"]})
        for f in d.get("farma", []):
            rsids = ", ".join(m["rsid"] for m in f.get("marcadores", []))
            texto = f"Farmaco: {f['farmaco']}. {f['interpretacao']}. Marcadores: {rsids}."
            chunks.append({"texto": texto, "tipo": "laudo_farma", "paciente_id": pid, "id": f["farmaco"]})
        for t in d.get("fit", []):
            rsids = ", ".join(m["rsid"] for m in t.get("marcadores", []))
            texto = f"Caracteristica fisica: {t['caracteristica']}. {t['interpretacao']}. Marcadores: {rsids}."
            chunks.append({"texto": texto, "tipo": "laudo_fit", "paciente_id": pid, "id": t["caracteristica"]})
    return chunks


def construir_indice() -> int:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    corpus_chunks = _chunks_do_corpus(Path(settings.CORPUS_DIR))
    laudo_chunks = _chunks_dos_laudos(Path(settings.LAUDOS_DIR))
    todos = corpus_chunks + laudo_chunks
    if not todos:
        raise RuntimeError("Nenhum chunk para indexar. Verifique data/corpus e data/laudos.")

    dispositivo = _detectar_dispositivo()
    logger.info("Carregando modelo de embedding local: %s (dispositivo: %s)", MODELO_EMBEDDING, dispositivo)
    modelo = SentenceTransformer(MODELO_EMBEDDING, device=dispositivo)
    textos = [c["texto"] for c in todos]
    vetores = modelo.encode(textos, convert_to_numpy=True, normalize_embeddings=True)
    vetores = np.asarray(vetores, dtype="float32")

    dim = vetores.shape[1]
    indice = faiss.IndexFlatIP(dim)
    indice.add(vetores)

    out = Path(settings.FAISS_INDEX_PATH)
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(indice, str(out / "index.faiss"))
    (out / "chunks.json").write_text(
        json.dumps(todos, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    logger.info("Indice FAISS construido com %d chunks (dim=%d)", len(todos), dim)
    return len(todos)


if __name__ == "__main__":
    from app.core.logging_config import configure_logging

    configure_logging()
    n = construir_indice()
    print(f"OK: {n} chunks indexados.")