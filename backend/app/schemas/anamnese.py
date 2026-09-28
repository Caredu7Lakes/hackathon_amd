"""schemas/anamnese.py — anamnese estruturada (33 itens).

Padroniza a coleta em perguntas fechadas e tipadas, para serem parseáveis
e cruzáveis por regra determinística contra os exames. Baseada nos 7 blocos
clássicos da semiologia (identificação, QP, HMA, antecedentes, história
familiar, hábitos de vida, revisão de sistemas), enviesada para o eixo
cardiometabólico do GenRisk.

NÃO interpreta nem pondera: apenas estrutura o relato do paciente. A
interpretação (classificação por corte, cruzamento) fica no service.
"""

from enum import Enum

from pydantic import BaseModel, Field, computed_field


class Sexo(str, Enum):
    masculino = "masculino"
    feminino = "feminino"


class Ancestralidade(str, Enum):
    europeia = "europeia"
    africana = "africana"
    indigena = "indigena"
    asiatica = "asiatica"
    mista = "mista"
    nao_informada = "nao_informada"


class DiabetesStatus(str, Enum):
    nao = "nao"
    pre_diabetes = "pre_diabetes"
    diabetes = "diabetes"


class TabagismoStatus(str, Enum):
    nunca = "nunca"
    ex_fumante = "ex_fumante"
    atual = "atual"


class EtilismoFrequencia(str, Enum):
    nunca = "nunca"
    ocasional = "ocasional"
    semanal = "semanal"
    diario = "diario"


class AtividadeFisica(str, Enum):
    sedentario = "sedentario"
    insuficiente = "insuficiente"
    ativo = "ativo"


class PadraoAlimentar(str, Enum):
    adequado = "adequado"
    irregular = "irregular"
    inadequado = "inadequado"


class Humor(str, Enum):
    estavel = "estavel"
    ansioso = "ansioso"
    deprimido = "deprimido"
    estressado = "estressado"


class Anamnese(BaseModel):
    """Anamnese estruturada de um paciente — 33 itens em 7 blocos."""

    paciente_id: str

    # --- Identificação (4) ---
    idade: int
    sexo: Sexo
    ocupacao: str
    ancestralidade: Ancestralidade = Ancestralidade.nao_informada

    # --- Queixa principal (1) ---
    motivo: str

    # --- HMA: sintomas cardiometabólicos atuais (5) ---
    dor_toracica_esforco: bool = False       # -> DAC
    dispneia_esforco: bool = False           # -> respiratório
    palpitacoes: bool = False
    poliuria_polidipsia: bool = False        # -> glicemia
    edema_claudicacao: bool = False

    # --- Antecedentes pessoais (7) ---
    diabetes_previo: DiabetesStatus = DiabetesStatus.nao   # -> glicemia
    hipertensao_previa: bool = False                        # -> PA
    dislipidemia: bool = False                              # -> lipídios
    evento_cv_previo: bool = False                          # IAM/AVC
    cirurgias: str | None = None
    medicacoes: list[str] = Field(default_factory=list)     # -> painel farma
    alergias: str | None = None

    # --- História familiar (4) ---
    hf_dac_precoce: bool = False             # <55H / <65M -> painel DAC
    hf_diabetes: bool = False                # -> painel DM
    hf_hipercolesterolemia: bool = False
    hf_morte_subita: bool = False

    # --- Hábitos de vida (8) — núcleo das camadas clínicas ---
    tabagismo_status: TabagismoStatus = TabagismoStatus.nunca   # -> fumo
    tabagismo_macos_ano: float | None = None                    # -> fumo
    etilismo_frequencia: EtilismoFrequencia = EtilismoFrequencia.nunca  # -> curva-J
    etilismo_doses_semana: float | None = None                  # -> curva-J
    atividade_fisica: AtividadeFisica = AtividadeFisica.sedentario
    padrao_alimentar: PadraoAlimentar = PadraoAlimentar.irregular
    sono_horas: float | None = None
    peso_kg: float | None = None                                # -> IMC
    altura_m: float | None = None                               # -> IMC

    # --- Revisão de sistemas (4) ---
    sintomas_respiratorios: bool = False     # tosse/sibilância -> respiratório
    sintomas_urinarios: bool = False
    humor: Humor = Humor.estavel
    uso_substancias: bool = False            # suplementos/ilícitas

    @computed_field  # type: ignore[prop-decorator]
    @property
    def imc(self) -> float | None:
        """IMC calculado (peso/altura²), quando ambos presentes."""
        if self.peso_kg and self.altura_m:
            return round(self.peso_kg / (self.altura_m ** 2), 1)
        return None