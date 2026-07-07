import { useState } from 'react'
import { usePacientes, useLeitura } from './api/hooks'
import { ApiError } from './api/client'
import type { Confianca, Modificador } from './api/types'
import './App.css'

const rotuloConfianca: Record<Confianca, string> = {
  alta: 'high confidence',
  moderada: 'moderate confidence',
  baixa: 'low confidence',
}

type Sintese = { desfecho: string; rotulo: string; classe: string; detalhe: string }

function sintetizar(
  modsPorDesfecho: Record<string, Modificador[]>,
  riscoBase: Record<string, number>,
): Sintese[] {
  if (!modsPorDesfecho) return []
  return Object.entries(modsPorDesfecho).map(([desfecho, mods]) => {
    const lista = Array.isArray(mods) ? mods : []
    const baseKey = Object.keys(riscoBase || {}).find((k) =>
      desfecho.toLowerCase().includes(k.toLowerCase()),
    )
    const valorBase = baseKey ? riscoBase[baseKey] : undefined
    const noBase = typeof valorBase === 'number'
    const risco = lista.filter((m) => m.direcao === 'risco')
    const protecao = lista.filter((m) => m.direcao === 'protecao')
    const maxHr = lista.length ? Math.max(...lista.map((m) => m.hazard_ratio)) : 0

    let rotulo: string
    let classe: string
    if (!noBase) {
      rotulo = 'new axis revealed'
      classe = 'novo'
    } else if (risco.length > 0 && protecao.length > 0) {
      rotulo = 'divergent forces'
      classe = 'divergente'
    } else if (protecao.length > 0) {
      rotulo = 'protective factor'
      classe = 'protetor'
    } else if (risco.length >= 2 && maxHr >= 1.5) {
      rotulo = 'strongly reinforced risk'
      classe = 'forte'
    } else {
      rotulo = 'reinforced risk'
      classe = 'moderado'
    }

    const detalhe = noBase
      ? `base risk ${valorBase.toFixed(2)}% · ${lista.length} modifier(s) · max HR ${maxHr.toFixed(2)}`
      : `not present in the genetic reading alone · max HR ${maxHr.toFixed(2)}`
    return { desfecho, rotulo, classe, detalhe }
  })
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
          Cross-reading of genetic reports — cardiometabolic axis
        </p>
      </header>

      <section className="seletor">
        <label htmlFor="paciente">Patient:</label>
        <select
          id="paciente"
          value={pacienteId ?? ''}
          onChange={(e) => setPacienteId(e.target.value || null)}
          disabled={pacientes.isLoading || pacientes.isError}
        >
          <option value="">— select —</option>
          {pacientes.data?.pacientes.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        {pacientes.isError && (
          <span className="erro-inline">Failed to load the patient list.</span>
        )}
      </section>

      <main>
        {pacienteId === null && (
          <p className="vazio">Select a patient to see the cross-reading.</p>
        )}
        {pacienteId !== null && leitura.isLoading && (
          <p className="carregando">
            Generating cross-reading… the first request may take a few seconds.
          </p>
        )}

        {leitura.isError && (
          <p className="erro">
            {leitura.error instanceof ApiError && leitura.error.status === 404
              ? 'Patient not found.'
              : leitura.error instanceof ApiError && leitura.error.status === 502
                ? 'Could not generate a valid reading for this patient.'
                : 'Failed to generate the reading. Check whether the backend is running.'}
          </p>
        )}

        {leitura.data && (
          <article className="leitura">
            <h2>Summary</h2>
            <p>{leitura.data.resumo}</p>

            <h2>Cross-links</h2>
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
                <h2>Insufficient evidence</h2>
                <ul>
                  {leitura.data.evidencia_insuficiente.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </section>
            )}

            {leitura.data.integracao_omica.camadas_presentes.length > 0 && (
              <section className="omica">
                <h2 className="omica-titulo">Multi-omic re-reading</h2>
                <p className="omica-sub">
                  Additional layers reconfigure the patient's reading. Each modifier
                  carries its published weight, confidence interval, source, and outcome —
                  the base genetic risk stays intact, read alongside.
                </p>

                <div className="camadas-chips">
                  {leitura.data.integracao_omica.camadas_presentes.map((c) => (
                    <span key={c} className="camada-chip">{c}</span>
                  ))}
                </div>

                <div className="sintese-painel">
                  {sintetizar(
                    leitura.data.integracao_omica.modificadores_por_desfecho,
                    leitura.data.integracao_omica.risco_base_genetico,
                  ).map((s) => (
                    <div key={s.desfecho} className={`sintese-item ${s.classe}`}>
                      <span className="sintese-seta">
                        {s.classe === 'forte'
                          ? '↑↑'
                          : s.classe === 'moderado'
                            ? '↑'
                            : s.classe === 'protetor'
                              ? '↓'
                              : s.classe === 'divergente'
                                ? '⇅'
                                : '✦'}
                      </span>
                      <div className="sintese-texto">
                        <div className="sintese-desfecho">{s.desfecho}</div>
                        <div className="sintese-rotulo">{s.rotulo}</div>
                        <div className="sintese-detalhe">{s.detalhe}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {Object.entries(leitura.data.integracao_omica.modificadores_por_desfecho).map(
                  ([desfecho, mods]) => (
                    <div key={desfecho} className="desfecho-bloco">
                      <p className="desfecho-nome">{desfecho}</p>
                      {(mods as Modificador[]).map((m, i) => (
                        <div key={i} className="modificador">
                          <span className={`mod-hr ${m.direcao === 'protecao' ? 'protecao' : ''}`}>
                            HR {m.hazard_ratio.toFixed(2)}
                          </span>
                          <div className="mod-info">
                            <div className="mod-marcador">
                              {m.marcador} <span className="mod-valor">({m.valor})</span>
                            </div>
                            <div className="mod-meta">
                              <span className="mod-ic">
                                CI95 {m.ic_95[0].toFixed(2)}–{m.ic_95[1].toFixed(2)}
                              </span>
                              <span className="fonte-chip">{m.fonte}</span>
                              <span className="mod-camada">{m.camada}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ),
                )}
              </section>
            )}

            <p className="disclaimer">{leitura.data.disclaimer}</p>
          </article>
        )}
      </main>
    </div>
  )
}