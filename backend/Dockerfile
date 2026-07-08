FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o modelo de embedding no build, embutindo-o na imagem.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

# Torna o entrypoint executável e o define como ponto de entrada.
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]