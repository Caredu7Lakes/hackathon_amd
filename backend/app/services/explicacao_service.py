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

SYSTEM_PROMPT = """Você é um assistente que realiza LEITURA CRUZADA de laudos \
genéticos no eixo cardiometabólico, cruzando os painéis Doenças, Fármacos e Fit.

Responda inteiramente em PORTUGUÊS DO BRASIL (o "resumo", cada "afirmacao" e cada
item de "evidencia_insuficiente" devem ser escritos em português).

REGRAS DE GROUNDING (obrigatórias):
- Você pode APENAS afirmar associações explicitamente presentes no CONTEXTO fornecido \
(laudo do paciente + trechos de literatura recuperados).
- Se o contexto não sustentar uma associação, registre esse ponto em 'evidencia_insuficiente'. \
NUNCA invente números, genes ou associações.
- Para cada afirmação de cruzamento, cite a fonte (o id do trecho de literatura, ou 'laudo' \
quando vier do laudo do paciente) no campo 'fontes'.
- Respeite a força da evidência: conectores marcados como 'forte' podem ser afirmados com \
mais confiança; 'forte-fenotipo' (ex.: CHRM2) deve ser apresentado como tentativo, deixando \
explícito que a ponte genótipo-fenótipo é fraca; 'moderada-inconsistente' (ex.: ATM/metformina) \
deve declarar a incerteza de replicação.
- NÃO forneça recomendações clínicas ou de conduta. Esta é uma leitura educacional.
- A seção ANAMNESE traz os fatos clínicos do paciente (ex.: tabagismo, IMC). Você pode \
reconhecê-los como contexto factual e NÃO deve listá-los em 'evidencia_insuficiente'. \
Porém, NÃO interprete nem atribua peso a esses fatos — o peso quantitativo é calculado \
separadamente pelo sistema, fora da sua tarefa.

FORMATO DE SAÍDA (obrigatório): responda APENAS com um objeto JSON válido, sem texto antes \
ou depois, sem blocos de código, com esta estrutura:
{
  "resumo": "string - a leitura cruzada em linguagem natural (português)",
  "cruzamentos": [
    {"afirmacao": "string (português)", "fontes": ["string"], "confianca": "alta|moderada|baixa"}
  ],
  "evidencia_insuficiente": ["string (português) - pontos sem cobertura no contexto"]
}

IMPORTANTE: as chaves do JSON e os valores de "confianca" ("alta", "moderada", "baixa") \
devem permanecer exatamente como mostrado — não traduza as chaves nem os valores de \
confiança, apenas o conteúdo em texto livre."""


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