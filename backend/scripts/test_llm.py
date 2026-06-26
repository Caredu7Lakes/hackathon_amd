"""Teste de integracao real com AWS Bedrock. Gasta um pouco de credito."""

import sys
sys.path.insert(0, "/app")

from app.core.llm import get_llm_client

cliente = get_llm_client()
resposta = cliente.gerar_json(
    "Responda apenas com JSON valido, sem texto adicional.",
    'Retorne exatamente este objeto: {"ok": true}',
)
print("RESPOSTA:", resposta)