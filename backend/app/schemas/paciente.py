"""Schemas Pydantic do laudo genético.

Modelados sobre a estrutura real dos laudos Genera. Cada marcador carrega
rsid, gene, genótipo e efeito (peso). O campo `efeito` é o peso já tabelado
pela Genera — decisão A: não recalculamos nada, apenas estruturamos e lemos.

Estes schemas governam a Sprint 1 (ingestão dos PDFs → JSON validado).
"""

from pydantic import BaseModel, Field


class Marcador(BaseModel):
    """Um SNP de um laudo, com seu efeito tabelado."""

    rsid: str
    gene: str | None = None
    cromossomo: str | None = None
    genotipo: str | None = None
    efeito: float | None = None  # peso vindo do laudo; pode faltar em alguns painéis


class RiscoDoenca(BaseModel):
    """Entrada do painel de doenças: risco já calculado pela Genera."""

    doenca: str
    risco_percentual: float
    faixa: str | None = None  # ex.: "Risco aumentado" / "Risco padrão"
    marcadores: list[Marcador] = Field(default_factory=list)


class RespostaFarmaco(BaseModel):
    """Entrada do painel farma: interpretação de resposta a um fármaco."""

    farmaco: str
    genotipo: str | None = None
    interpretacao: str  # texto da predisposição (ex.: "menor taxa de resposta")
    marcadores: list[Marcador] = Field(default_factory=list)


class TraitFit(BaseModel):
    """Entrada do painel fit: característica de desempenho/predisposição física."""

    caracteristica: str
    interpretacao: str
    marcadores: list[Marcador] = Field(default_factory=list)


class PacienteLaudo(BaseModel):
    """Laudo estruturado de um paciente (fictício).

    Apenas os três painéis do eixo do MVP são obrigatórios no recorte
    cardiometabólico; os demais ficam para expansão.
    """

    paciente_id: str  # hash/ID fictício, nunca nome real
    doencas: list[RiscoDoenca] = Field(default_factory=list)
    farma: list[RespostaFarmaco] = Field(default_factory=list)
    fit: list[TraitFit] = Field(default_factory=list)
