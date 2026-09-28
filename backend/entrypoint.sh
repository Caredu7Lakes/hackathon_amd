#!/bin/sh
# Entrypoint: garante que o índice FAISS existe antes de servir.
# Se o índice não existir (primeiro boot, volume vazio, clone novo),
# constrói uma vez. Idempotente: se já existe, não reconstrói.
set -e

INDEX_FILE="data/faiss_index/index.faiss"

if [ ! -f "$INDEX_FILE" ]; then
  echo "[entrypoint] Indice FAISS nao encontrado. Construindo..."
  python -m app.rag.ingest
  echo "[entrypoint] Indice construido."
else
  echo "[entrypoint] Indice FAISS encontrado. Pulando ingest."
fi

echo "[entrypoint] Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"