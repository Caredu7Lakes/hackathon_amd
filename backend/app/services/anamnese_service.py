"""services/anamnese_service.py — classificação clínica + cruzamento determinístico.

SEM LLM. Duas operações, ambas por regra auditável:

1. classificar_clinico(): aplica CORTES diagnósticos publicados a medições
   brutas, identificadas por CÓDIGO LOINC (padrão universal de
   interoperabilidade). Ex.: glicemia de jejum (LOINC 1558-6) >=100 ->
   pré-diabetes (corte ADA). É classificação, não peso — o número vira
   rótulo diagnóstico, nunca hazard ratio.

2. cruzar_anamnese_exames(): compara o que a anamnese declara com o que os
   exames mostram, gerando um mapa de CONCORDÂNCIA / DISCREPÂNCIA. Não
   diagnostica: apenas sinaliza divergências para revisão clínica humana.

Chavear por LOINC (e não por nome de exame) elimina a variação de
nomenclatura entre laboratórios: o mesmo código identifica o analito
qualquer que seja o texto do laudo. Os achados chegam via FHIR
(Observation.code.coding.code), do adaptador interop.py.

Fronteira de honestidade: um flag de discrepância é um alerta de revisão,
nunca uma conclusão diagnóstica.
"""

from dataclasses import dataclass

from app.schemas.anamnese import Anamnese, DiabetesStatus

# --- Códigos LOINC canônicos ------------------------------------------------

LOINC_GLICEMIA_JEJUM = "1558-6"
LOINC_PA_SISTOLICA = "8480-6"
LOINC_PA_DIASTOLICA = "8462-4"


@dataclass
class AchadoClinico:
    """Medição clínica bruta, identificada por LOINC. Desacoplada do schema
    de exame — o chamador constrói a partir de um FHIR Observation."""

    loinc: str       # ex.: "1558-6"
    valor: float
    unidade: str = ""


@dataclass
class Classificacao:
    """Resultado de aplicar um corte diagnóstico a um achado."""

    loinc: str
    marcador: str
    valor: float
    rotulo: str      # ex.: "pre_diabetes"
    corte_fonte: str # ex.: "ADA"


# --- Cortes diagnósticos (regras de classificação, não pesos) --------------


def classificar_glicemia(valor: float) -> Classificacao:
    """Glicemia de jejum (mg/dL) — cortes ADA: <100 normal, 100-125
    pré-diabetes, >=126 diabetes."""
    if valor >= 126:
        rotulo = "diabetes"
    elif valor >= 100:
        rotulo = "pre_diabetes"
    else:
        rotulo = "normal"
    return Classificacao(LOINC_GLICEMIA_JEJUM, "glicemia_jejum", valor, rotulo, "ADA")


def classificar_pa(pas: float, pad: float) -> Classificacao:
    """Pressão arterial (mmHg) — corte de hipertensão >=140/90 (consultório)."""
    rotulo = "hipertensao" if (pas >= 140 or pad >= 90) else "normal"
    return Classificacao(LOINC_PA_SISTOLICA, "pressao_arterial", pas, rotulo, "Diretriz HAS")


def classificar_clinico(achados: list[AchadoClinico]) -> list[Classificacao]:
    """Aplica os cortes disponíveis aos achados reconhecidos por LOINC.
    Achado com LOINC sem regra é ignorado (não se inventa classificação)."""
    por_loinc = {a.loinc: a.valor for a in achados}
    out: list[Classificacao] = []
    if LOINC_GLICEMIA_JEJUM in por_loinc:
        out.append(classificar_glicemia(por_loinc[LOINC_GLICEMIA_JEJUM]))
    if LOINC_PA_SISTOLICA in por_loinc and LOINC_PA_DIASTOLICA in por_loinc:
        out.append(classificar_pa(
            por_loinc[LOINC_PA_SISTOLICA], por_loinc[LOINC_PA_DIASTOLICA]
        ))
    return out


# --- Cruzamento anamnese × exame -------------------------------------------


@dataclass
class Cruzamento:
    """Item do mapa de concordância/discrepância."""

    tipo: str        # "concordancia" | "discrepancia"
    dominio: str     # ex.: "glicemia"
    anamnese: str    # o que a anamnese declarou
    exame: str       # o que o exame mostrou
    mensagem: str


def cruzar_anamnese_exames(
    anamnese: Anamnese, achados: list[AchadoClinico]
) -> list[Cruzamento]:
    """Cruza declarações da anamnese com achados classificados por LOINC.

    Regra geral: negação na anamnese + achado positivo no exame -> discrepância;
    coerência entre os dois -> concordância. Só domínios com corte e com
    declaração correspondente são avaliados.
    """
    classes = {c.marcador: c for c in classificar_clinico(achados)}
    out: list[Cruzamento] = []

    # Glicemia × diabetes declarado
    if "glicemia_jejum" in classes:
        c = classes["glicemia_jejum"]
        nega = anamnese.diabetes_previo == DiabetesStatus.nao
        if c.rotulo in ("pre_diabetes", "diabetes") and nega:
            out.append(Cruzamento(
                "discrepancia", "glicemia",
                "nega diabetes/pré-diabetes",
                f"glicemia {c.valor:.0f} mg/dL ({c.rotulo})",
                f"Glicemia laboratorial compatível com {c.rotulo} não relatada na anamnese.",
            ))
        elif c.rotulo in ("pre_diabetes", "diabetes") and not nega:
            out.append(Cruzamento(
                "concordancia", "glicemia",
                f"relata {anamnese.diabetes_previo.value}",
                f"glicemia {c.valor:.0f} mg/dL ({c.rotulo})",
                "Achado laboratorial coerente com o relato da anamnese.",
            ))

    # Pressão arterial × hipertensão declarada
    if "pressao_arterial" in classes:
        c = classes["pressao_arterial"]
        if c.rotulo == "hipertensao" and not anamnese.hipertensao_previa:
            out.append(Cruzamento(
                "discrepancia", "pressao_arterial",
                "nega hipertensão",
                f"PA elevada ({c.valor:.0f} mmHg sistólica)",
                "Pressão elevada na medição não relatada na anamnese.",
            ))
        elif c.rotulo == "hipertensao" and anamnese.hipertensao_previa:
            out.append(Cruzamento(
                "concordancia", "pressao_arterial",
                "relata hipertensão",
                f"PA elevada ({c.valor:.0f} mmHg sistólica)",
                "Medição coerente com o relato da anamnese.",
            ))

    return out


# --- Carregamento e ponte com FHIR -----------------------------------------

import json
from pathlib import Path

from app.core.config import get_settings
from app.adapters.interop import extrair_fatos_fhir


def carregar_anamnese(paciente_id: str) -> Anamnese | None:
    """Lê a anamnese estruturada de data/anamnese/. Ausente -> None (paciente
    sem anamnese não quebra o fluxo existente)."""
    caminho = Path(get_settings().ANAMNESE_DIR) / f"paciente_{paciente_id}.json"
    if not caminho.exists():
        return None
    return Anamnese.model_validate_json(caminho.read_text(encoding="utf-8"))


def carregar_achados_fhir(paciente_id: str) -> list[AchadoClinico]:
    """Lê o bundle FHIR de data/fhir/ e converte Observations em AchadoClinico
    (LOINC + valor numérico). Ausente -> lista vazia."""
    caminho = Path(get_settings().FHIR_DIR) / f"paciente_{paciente_id}.json"
    if not caminho.exists():
        return []
    bundle = json.loads(caminho.read_text(encoding="utf-8"))
    achados: list[AchadoClinico] = []
    for f in extrair_fatos_fhir(bundle):
        if f.tipo == "observation" and f.valor:
            try:
                num = float(f.valor.split()[0])  # "118 mg/dL" -> 118.0
            except (ValueError, IndexError):
                continue
            achados.append(AchadoClinico(loinc=f.codigo, valor=num))
    return achados


def gerar_cruzamento_clinico(paciente_id: str) -> dict | None:
    """Orquestra: carrega anamnese + FHIR, cruza, devolve dict para a API.
    Retorna None se não houver anamnese (nada a cruzar)."""
    anamnese = carregar_anamnese(paciente_id)
    if anamnese is None:
        return None
    achados = carregar_achados_fhir(paciente_id)
    cruzamentos = cruzar_anamnese_exames(anamnese, achados)
    return {
        "classificacoes": [c.__dict__ for c in classificar_clinico(achados)],
        "cruzamentos": [c.__dict__ for c in cruzamentos],
        "nota": "Discrepâncias são alertas de revisão clínica, não diagnósticos.",
    }