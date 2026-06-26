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
}

export interface ListaPacientes {
  pacientes: string[]
}