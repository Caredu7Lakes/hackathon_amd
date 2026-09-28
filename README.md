# GenRisk — Multi-Omic Cardiometabolic Risk Reader

> Educational and demonstrative prototype. Not a medical device. Does not provide diagnosis or treatment recommendations.

GenRisk performs **cross-reading of genetic reports** on the cardiometabolic axis and layers additional **omic and clinical evidence** on top — gut microbiome, DNA methylation, and structured clinical history. Each layer is stratified by outcome, with every weight traceable to a published source (hazard ratio, confidence interval, outcome, and direction). The base genetic risk is never recalculated: layers are read alongside it, never fused into a single misleading number.

It ingests real interoperability formats — **VCF** for genetic variants and **FHIR** (LOINC/SNOMED-coded) for clinical findings — and performs a **deterministic anamnesis × exam cross-check** that flags concordances and discrepancies between what the patient reports and what the labs show.

Built for the **AMD Developer Hackathon: ACT II** (Unicorn Track).

## Architecture

- **Backend** — FastAPI + RAG (FAISS, local sentence-transformers embeddings) + Anthropic API for the cross-reading. Deterministic engines (no LLM) for the multi-omic layering and the clinical cross-check.
- **Frontend** — React 19 + Vite + TypeScript. Clinical UI with a directional synthesis panel and a concordance/discrepancy map.
- **Layers** — genetic PRS (base), microbiome, methylation, structured clinical anamnesis.
- **Interoperability (ports-and-adapters)** — VCF ingestion via `cyvcf2` (only clinically-mapped variants are extracted, with provenance); FHIR-lite adapter parsing `Observation` (LOINC), `Condition` (SNOMED CT), and `DiagnosticReport`.

## Structured anamnesis & clinical cross-check

Clinical history is captured as a **33-item structured anamnesis** (7 classic semiology blocks, cardiometabolic-focused), replacing free text so it can be parsed and cross-referenced by rule. Two deterministic operations, no LLM:

- **Classification by cutoff** — raw measurements are labeled by published diagnostic thresholds, keyed by **LOINC** code (immune to lab-to-lab naming variation). Example: fasting glucose (LOINC 1558-6) ≥100 mg/dL → pre-diabetes (ADA cutoff). This is classification, not weighting — a measurement never becomes a hazard ratio.
- **Anamnesis × exam cross-check** — compares what the anamnesis declares against classified findings, producing a **concordance / discrepancy map**. A discrepancy (e.g. patient denies diabetes but lab shows pre-diabetes) is a review flag, never a diagnosis.

## Honesty boundary

Every numeric weight traces to a published study indexed in the RAG corpus. Nothing is invented by the model. Outcomes are never mixed: microbiome-for-diabetes and methylation-for-macrovascular-event stay in separate buckets. When a factor is protective (e.g. light-moderate alcohol), it is shown as protective — the panel labels divergent forces honestly rather than forcing everything toward risk. Clinical discrepancy flags are review alerts, not conclusions.

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for the frontend)
- An Anthropic API key

## Setup

### 1. Backend (containerized)

```bash
# From the repository root
cp backend/.env.example backend/.env
# Edit backend/.env and set LLM_API_KEY=<your Anthropic API key>

cd infra
docker compose up -d --build
```

The backend runs at `http://localhost:8000`.

> Note: `docker compose restart` does not reload `.env`. After changing environment variables, use `docker compose up -d --force-recreate`.

### 2. Build the RAG index

```bash
docker exec hackathon-amd-backend python -m app.rag.ingest
```

This generates embeddings for the scientific corpus and patient reports, building the FAISS index.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:5173` and proxies API calls to the backend.

## Running the tests

```bash
docker exec hackathon-amd-backend python -m pytest -q
```

The suite (35 tests) covers the leitura service, RAG, the multi-omic integration engine, the deterministic clinical cross-check (LOINC classification, concordance/discrepancy), adversarial robustness, and a 200-patient randomized stress test with invariant checks.

## AMD execution (ROCm-ready)

The embedding pipeline detects the best available device automatically: AMD GPU (ROCm) → NVIDIA GPU (CUDA) → CPU, with transparent CPU fallback. To benchmark embedding performance on the current device:

```bash
docker exec hackathon-amd-backend python -m scripts.benchmark_embedding
```

On AMD Developer Cloud (ROCm), the same command detects the AMD GPU and produces a comparable measurement for a real before/after benchmark.

## Data layout

| Directory | Content |
|---|---|
| `data/laudos` | Patient genetic reports (JSON) |
| `data/exames` | Multi-omic exams (microbiome, methylation) |
| `data/anamnese` | Structured 33-item anamnesis per patient |
| `data/fhir` | FHIR bundles (LOINC-coded clinical findings) |
| `data/corpus` | Scientific corpus for the RAG index |

## Environment variables

| Variable | Description |
|---|---|
| `LLM_API_KEY` | Anthropic API key (required) |
| `LLM_MODEL` | Model string (default: claude-sonnet-4-6) |
| `LAUDOS_DIR` | Patient reports directory |
| `CORPUS_DIR` | Scientific corpus directory |
| `EXAMES_DIR` | Multi-omic exams directory |
| `ANAMNESE_DIR` | Structured anamnesis directory |
| `FHIR_DIR` | FHIR bundles directory |
| `FAISS_INDEX_PATH` | FAISS index path |

## Disclaimer

This is an educational prototype. The genetic associations used derive mostly from European-ancestry studies; transferability to the highly admixed Brazilian population is a recognized limitation. Always consult a qualified healthcare professional.