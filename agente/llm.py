"""Cliente OpenRouter: chamadas de texto com saída estruturada (Pydantic) e chamadas brutas."""

from __future__ import annotations

import copy
import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agente.config import Config

T = TypeVar("T", bound=BaseModel)

# Palavras-chave de JSON Schema que alguns provedores rejeitam em structured outputs.
# A validação completa continua sendo feita pelo Pydantic depois da resposta.
_CHAVES_REMOVIDAS = {"minItems", "maxItems", "minLength", "maxLength", "pattern", "format", "default", "title"}


class ErroLLM(RuntimeError):
    def __init__(self, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.status = status


def _sanitizar_schema(no: Any) -> Any:
    if isinstance(no, dict):
        novo = {}
        for k, v in no.items():
            if k in ("properties", "$defs"):
                # Chaves aqui são nomes de campos/modelos, não palavras-chave do schema.
                novo[k] = {nome: _sanitizar_schema(sub) for nome, sub in v.items()}
            elif k not in _CHAVES_REMOVIDAS:
                novo[k] = _sanitizar_schema(v)
        if novo.get("type") == "object" and "properties" in novo:
            novo["additionalProperties"] = False
        return novo
    if isinstance(no, list):
        return [_sanitizar_schema(x) for x in no]
    return no


def extrair_json(texto: str) -> str:
    """Remove cercas de código e texto ao redor, devolvendo só o objeto JSON."""
    texto = texto.strip()
    cerca = re.search(r"```(?:json)?\s*(.*?)```", texto, re.DOTALL)
    if cerca:
        texto = cerca.group(1).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("Resposta não contém objeto JSON.")
    return texto[inicio : fim + 1]


def _texto_da_mensagem(msg: dict) -> str:
    conteudo = msg.get("content") or ""
    if isinstance(conteudo, list):
        return "".join(p.get("text", "") for p in conteudo if isinstance(p, dict))
    return conteudo


class ClienteOpenRouter:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._suporta_json_schema: dict[str, bool] = {}
        self._suporta_raciocinio: dict[str, bool] = {}
        self.uso_acumulado: dict[str, float] = {"prompt_tokens": 0, "completion_tokens": 0, "custo_usd": 0.0}

    # ------------------------------------------------------------------ baixo nível
    def post(self, payload: dict) -> dict:
        if not self.cfg.api_key:
            raise ErroLLM("OPENROUTER_API_KEY não configurada. Copie .env.example para .env e preencha a chave.")
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "HTTP-Referer": self.cfg.app_url,
            "X-Title": self.cfg.app_nome,
        }
        payload = {**payload, "usage": {"include": True}}
        try:
            with httpx.Client(timeout=self.cfg.timeout_s) as c:
                r = c.post(f"{self.cfg.base_url}/chat/completions", json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise ErroLLM(f"Falha de rede ao chamar OpenRouter: {e}") from e
        if r.status_code >= 400:
            raise ErroLLM(f"OpenRouter {r.status_code}: {r.text[:800]}", status=r.status_code)
        data = r.json()
        if data.get("error"):
            raise ErroLLM(f"OpenRouter erro: {data['error']}")
        if not data.get("choices"):
            raise ErroLLM(f"Resposta sem 'choices': {str(data)[:500]}")
        uso = data.get("usage") or {}
        self.uso_acumulado["prompt_tokens"] += uso.get("prompt_tokens", 0) or 0
        self.uso_acumulado["completion_tokens"] += uso.get("completion_tokens", 0) or 0
        self.uso_acumulado["custo_usd"] += float(uso.get("cost", 0) or 0)
        return data

    # ------------------------------------------------------------------ saída estruturada
    def gerar_estruturado(
        self,
        sistema: str,
        usuario: str,
        modelo_saida: type[T],
        *,
        modelo: str | None = None,
        tentativas: int = 2,
    ) -> T:
        modelo = modelo or self.cfg.modelo_texto
        schema = modelo_saida.model_json_schema()

        def montar_mensagens() -> list[dict]:
            # Com response_format aceito, o schema vai só nele (economiza ~5 mil tokens de entrada por chamada).
            # Sem suporte, vai no texto do pedido.
            if self._suporta_json_schema.get(modelo, True):
                pedido = f"{usuario}\n\nResponda somente com o objeto JSON no formato solicitado."
            else:
                pedido = (
                    f"{usuario}\n\n---\nResponda SOMENTE com um objeto JSON válido que siga exatamente este JSON Schema "
                    f"(sem texto antes ou depois):\n{json.dumps(schema, ensure_ascii=False)}"
                )
            return [
                # cache_control: o contexto fixo (igual em todos os modos) é reaproveitado por ~5 min (Anthropic, Gemini).
                {"role": "system", "content": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}]},
                {"role": "user", "content": pedido},
            ]

        mensagens = montar_mensagens()
        ultimo_erro = ""
        for _ in range(tentativas + 1):
            payload: dict[str, Any] = {"model": modelo, "messages": mensagens, "max_tokens": self.cfg.max_tokens}
            if self.cfg.esforco_raciocinio and self._suporta_raciocinio.get(modelo, True):
                payload["reasoning"] = {"effort": self.cfg.esforco_raciocinio}
            if self._suporta_json_schema.get(modelo, True):
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": modelo_saida.__name__,
                        "strict": False,
                        "schema": _sanitizar_schema(copy.deepcopy(schema)),
                    },
                }
            try:
                data = self.post(payload)
            except ErroLLM as e:
                if e.status == 400 and "reasoning" in payload and "reason" in str(e).lower():
                    # Modelo não aceita ajuste de raciocínio: repete sem o parâmetro.
                    self._suporta_raciocinio[modelo] = False
                    continue
                if "response_format" in payload and e.status == 400:
                    # Provedor recusou o response_format: repete com o schema no texto do pedido.
                    self._suporta_json_schema[modelo] = False
                    mensagens = montar_mensagens()
                    continue
                raise

            texto = _texto_da_mensagem(data["choices"][0]["message"])
            try:
                return modelo_saida.model_validate_json(extrair_json(texto))
            except (ValidationError, ValueError) as e:
                ultimo_erro = str(e)[:2000]
                mensagens = mensagens[:2] + [
                    {"role": "assistant", "content": texto},
                    {
                        "role": "user",
                        "content": f"A resposta não passou na validação:\n{ultimo_erro}\n"
                        "Corrija e responda novamente apenas com o JSON completo.",
                    },
                ]
        raise ErroLLM(f"O modelo não produziu JSON válido após {tentativas + 1} tentativas. Último erro: {ultimo_erro}")
