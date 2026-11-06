"""Configuração via variáveis de ambiente (arquivo .env na raiz do projeto)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


@dataclass(frozen=True)
class Config:
    api_key: str | None
    base_url: str
    modelo_texto: str
    modelo_imagem: str
    app_url: str
    app_nome: str
    timeout_s: float
    max_tokens: int
    dir_contexto: Path
    dir_dados: Path
    dir_saida: Path


def carregar_config() -> Config:
    def caminho(var: str, padrao: str) -> Path:
        p = Path(os.getenv(var, padrao))
        return p if p.is_absolute() else RAIZ / p

    return Config(
        api_key=os.getenv("OPENROUTER_API_KEY") or None,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
        # Texto: qualquer modelo do OpenRouter com suporte a structured outputs.
        modelo_texto=os.getenv("MODELO_TEXTO", "anthropic/claude-sonnet-5.5"),
        # Nano Banana 2. Alternativas: google/gemini-3-pro-image (Pro), google/gemini-2.5-flash-image (original).
        modelo_imagem=os.getenv("MODELO_IMAGEM", "google/gemini-3.1-flash-image"),
        app_url=os.getenv("OPENROUTER_APP_URL", "http://localhost"),
        app_nome=os.getenv("OPENROUTER_APP_NOME", "Agente de Conteudo iPhones"),
        timeout_s=float(os.getenv("TIMEOUT_S", "180")),
        max_tokens=int(os.getenv("MAX_TOKENS", "16000")),
        dir_contexto=caminho("DIR_CONTEXTO", "contexto"),
        dir_dados=caminho("DIR_DADOS", "dados"),
        dir_saida=caminho("DIR_SAIDA", "saida"),
    )
