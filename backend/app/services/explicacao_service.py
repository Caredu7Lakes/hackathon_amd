"""services/explicacao_service.py — leitura cruzada com grounding estrito.

Orquestra: laudo (leitura_service) + chunks recuperados (RAG) -> LLM -> JSON
validado. A LLM so afirma o que esta no contexto recuperado; sem cobertura,
deve responder 'evidencia insuficiente'. Disclaimer e anexado sempre.

A LLM e injetada (LLMClient), permitindo mock nos testes.
"""

from app.core.disclaimer import DISCLAIMER_OBRIGATORIO
from app.core.llm import LLMClient, get_llm_client
from app.core.logging_config import get_logger
from app.rag.store import buscar
from app.schemas.paciente import PacienteLaudo
from app.services.leitura_service import carregar_laudo

logger = get_logger(__name__)

SYSTEM_PROMPT = """Voce e um assistente que faz LEITURA CRUZADA de laudos geneticos \
no eixo cardiometabolico, cruzando os paineis Doencas, Farma e Fit.

REGRAS DE GROUNDING (obrigatorias):
- Voce SO pode afirmar associacoes que estejam explicitamente no CONTEXTO fornecido \
(laudo do paciente + trechos de literatura recuperados).
- Se o contexto nao sustentar uma associacao, escreva 'evidencia insuficiente' para \
aquele ponto. NUNCA invente numeros, genes ou associacoes.
- Para cada afirmacao de cruzamento, cite a fonte (id do trecho de literatura ou \
'laudo' quando vier do laudo do paciente) no campo 'fontes'.
- Respeite a forca de evidencia: conectores marcados como 'forte' podem ser afirmados \
com mais confianca; 'forte-fenotipo' (ex.: CHRM2) devem ser apresentados como brandos, \
explicitando que a ponte genotipo-fenotipo e fraca; 'moderada-inconsistente' (ex.: ATM/\
metformina) devem declarar a incerteza de replicacao.
- NAO de recomendacao clinica nem de conduta. Isto e leitura educacional.

FORMATO DE SAIDA (obrigatorio): responda APENAS com um objeto JSON valido, sem \
texto antes ou depois, sem blocos de codigo, com esta estrutura:
{
  "resumo": "string - leitura cruzada em linguagem natural",
  "cruzamentos": [
    {"afirmacao": "string", "fontes": ["string"], "confianca": "alta|moderada|baixa"}
  ],
  "evidencia_insuficiente": ["string - pontos sem cobertura no contexto"]
}"""


def _montar_contexto(laudo: PacienteLaudo, chunks: list[dict]) -> str:
    linhas = ["=== LAUDO DO PACIENTE (eixo cardiometabolico) ==="]
    for d in laudo.doencas:
        linhas.append(f"[Doenca] {d.doenca}: risco {d.risco_percentual}% ({d.faixa})")
    for f in laudo.farma:
        linhas.append(f"[Farma] {f.farmaco}: {f.interpretacao}")
    for t in laudo.fit:
        linhas.append(f"[Fit] {t.caracteristica}: {t.interpretacao}")
    linhas.append("\n=== LITERATURA RECUPERADA ===")
    for c in chunks:
        if c.get("tipo") == "corpus":
            linhas.append(
                f"[fonte:{c.get('id')}] (evidencia: {c.get('evidencia')}) {c.get('texto')}"
            )
    return "\n".join(linhas)


def gerar_leitura(paciente_id: str, llm: LLMClient | None = None) -> dict:
    """Produz a leitura cruzada de um paciente. Retorna dict pronto para a API.

    llm injetavel: em testes passa-se um mock; em producao usa Bedrock.
    """
    laudo = carregar_laudo(paciente_id)
    llm = llm or get_llm_client()

    termos = "diabetes tipo 2 doenca arterial coronariana metformina estatina FTO obesidade recuperacao cardiaca"
    chunks = buscar(termos, k=6)

    contexto = _montar_contexto(laudo, chunks)
    user = f"CONTEXTO:\n{contexto}\n\nProduza a leitura cruzada do paciente {paciente_id}."

    resultado = llm.gerar_json(SYSTEM_PROMPT, user)

    _validar_saida(resultado)

    resultado["disclaimer"] = DISCLAIMER_OBRIGATORIO
    resultado["paciente_id"] = paciente_id
    return resultado


def _validar_saida(r: dict) -> None:
    """Rejeita saida fora do contrato. Grounding: cada cruzamento precisa de fonte."""
    for chave in ("resumo", "cruzamentos", "evidencia_insuficiente"):
        if chave not in r:
            raise ValueError(f"Saida da LLM sem campo obrigatorio: '{chave}'")
    if not isinstance(r["cruzamentos"], list):
        raise ValueError("Campo 'cruzamentos' deve ser lista")
    for c in r["cruzamentos"]:
        if not c.get("fontes"):
            raise ValueError("Cruzamento sem fonte: viola grounding estrito")