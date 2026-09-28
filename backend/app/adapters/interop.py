"""adapters/interop.py — interoperabilidade de entrada (VCF + FHIR-lite).

Ports-and-adapters: normaliza entrada externa para os schemas que o motor
determinístico já consome. NÃO recalcula nada, NÃO inventa peso — apenas
estrutura e anexa proveniência (mesma fronteira de honestidade da ETAPA 3).

- VCF  -> list[Marcador]  (encaixe direto no schema existente)
- FHIR -> FatoClinico     (medições/condições brutas, sem peso)

O VCF é filtrado por uma lista curada de variantes de interesse clínico:
não se joga o VCF inteiro em lugar nenhum — extrai-se deterministicamente
só o que tem relevância validada. Variante sem mapeamento é descartada.
"""

from dataclasses import dataclass, field

from app.schemas.paciente import Marcador

# --- VCF -------------------------------------------------------------------

# rsid -> gene conhecido (curadoria clínica; expanda pela sua base).
# Só variantes aqui são extraídas — o resto do VCF é ignorado de propósito.
VARIANTES_ALVO: dict[str, str] = {
    "rs662799": "APOA5",    # triglicerídeos / risco cardiometabólico
    "rs1801133": "MTHFR",   # homocisteína
    "rs9939609": "FTO",     # obesidade / DM2
}


def extrair_variantes_vcf(caminho_vcf: str) -> list[Marcador]:
    """Lê um VCF e devolve só as variantes-alvo como Marcador (schema existente).

    Requer `cyvcf2` (pip install cyvcf2). Genótipo em notação de bases (ex.: 'A/G').
    `efeito` fica None: o peso não vem do VCF — é anexado pela camada clínica,
    não inventado aqui.
    """
    from cyvcf2 import VCF

    marcadores: list[Marcador] = []
    for var in VCF(caminho_vcf):
        if var.ID in VARIANTES_ALVO:
            marcadores.append(
                Marcador(
                    rsid=var.ID,
                    gene=VARIANTES_ALVO[var.ID],
                    cromossomo=str(var.CHROM),
                    genotipo=var.gt_bases[0] if len(var.gt_bases) else None,
                    efeito=None,
                )
            )
    return marcadores


# --- FHIR-lite -------------------------------------------------------------


@dataclass
class FatoClinico:
    """Fato clínico bruto vindo de um bundle FHIR, com proveniência.

    Não é MarcadorExame (que exige peso publicado). É medição/diagnóstico
    factual — entra como CONTEXTO de anamnese, não como peso do motor.
    """

    codigo: str          # LOINC (Observation) ou SNOMED CT (Condition)
    descricao: str
    valor: str | None    # medições têm valor; condições não
    tipo: str            # "observation" | "condition" | "diagnostic_report"
    fonte: str = "FHIR"


def extrair_fatos_fhir(bundle: dict) -> list[FatoClinico]:
    """Parseia só os recursos que importam de um bundle FHIR (JSON).

    Observation -> medição (LOINC); Condition -> diagnóstico (SNOMED CT);
    DiagnosticReport -> laudo. Nada mais é lido.
    """
    fatos: list[FatoClinico] = []
    for entry in bundle.get("entry", []):
        r = entry.get("resource", {})
        tipo = r.get("resourceType")

        if tipo == "Observation":
            coding = r.get("code", {}).get("coding", [{}])[0]
            valor = r.get("valueQuantity", {}).get("value")
            unidade = r.get("valueQuantity", {}).get("unit", "")
            fatos.append(FatoClinico(
                codigo=coding.get("code", ""),
                descricao=coding.get("display", ""),
                valor=f"{valor} {unidade}".strip() if valor is not None else None,
                tipo="observation",
            ))
        elif tipo == "Condition":
            coding = r.get("code", {}).get("coding", [{}])[0]
            fatos.append(FatoClinico(
                codigo=coding.get("code", ""),
                descricao=coding.get("display", ""),
                valor=None,
                tipo="condition",
            ))
        elif tipo == "DiagnosticReport":
            coding = r.get("code", {}).get("coding", [{}])[0]
            fatos.append(FatoClinico(
                codigo=coding.get("code", ""),
                descricao=coding.get("display", r.get("conclusion", "")),
                valor=None,
                tipo="diagnostic_report",
            ))
    return fatos


# --- Normalizador ----------------------------------------------------------


@dataclass
class EntradaNormalizada:
    """Saída dos adaptadores, pronta para o motor. Camada-base intacta."""

    variantes: list[Marcador] = field(default_factory=list)
    fatos_clinicos: list[FatoClinico] = field(default_factory=list)


def normalizar(
    caminho_vcf: str | None = None,
    bundle_fhir: dict | None = None,
) -> EntradaNormalizada:
    """Funde VCF + FHIR num objeto de entrada, mantendo proveniência.

    Não toca no PRS base nem nos pesos publicados: variantes são evidência
    genética adicional; fatos clínicos são anamnese factual.
    """
    return EntradaNormalizada(
        variantes=extrair_variantes_vcf(caminho_vcf) if caminho_vcf else [],
        fatos_clinicos=extrair_fatos_fhir(bundle_fhir) if bundle_fhir else [],
    )