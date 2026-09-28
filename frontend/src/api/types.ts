// Contrato de saida do backend (espelha o JSON de /api/v1/leitura).
// Tipar isto explicitamente e a rede de seguranca contra ler campo
// que nao existe — o TypeScript pega o erro antes da banca.

export type Confianca = 'alta' | 'moderada' | 'baixa'

export interface Cruzamento {
  afirmacao: string
  fontes: string[]
  confianca: Confianca
}

export interface Leitura {
  resumo: string
  cruzamentos: Cruzamento[]
  evidencia_insuficiente: string[]
  disclaimer: string
  paciente_id: string
  integracao_omica: IntegracaoOmica
  cruzamento_clinico?: CruzamentoClinico
}

export interface ListaPacientes {
  pacientes: string[]
}

export interface Modificador {
  camada: string
  marcador: string
  valor: string
  hazard_ratio: number
  ic_95: [number, number]
  fonte: string
  desfecho: string
  direcao: string
}

export interface IntegracaoOmica {
  risco_base_genetico: Record<string, number>
  camadas_presentes: string[]
  modificadores_por_desfecho: Record<string, Modificador[]>
}

// --- Cruzamento clinico (anamnese × exame, LOINC) ---

export interface ClassificacaoClinica {
  loinc: string
  marcador: string
  valor: number
  rotulo: string
  corte_fonte: string
}

export interface CruzamentoClinicoItem {
  tipo: 'concordancia' | 'discrepancia'
  dominio: string
  anamnese: string
  exame: string
  mensagem: string
}

export interface CruzamentoClinico {
  classificacoes: ClassificacaoClinica[]
  cruzamentos: CruzamentoClinicoItem[]
  nota: string
}