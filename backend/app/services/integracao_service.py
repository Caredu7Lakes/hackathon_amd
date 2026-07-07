"""services/integracao_service.py — motor de integracao multi-omica (ETAPA 3).

Deterministico, SEM LLM (decisao A do ETAPA 0): os pesos vem dos exames
(literatura publicada); aqui so se aplica a aritmetica de Cox, transparente
e auditavel. A LLM nunca toca nestes numeros.

Fronteira de honestidade (ETAPA 3, secao 2): os modificadores sao
ESTRATIFICADOS POR DESFECHO. Risco-base e modificadores de desfechos
distintos NUNCA sao fundidos num unico numero. Cada modificador carrega
peso, IC, fonte e desfecho.
"""

from app.schemas.exames import ExameOmico
from app.schemas.paciente import PacienteLaudo


def _risco_base_por_desfecho(laudo: PacienteLaudo) -> dict[str, float]:
    """Mapa desfecho -> risco percentual base, vindo do laudo (PRS)."""
    base = {}
    for d in laudo.doencas:
        base[d.doenca.lower()] = d.risco_percentual
    return base


def integrar(laudo: PacienteLaudo, exames: list[ExameOmico]) -> dict:
    """Produz a leitura multi-omica estratificada por desfecho.

    Para cada modificador de exame, registra o peso publicado e a que
    desfecho se aplica, mantendo a camada-base separada. Nao soma desfechos
    distintos; nao recalcula o PRS — apenas relê o paciente por camadas.
    """
    base = _risco_base_por_desfecho(laudo)

    modificadores = []
    for exame in exames:
        for m in exame.marcadores:
            p = m.peso
            modificadores.append(
                {
                    "camada": exame.camada,
                    "marcador": m.nome,
                    "valor": m.valor,
                    "hazard_ratio": p.hazard_ratio,
                    "ic_95": list(p.ic_95),
                    "fonte": p.fonte_id,
                    "desfecho": p.desfecho,
                    "direcao": p.direcao,
                }
            )

    # Agrupa modificadores por desfecho — estratificacao (nunca funde).
    por_desfecho: dict[str, list[dict]] = {}
    for mod in modificadores:
        por_desfecho.setdefault(mod["desfecho"], []).append(mod)

    return {
        "risco_base_genetico": base,
        "camadas_presentes": sorted({e.camada for e in exames}),
        "modificadores_por_desfecho": por_desfecho,
    }