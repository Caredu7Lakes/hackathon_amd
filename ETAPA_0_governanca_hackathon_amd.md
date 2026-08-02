# ETAPA 0 — Governança e Fundação · Projeto `hackathon_amd`

**Status:** baseline aprovado
**Prazo final do hackathon:** 08/07 (prazo máximo)
**Responsável:** Carlos Eduardo (solo dev/QA)
**Natureza do documento:** este é o artefato fundacional. Toda decisão de escopo aqui registrada foi explicitamente aprovada e não deve ser revertida sem novo registro. Mudança de escopo é tratada como evento de governança, não como ajuste silencioso.

---

## 1. O que o projeto é (e o que não é)

### 1.1 Posicionamento

`hackathon_amd` é um **protótipo educacional/demonstrativo** que faz **leitura cruzada inteligente** de laudos genéticos, no eixo **cardiometabólico**, cruzando três painéis: **Doenças × Farma × Fit**.

O modelo lê o laudo genético de um paciente (fictício), identifica no eixo cardiometabólico os riscos de doença relevantes, o perfil farmacogenético correspondente e os marcadores de fitness conectados, e uma LLM produz uma leitura que cruza os três painéis — sempre ancorada no que está literalmente nos laudos e na literatura recuperada (grounding estrito).

### 1.2 Declaração explícita de NÃO-escopo

Para evitar drift, fica registrado o que o MVP **não** faz:

- **Não é ferramenta de apoio à decisão clínica.** Não se apresenta como tal em nenhum ponto da demo, do pitch ou da saída do modelo.
- **Não recalcula risco.** Não há motor de ajuste, não há tabela de regras `apontamento clínico → ajuste de risco`. Decisão tomada e registrada.
- **Não consome exames clínicos** (hemograma, urina, microbiota). Ficaram fora do MVP, pois sem mecanismo de ajuste não teriam função. Reservados para expansão pós-08/07.
- **Não usa dados reais de pacientes.** Todos os dados são de um paciente fictício (laudos Genera) e, opcionalmente, sintéticos derivados.
- **Não calcula PRS do zero.** Os pesos de efeito já vêm tabelados nos laudos; o MVP não reimplementa GWAS-to-weight.

---

## 2. Decisões de arquitetura travadas

| # | Decisão | Estado |
|---|---------|--------|
| A | Arquitetura híbrida: a LLM **não** produz números. Risco vem da leitura dos laudos. | Travado |
| B | LLM via **API** (HTTP). RAG, backend e estruturação 100% locais. Sem cloud, sem GPU. | Travado |
| C | Multi-turno apenas de **exploração**, sobre resultado fixo. Stateless calcula uma vez; a conversa só lê. Entra como extra se sobrar tempo. | Travado |
| D | AMD/ROCm é elemento de **pitch/narrativa**, não de execução. A demo não afirma rodar em AMD se não estiver. | Travado |
| E | Eixo único: **cardiometabólico**. Não cobrir as 21 doenças. | Travado |
| F | Sem motor de ajuste. MVP é **leitura cruzada com grounding**. | Travado |

### 2.1 Componentes do backend

- **`leitura_service`** — determinístico. Lê e estrutura os laudos, extrai os riscos e marcadores do eixo cardiometabólico. Testável isoladamente, sem LLM. Tem testes unitários reais (entrada → saída esperada).
- **`explicacao_service`** — RAG + LLM. Recebe os dados estruturados + trechos recuperados (laudos e literatura) e devolve a leitura cruzada em linguagem natural, com fontes. Testável por comportamento.

A separação é deliberada: o que é determinístico tem cobertura de teste de verdade; o que é probabilístico (LLM) é isolado e testado por comportamento.

---

## 3. Os dados (paciente fictício — laudos Genera)

Sete painéis disponíveis, todos do mesmo paciente fictício. Cada laudo já contém o campo **Efeito** (peso) por SNP e, nas doenças, o risco percentual já calculado.

| Painel | Conteúdo | Uso no MVP |
|--------|----------|------------|
| Doenças (escala de risco) | 21 doenças, ~10 SNPs cada + risco % + decomposição genético/ambiental | **Núcleo** (recorte cardiometabólico) |
| Farma | ~16 fármacos, genótipo + interpretação de resposta | **Núcleo** |
| Fit | desempenho físico, IMC/obesidade, recuperação cardíaca | **Terceiro eixo** (conectores) |
| Nutri | vitaminas, dietas | Expansão |
| Skin | pele | Expansão |
| Aging | envelhecimento | Expansão |
| You | traços comportamentais | Expansão |

### 3.1 Recorte cardiometabólico do MVP

**Lado Doenças:** diabetes tipo 2 (risco 50,17%), doença arterial coronariana.

**Lado Farma:** metformina e sulfonilureias (maior resposta), atorvastatina (menor resposta, rs7412), estatinas/distúrbio muscular (rs4693075), sinvastatina (rs4149056).

**Lado Fit (conectores):**
- **FTO (rs9939609, rs1421085, rs1861868)** → obesidade/IMC → diabetes. **Conector forte.**
- **CHRM2 (rs324640)** → recuperação cardíaca lenta → risco cardiovascular. **Conector brando** (a ponte genótipo→fenótipo é mais frouxa; apresentar com menor confiança).

---

## 4. Corpus de RAG (12 fontes científicas + 21 laudos)

Cada bloco traz a força de evidência, que governa o quanto a LLM pode afirmar.

### Bloco 1 — FTO/obesidade → diabetes · Evidência FORTE
- Meta-análise escandinava (n=41.504): rs9939609 ~ DT2 (OR 1,13), mantém-se após ajuste para IMC.
- Meta-análise indiana (n=28.394).
- Estudo brasileiro de obesidade severa (fundamentação nacional).
- Interação FTO × dieta mediterrânea (cruza com Nutri, se expandir).

### Bloco 2 — Recuperação cardíaca → risco CV · Evidência FORTE no fenótipo, FRACA no genótipo
- NEJM 1999 (recuperação da FC como preditor de mortalidade).
- Cleveland Clinic (preditor independente da gravidade angiográfica).
- **Ressalva:** o elo CHRM2 (genótipo) → fenótipo é o mais fraco do corpus. Conector brando.

### Bloco 3 — Farmacogenômica · Evidência ALTA
- **CPIC guideline SLCO1B1/sinvastatina** — diretriz clínica formal, evidência alta para miopatia. Fonte mais forte do corpus.
- GWAS Nature Genetics metformina/ATM (rs11212617, OR 1,35) — **com ressalva**: não replicado em todos os estudos (DPP não confirmou). Apresentar como associação real, porém menos consolidada que SLCO1B1.
- Meta-análise de replicação ATM (5 coortes).

### Bloco 4 — Contexto brasileiro · Para enquadramento (não cruzamento individual)
- SciELO — farmacogenômica e diversidade da população brasileira.
- CV-Genes (PROADI-SUS) — esforço nacional para PRS brasileiro.
- PRS hipercolesterolemia ELSA-Brasil/InCor (eixo cardiovascular).

### 4.1 Limitação populacional — declaração obrigatória na saída

Os marcadores da Genera derivam majoritariamente de população europeia. A população brasileira é altamente miscigenada, o que reduz a transferibilidade. **A saída do modelo deve declarar essa limitação explicitamente.** Transformar a fragilidade em sinal de rigor é a postura adotada — esconder seria pior numa banca.

---

## 5. Defesas e regras de grounding

- A LLM só afirma o que está nos laudos recuperados e na literatura recuperada. Sem cobertura → "evidência insuficiente para este marcador".
- Saída forçada em JSON, validada contra schema antes de chegar à tela.
- Campo de fontes obrigatório (qual laudo / qual artigo sustenta cada afirmação).
- Sanitização do texto livre antes de compor o prompt.
- Disclaimer de "não é aconselhamento médico" presente em 100% das saídas.
- Ao usar literatura externa, a LLM só pode afirmar a conexão nos termos que o artigo sustenta — não extrapolar.

---

## 6. Sprints (23/06 → 08/07)

Folga proposital nas Sprints 2 e 3 (maior risco técnico: RAG e backend).

### Sprint 0 — Fundação e governança (23–24/06)
- Este documento (baseline aprovado).
- Estrutura do projeto (FastAPI async, espelhando moshe1.8).
- `.env.example` sem segredos; `.env` no `.gitignore` desde o commit zero.
- Schema Pydantic do `PacienteLaudo` (estrutura dos laudos).
- Constante central de disclaimer.
- Confirmar PDFs acessíveis.

### Sprint 1 — Estruturação dos laudos (25–26/06)
- Ingestão dos 7 PDFs → JSON estruturado por painel.
- Recorte cardiometabólico extraído e validado contra o schema.
- (Opcional) gerar pacientes sintéticos para variar a demo.

### Sprint 2 — RAG (27–29/06)
- Ingestão e chunking dos laudos + 12 fontes científicas.
- Embeddings open-source + banco vetorial local (FAISS/Chroma).
- **Teste de aceite obrigatório:** busca por nome de variante retorna o trecho certo, sem LLM no circuito. Não avança enquanto não estiver verde.

### Sprint 3 — Backend de leitura cruzada (30/06–03/07)
- `leitura_service` (determinístico) + testes unitários.
- `explicacao_service` (RAG + LLM) com grounding estrito.
- Rota `/api/v1/leitura`.
- Saída JSON validada, com fontes e disclaimer.
- Sanitização de entrada; erro controlado para JSON quebrado.

### Sprint 4 — Frontend de demo (04–05/07)
- Interface mínima: seleciona paciente → mostra leitura cruzada (Doenças × Farma × Fit), fontes, disclaimer e a declaração de limitação populacional.
- (Se sobrar tempo) multi-turno de exploração sobre resultado fixo.

### Sprint 5 — QA adversarial + vídeo (06–08/07)
- Prompt injection no campo livre.
- Token overflow.
- Paciente/marcador sem cobertura → resposta de "evidência insuficiente".
- Verificar: 100% das saídas com fonte, disclaimer e limitação populacional.
- Gravar demo com margem de um dia.

---

## 7. Lições de ambiente herdadas do moshe1.8 (aplicáveis aqui)

- Salvar no VS Code antes de qualquer comando que leia do disco.
- Nunca colar saída de comando de volta no terminal PowerShell.
- PowerShell 5.1 `>` gera UTF-16 (quebra CI Linux) — usar `Out-File -Encoding utf8`.
- `2>/dev/null` é sintaxe Linux; quebra no PowerShell.
- Arquivos com nome em português podem divergir dos caminhos de import em inglês — atenção.

---

## 8. Item de governança pendente herdado

Rotação das credenciais de API expostas durante validação de config do Docker Compose no moshe1.8 — **alta prioridade, não fechada.** Registrado aqui para não se perder na troca de contexto entre projetos.
