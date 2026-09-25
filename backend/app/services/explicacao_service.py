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
from app.services.exames_service import carregar_exames
from app.services.integracao_service import integrar

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an assistant that performs CROSS-READING of \
genetic reports on the cardiometabolic axis, cross-referencing the Diseases, Drugs, and Fit panels.

Respond entirely in ENGLISH (the "resumo", each "afirmacao", and each
item in "evidencia_insuficiente" must be written in English).

GROUNDING RULES (mandatory):
- You may ONLY state associations explicitly present in the provided CONTEXT \
(patient's report + retrieved literature excerpts).
- If the context does not support an association, record that point in 'evidencia_insuficiente'. \
NEVER invent numbers, genes, or associations.
- For each cross-reference statement, cite the source (the id of the literature excerpt, or 'laudo' \
when it comes from the patient's report) in the 'fontes' field.
- Respect the strength of evidence: connectors marked 'forte' may be stated with \
greater confidence; 'forte-fenotipo' (e.g., CHRM2) must be presented as tentative, making \
explicit that the genotype-phenotype bridge is weak; 'moderada-inconsistente' (e.g., ATM/metformin) \
must declare the replication uncertainty.
- Do NOT provide clinical or management recommendations. This is an educational reading.
- The ANAMNESE section provides the patient's clinical facts (e.g., smoking, BMI). You may \
acknowledge them as factual context and must NOT list them in 'evidencia_insuficiente'. \
However, do NOT interpret or assign weight to these facts — the quantitative weight is calculated \
separately by the system, outside your task.

OUTPUT FORMAT (mandatory): respond ONLY with a valid JSON object, with no text before \
or after, no code blocks, with this structure:
{
  "resumo": "string - the cross-reading in natural language (English)",
  "cruzamentos": [
    {"afirmacao": "string (English)", "fontes": ["string"], "confianca": "alta|moderada|baixa"}
  ],
  "evidencia_insuficiente": ["string (English) - points without coverage in the context"]
}

IMPORTANT: the JSON keys and the "confianca" values ("alta", "moderada", "baixa") \
must remain exactly as shown — do not translate the keys or the confidence \
values, only the free-text content."""


def _montar_contexto(laudo: PacienteLaudo, chunks: list[dict], exames: list | None = None) -> str:
    linhas = ["=== LAUDO DO PACIENTE (eixo cardiometabolico) ==="]
    for d in laudo.doencas:
        linhas.append(f"[Doenca] {d.doenca}: risco {d.risco_percentual}% ({d.faixa})")
    for f in laudo.farma:
        linhas.append(f"[Farma] {f.farmaco}: {f.interpretacao}")
    for t in laudo.fit:
        linhas.append(f"[Fit] {t.caracteristica}: {t.interpretacao}")

    # Fatos clinicos da anamnese (camada clinica). Entram como CONTEXTO factual:
    # a LLM pode reconhecer que existem, mas nao interpreta nem atribui peso —
    # o peso e tratado pelo motor deterministico, nao aqui.
    fatos_clinicos = [
        m for e in (exames or []) if getattr(e, "camada", None) == "clinico"
        for m in e.marcadores
    ]
    if fatos_clinicos:
        linhas.append("\n=== ANAMNESE (fatos clinicos do paciente) ===")
        for m in fatos_clinicos:
            linhas.append(f"[Clinico] {m.nome}: {m.valor}")

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

    # Carrega os exames antes, para a anamnese entrar no contexto da LLM.
    exames = carregar_exames(paciente_id)

    contexto = _montar_contexto(laudo, chunks, exames)
    user = f"CONTEXTO:\n{contexto}\n\nProduza a leitura cruzada do paciente {paciente_id}."

    resultado = llm.gerar_json(SYSTEM_PROMPT, user)

    _validar_saida(resultado)

    # Segundo cruzamento (ETAPA 3): integracao multi-omica deterministica.
    resultado["integracao_omica"] = integrar(laudo, exames)

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