import type { Leitura, ListaPacientes } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// Erro de API com status, para a UI distinguir 404 de 502 de falha de rede.
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

// Wrapper unico sobre fetch: centraliza checagem de status e parse.
// signal: permite cancelamento (defesa contra race condition no seletor).
async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal })
  if (!res.ok) {
    let detalhe = `Erro ${res.status}`
    try {
      const corpo = await res.json()
      if (corpo?.detail) detalhe = corpo.detail
    } catch {
      // resposta sem corpo JSON — mantem a mensagem generica
    }
    throw new ApiError(res.status, detalhe)
  }
  return res.json() as Promise<T>
}

export function fetchPacientes(signal?: AbortSignal): Promise<ListaPacientes> {
  return getJson<ListaPacientes>(`${API_BASE}/api/v1/pacientes`, signal)
}

export function fetchLeitura(
  pacienteId: string,
  signal?: AbortSignal,
): Promise<Leitura> {
  return getJson<Leitura>(
    `${API_BASE}/api/v1/leitura/${encodeURIComponent(pacienteId)}`,
    signal,
  )
}

