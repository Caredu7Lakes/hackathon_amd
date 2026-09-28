FROM python:3.12-slim
WORKDIR /app

# Dependências de sistema para compilar cyvcf2 (htslib).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcurl4-openssl-dev zlib1g-dev libbz2-dev liblzma-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o modelo de embedding no build, embutindo-o na imagem.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]