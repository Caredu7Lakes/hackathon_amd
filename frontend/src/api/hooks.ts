import { useQuery } from '@tanstack/react-query'
import { fetchLeitura, fetchPacientes } from './client'

// Lista de pacientes para o seletor. Busca uma vez e cacheia.
export function usePacientes() {
  return useQuery({
    queryKey: ['pacientes'],
    queryFn: ({ signal }) => fetchPacientes(signal),
  })
}

// Leitura cruzada de um paciente. So dispara quando ha um id selecionado
// (enabled), e a queryKey inclui o id — trocar de paciente troca a chave,
// e o TanStack Query trata o cancelamento da busca anterior via signal.
// E esta a defesa contra a race condition do seletor: resposta antiga de
// outro paciente nunca sobrescreve a atual.
export function useLeitura(pacienteId: string | null) {
  return useQuery({
    queryKey: ['leitura', pacienteId],
    queryFn: ({ signal }) => fetchLeitura(pacienteId!, signal),
    enabled: pacienteId !== null,
  })
}