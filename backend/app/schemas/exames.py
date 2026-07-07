"""Schemas dos exames multi-ômicos (ETAPA 3).

Camadas aditivas sobre o laudo genético (PRS base). Cada marcador de exame
carrega um peso PUBLICADO (hazard_ratio) com sua fonte, intervalo de
confiança e o DESFECHO específico a que se aplica — a fronteira de
honestidade do ETAPA 3, seção 2.2. Nada aqui é recalculado pelo sistema;
os pesos vêm da literatura e são apenas estruturados.
"""

from pydantic import BaseModel, Field


class PesoPublicado(BaseModel):
    """Peso estatístico de um marcador, ancorado na literatura.

    Os quatro atributos obrigatórios do ETAPA 3 (seção 2.2): valor do peso,
    intervalo de confiança, fonte publicada e desfecho explícito.
    """

    hazard_ratio: float  # peso por desvio-padrão / por presença do marcador
    ic_95: tuple[float, float]  # intervalo de confiança de 95%
    fonte_id: str  # id da fonte no corpus (ex.: "liu_2024_microbiome")
    desfecho: str  # ex.: "diabetes tipo 2 incidente"
    direcao: str  # "risco" ou "protecao" — sinal qualitativo da associação


class MarcadorExame(BaseModel):
    """Um marcador de exame multi-ômico (táxon, métrica ou sítio CpG)."""

    nome: str  # ex.: "Akkermansia muciniphila", "cg05575921", "Shannon index"
    valor: str  # valor fictício do paciente (ex.: "reduzida", "0.42", "hipometilado")
    tipo_marcador: str  # "taxon" | "metrica_diversidade" | "sitio_cpg"
    peso: PesoPublicado


class ExameOmico(BaseModel):
    """Exame de uma camada ômica (microbioma ou metilação) de um paciente."""

    paciente_id: str
    camada: str  # "microbioma" | "metilacao"
    metodo: str  # ex.: "shotgun metagenomics", "array de metilação (EWAS)"
    marcadores: list[MarcadorExame] = Field(default_factory=list)