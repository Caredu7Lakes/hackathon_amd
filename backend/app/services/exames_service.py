"""services/exames_service.py — carga dos exames multi-omicos (ETAPA 3).

Aditivo e opcional: se o paciente nao tem exames, retorna lista vazia e o
sistema se comporta como antes. Sem LLM, sem recalculo aqui — apenas carga
e validacao contra o schema ExameOmico.
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.schemas.exames import ExameOmico


def carregar_exames(paciente_id: str) -> list[ExameOmico]:
    """Carrega todos os exames omicos de um paciente. Vazio se nao houver."""
    settings = get_settings()
    exames_dir = Path(getattr(settings, "EXAMES_DIR", "data/exames"))
    if not exames_dir.exists():
        return []
    exames = []
    for arq in sorted(exames_dir.glob(f"{paciente_id}_*.json")):
        dados = json.loads(arq.read_text(encoding="utf-8"))
        exames.append(ExameOmico.model_validate(dados))
    return exames