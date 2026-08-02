import { useState } from 'react'
import { usePacientes, useLeitura } from './api/hooks'
import { ApiError } from './api/client'
import type { Confianca, Modificador } from './api/types'
import './App.css'

const rotuloConfianca: Record<Confianca, string> = {
  alta: 'confiança alta',
  moderada: 'confiança moderada',
  baixa: 'confiança baixa',
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
      rotulo = 'novo eixo revelado'
      classe = 'novo'
    } else if (risco.length > 0 && protecao.length > 0) {
      rotulo = 'forças divergentes'
      classe = 'divergente'
    } else if (protecao.length > 0) {
      rotulo = 'fator protetor'
      classe = 'protetor'
    } else if (risco.length >= 2 && maxHr >= 1.5) {
      rotulo = 'risco fortemente reforçado'
      classe = 'forte'
    } else {
      rotulo = 'risco reforçado'
      classe = 'moderado'
    }

    const detalhe = noBase
      ? `risco base ${valorBase.toFixed(2)}% · ${lista.length} modificador(es) · HR máx ${maxHr.toFixed(2)}`
      : `não presente apenas na leitura genética · HR máx ${maxHr.toFixed(2)}`
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
            Gerando leitura cruzada… a primeira requisição pode levar alguns segundos.
          </p>
        )}

        {leitura.isError && (
          <p className="erro">
            {leitura.error instanceof ApiError && leitura.error.status === 404
              ? 'Paciente não encontrado.'
              : leitura.error instanceof ApiError && leitura.error.status === 502
                ? 'Não foi possível gerar uma leitura válida para este paciente.'
                : 'Falha ao gerar a leitura. Verifique se o backend está rodando.'}
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

            {leitura.data.integracao_omica.camadas_presentes.length > 0 && (
              <section className="omica">
                <h2 className="omica-titulo">Releitura multiômica</h2>
                <p className="omica-sub">
                  Camadas adicionais reconfiguram a leitura do paciente. Cada modificador
                  carrega seu peso publicado, intervalo de confiança, fonte e desfecho —
                  o risco genético base permanece intacto, lido em paralelo.
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
                                IC95 {m.ic_95[0].toFixed(2)}–{m.ic_95[1].toFixed(2)}
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