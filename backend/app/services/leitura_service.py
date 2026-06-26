"""leitura_service — deterministico.

Carrega o laudo de um paciente (JSON curado em data/laudos/) e o valida contra
o schema PacienteLaudo. Sem LLM no circuito: entrada conhecida -> saida previsivel.
E a peca com cobertura de teste unitario real (decisao ETAPA 0, secao 2.1).
"""

import json
from pathlib import Path

from app.core.config import get_settings
from app.schemas.paciente import PacienteLaudo


class LaudoNaoEncontradoError(Exception):
    """Disparado quando o JSON do paciente nao existe em data/laudos/."""


def carregar_laudo(paciente_id: str) -> PacienteLaudo:
    """Le e valida o laudo de um paciente pelo ID.

    Levanta LaudoNaoEncontradoError se o arquivo nao existir.
    Levanta pydantic.ValidationError se o JSON nao bater com o schema.
    """
    settings = get_settings()
    caminho = Path(settings.LAUDOS_DIR) / f"paciente_{paciente_id}.json"
    if not caminho.exists():
        raise LaudoNaoEncontradoError(
            f"Laudo nao encontrado para paciente_id='{paciente_id}' em {caminho}"
        )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return PacienteLaudo.model_validate(dados)


def listar_pacientes() -> list[str]:
    """Lista os paciente_id disponiveis em data/laudos/."""
    settings = get_settings()
    laudos_dir = Path(settings.LAUDOS_DIR)
    if not laudos_dir.exists():
        return []
    ids = []
    for arquivo in sorted(laudos_dir.glob("paciente_*.json")):
        nome = arquivo.stem.removeprefix("paciente_")
        ids.append(nome)
    return ids