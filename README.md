\# GenRisk — Multi-Omic Cardiometabolic Risk Reader

\> Educational and demonstrative prototype. Not a medical device. Does not provide diagnosis or treatment recommendations.

GenRisk performs \*\*cross-reading of genetic reports\*\* on the cardiometabolic axis and layers additional \*\*omic and clinical evidence\*\* on top — gut microbiome, DNA methylation, and structured clinical history. Each layer is stratified by outcome, with every weight traceable to a published source (hazard ratio, confidence interval, outcome, and direction). The base genetic risk is never recalculated: layers are read alongside it, never fused into a single misleading number.

Built for the \*\*AMD Developer Hackathon: ACT II\*\* (Unicorn Track).

\#\# Architecture

\- \*\*Backend\*\* — FastAPI \+ RAG (FAISS, local sentence-transformers embeddings) \+ Anthropic API for the cross-reading. Deterministic integration engine (no LLM) for the multi-omic layering.  
\- \*\*Frontend\*\* — React 19 \+ Vite \+ TypeScript. Clinical UI with a directional synthesis panel.  
\- \*\*Layers\*\* — genetic PRS (base), microbiome, methylation, clinical anamnesis.

\#\# Honesty boundary

Every numeric weight traces to a published study indexed in the RAG corpus. Nothing is invented by the model. Outcomes are never mixed: microbiome-for-diabetes and methylation-for-macrovascular-event stay in separate buckets. When a factor is protective (e.g. light-moderate alcohol), it is shown as protective — the panel labels divergent forces honestly rather than forcing everything toward risk.

\#\# Prerequisites

\- Docker and Docker Compose  
\- Node.js 18+ (for the frontend)  
\- An Anthropic API key

\#\# Setup

\#\#\# 1\. Backend (containerized)

\`\`\`bash  
\# From the repository root  
cp backend/.env.example backend/.env  
\# Edit backend/.env and set LLM\_API\_KEY=\<your Anthropic API key\>

cd infra  
docker compose up \-d \--build  
\`\`\`

The backend runs at \`http://localhost:8000\`.

\> Note: \`docker compose restart\` does not reload \`.env\`. After changing environment variables, use \`docker compose up \-d \--force-recreate\`.

\#\#\# 2\. Build the RAG index

\`\`\`bash  
docker exec hackathon-amd-backend python \-m app.rag.ingest  
\`\`\`

This generates embeddings for the scientific corpus and patient reports, building the FAISS index.

\#\#\# 3\. Frontend

\`\`\`bash  
cd frontend  
npm install  
npm run dev  
\`\`\`

The UI runs at \`http://localhost:5173\` and proxies API calls to the backend.

\#\# Running the tests

\`\`\`bash  
docker exec hackathon-amd-backend python \-m pytest \-q  
\`\`\`

The suite covers the leitura service, RAG, the integration engine, adversarial robustness, and a 200-patient randomized stress test with invariant checks.

\#\# AMD execution (ROCm-ready)

The embedding pipeline detects the best available device automatically: AMD GPU (ROCm) → NVIDIA GPU (CUDA) → CPU, with transparent CPU fallback. To benchmark embedding performance on the current device:

\`\`\`bash  
docker exec hackathon-amd-backend python \-m scripts.benchmark\_embedding  
\`\`\`

On AMD Developer Cloud (ROCm), the same command detects the AMD GPU and produces a comparable measurement for a real before/after benchmark.

\#\# Environment variables

| Variable | Description |  
|---|---|  
| \`LLM\_API\_KEY\` | Anthropic API key (required) |  
| \`LLM\_MODEL\` | Model string (default: claude-sonnet-4-6) |  
| \`LAUDOS\_DIR\` | Patient reports directory |  
| \`CORPUS\_DIR\` | Scientific corpus directory |  
| \`FAISS\_INDEX\_PATH\` | FAISS index path |

\#\# Disclaimer

This is an educational prototype. The genetic associations used derive mostly from European-ancestry studies; transferability to the highly admixed Brazilian population is a recognized limitation. Always consult a qualified healthcare professional.  
