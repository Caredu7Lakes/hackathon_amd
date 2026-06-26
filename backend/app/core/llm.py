"""core/llm.py — camada de abstracao de LLM.

- AnthropicClient: API Anthropic direta (caminho garantido da demo).
- BedrockClient: AWS Bedrock + Claude (quando a cota AWS liberar).
- get_llm_client(): fabrica que escolhe pela config (LLM_PROVIDER).
Testes mockam esta camada — nunca chamam a API real.
"""

import json
from typing import Protocol

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LLMClient(Protocol):
    def gerar_json(self, system: str, user: str) -> dict: ...


class AnthropicClient:
    """API Anthropic direta (console.anthropic.com). Auth por chave de API."""

    def __init__(self) -> None:
        import anthropic

        settings = get_settings()
        self._model = settings.LLM_MODEL
        self._client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)

    def gerar_json(self, system: str, user: str) -> dict:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        texto = msg.content[0].text
        return _parse_json_estrito(texto)


class BedrockClient:
    """AWS Bedrock + Claude. Auth pelo perfil AWS (boto3)."""

    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        self._model_id = settings.BEDROCK_MODEL_ID
        self._client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)

    def gerar_json(self, system: str, user: str) -> dict:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        resp = self._client.invoke_model(modelId=self._model_id, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        texto = payload["content"][0]["text"]
        return _parse_json_estrito(texto)


def _parse_json_estrito(texto: str) -> dict:
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM nao retornou JSON valido: {e}") from e


def get_llm_client() -> LLMClient:
    settings = get_settings()
    provedor = settings.LLM_PROVIDER
    if provedor == "anthropic":
        return AnthropicClient()
    if provedor == "bedrock":
        return BedrockClient()
    raise ValueError(f"Provedor de LLM desconhecido: {provedor}")