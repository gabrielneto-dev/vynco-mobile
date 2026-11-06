"""Carrega a engenharia de contexto (arquivos .md) e os dados reais do negócio."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agente.config import Config
from agente.schemas import Aparelho

ORDEM_ARQUIVOS = [
    "BRIEFING.md",
    "BRAND.md",
    "AUDIENCES.md",
    "CONTENT_PILLARS.md",
    "COPY_GUIDELINES.md",
    "CREATIVE_STANDARDS.md",
    "QUALITY_RULES.md",
]


@dataclass
class Contexto:
    arquivos: dict[str, str]
    negocio: dict
    estoque: list[Aparelho] = field(default_factory=list)

    @property
    def negocio_confirmado(self) -> dict:
        return {k: v for k, v in self.negocio.items() if not k.startswith("_") and v not in (None, "", [])}

    @property
    def negocio_pendente(self) -> list[str]:
        return [k for k, v in self.negocio.items() if not k.startswith("_") and v in (None, "", [])]

    @property
    def estoque_disponivel(self) -> list[Aparelho]:
        return [a for a in self.estoque if a.disponivel]

    def produto(self, produto_id: str) -> Aparelho | None:
        return next((a for a in self.estoque if a.id == produto_id), None)


def _ler_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    return json.loads(caminho.read_text(encoding="utf-8"))


def carregar_contexto(cfg: Config) -> Contexto:
    arquivos: dict[str, str] = {}
    for nome in ORDEM_ARQUIVOS:
        p = cfg.dir_contexto / nome
        if p.exists():
            arquivos[nome] = p.read_text(encoding="utf-8")
    # Arquivos extras que o time adicionar em contexto/ também entram.
    for p in sorted(cfg.dir_contexto.glob("*.md")):
        if p.name not in arquivos:
            arquivos[p.name] = p.read_text(encoding="utf-8")

    negocio = _ler_json(cfg.dir_dados / "negocio.json", {})
    estoque = [Aparelho.model_validate(x) for x in _ler_json(cfg.dir_dados / "estoque.json", [])]
    return Contexto(arquivos=arquivos, negocio=negocio, estoque=estoque)
