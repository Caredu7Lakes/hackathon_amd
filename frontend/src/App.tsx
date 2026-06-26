import { useState } from 'react'
import { usePacientes, useLeitura } from './api/hooks'
import { ApiError } from './api/client'
import type { Confianca } from './api/types'
import './App.css'

const rotuloConfianca: Record<Confianca, string> = {
  alta: 'confiança alta',
  moderada: 'confiança moderada',
  baixa: 'confiança baixa',
}

export default function App() {
  const [pacienteId, setPacienteId] = useState<string | null>(null)

  const pacientes = usePacientes()
  const leitura = useLeitura(pacienteId)

  return (
    <div className="app">
      <header className="app-header">
        <h1>GenRisk</h1>
        <p className="subtitulo">
          Leitura cruzada de laudos genéticos — eixo cardiometabólico
        </p>
      </header>

      <section className="seletor">
        <label htmlFor="paciente">Paciente:</label>
        <select
          id="paciente"
          value={pacienteId ?? ''}
          onChange={(e) => setPacienteId(e.target.value || null)}
          disabled={pacientes.isLoading || pacientes.isError}
        >
          <option value="">— selecione —</option>
          {pacientes.data?.pacientes.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        {pacientes.isError && (
          <span className="erro-inline">Falha ao carregar a lista de pacientes.</span>
        )}
      </section>

      <main>
        {pacienteId === null && (
          <p className="vazio">Selecione um paciente para ver a leitura cruzada.</p>
        )}

        {pacienteId !== null && leitura.isLoading && (
          <p className="carregando">
            Gerando leitura cruzada… a primeira consulta pode levar alguns segundos.
          </p>
        )}

        {leitura.isError && (
          <p className="erro">
            {leitura.error instanceof ApiError && leitura.error.status === 404
              ? 'Paciente não encontrado.'
              : leitura.error instanceof ApiError && leitura.error.status === 502
                ? 'Não foi possível gerar uma leitura válida para este paciente.'
                : 'Falha ao gerar a leitura. Verifique se o backend está no ar.'}
          </p>
        )}

        {leitura.data && (
          <article className="leitura">
            <h2>Resumo</h2>
            <p>{leitura.data.resumo}</p>

            <h2>Cruzamentos</h2>
            <ul className="cruzamentos">
              {leitura.data.cruzamentos.map((c, i) => (
                <li key={i} className={`cruzamento ${c.confianca}`}>
                  <span className={`selo ${c.confianca}`}>
                    {rotuloConfianca[c.confianca]}
                  </span>
                  <p className="afirmacao">{c.afirmacao}</p>
                  <div className="fontes">
                    {c.fontes.map((f) => (
                      <span key={f} className="fonte-chip">{f}</span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>

            {leitura.data.evidencia_insuficiente.length > 0 && (
              <section className="evidencia-insuf">
                <h2>Evidência insuficiente</h2>
                <ul>
                  {leitura.data.evidencia_insuficiente.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </section>
            )}

            <p className="disclaimer">{leitura.data.disclaimer}</p>
          </article>
        )}
      </main>
    </div>
  )
}