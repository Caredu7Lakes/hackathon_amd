"""Benchmark do embedding — compara desempenho por dispositivo (CPU vs GPU AMD).

Mede o tempo de geracao de embeddings do corpus atual no dispositivo detectado.
Rode antes (CPU) e depois (GPU AMD via ROCm, quando a nuvem do hackathon abrir)
para obter o ganho mensuravel. Saida honesta: registra dispositivo, numero de
textos, tempo total e tempo por texto.
"""
import json
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.rag.ingest import MODELO_EMBEDDING, _detectar_dispositivo

logger = get_logger(__name__)


def _carregar_textos() -> list[str]:
    """Reune os textos do corpus + laudos, como o ingest faz."""
    settings = get_settings()
    textos = []
    for arq in sorted(Path(settings.CORPUS_DIR).glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        textos.append(f"{d.get('titulo', '')}. {d.get('texto', '')}")
    return textos


def benchmark(repeticoes: int = 3) -> dict:
    from sentence_transformers import SentenceTransformer

    dispositivo = _detectar_dispositivo()
    textos = _carregar_textos()
    if not textos:
        raise RuntimeError("Nenhum texto no corpus para benchmark.")

    modelo = SentenceTransformer(MODELO_EMBEDDING, device=dispositivo)
    # Warm-up: primeira passada carrega pesos/kernels, nao conta.
    modelo.encode(textos, convert_to_numpy=True, normalize_embeddings=True)

    tempos = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        modelo.encode(textos, convert_to_numpy=True, normalize_embeddings=True)
        tempos.append(time.perf_counter() - inicio)

    media = sum(tempos) / len(tempos)
    resultado = {
        "dispositivo": dispositivo,
        "n_textos": len(textos),
        "repeticoes": repeticoes,
        "tempo_total_medio_s": round(media, 4),
        "tempo_por_texto_ms": round(media / len(textos) * 1000, 3),
        "tempos_por_rodada_s": [round(t, 4) for t in tempos],
    }
    return resultado


if __name__ == "__main__":
    configure_logging()
    r = benchmark()
    logger.info("Benchmark concluido: %s", r)
    print(json.dumps(r, ensure_ascii=True, indent=2))