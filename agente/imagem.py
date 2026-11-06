"""Geração de imagens com Nano Banana (Gemini Image) via OpenRouter."""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path

from agente.llm import ClienteOpenRouter, ErroLLM

PROPORCOES_VALIDAS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
TAMANHOS_VALIDOS = {"1K", "2K", "4K"}  # suportado pelo Nano Banana Pro / 2

# Acrescentado a todo prompt: regras de CREATIVE_STANDARDS.md que não podem depender do LLM lembrar.
SUFIXO_PADRAO = (
    "\n\nConstraints: photorealistic, accurate real-world iPhone proportions, camera layout and finishes; "
    "clean minimal tech aesthetic; no brand logos as design elements, no Apple logo emphasis, "
    "no 'official'/'authorized' badges, no visible damage or cracked screens, no watermark, "
    "no recognizable real people. Leave clean negative space for text overlay."
)


@dataclass
class ImagemGerada:
    dados: bytes
    extensao: str
    texto_modelo: str


def _data_url(caminho: Path) -> str:
    mime = mimetypes.guess_type(caminho.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(caminho.read_bytes()).decode()}"


def _decodificar(url: str) -> tuple[bytes, str]:
    if not url.startswith("data:"):
        raise ErroLLM(f"Formato de imagem inesperado: {url[:60]}...")
    cabecalho, b64 = url.split(",", 1)
    mime = cabecalho[5:].split(";")[0]
    ext = (mimetypes.guess_extension(mime) or ".png").lstrip(".")
    return base64.b64decode(b64), "jpg" if ext == "jpe" else ext


def gerar_imagens(
    cliente: ClienteOpenRouter,
    prompt: str,
    *,
    proporcao: str = "4:5",
    modelo: str | None = None,
    tamanho: str | None = None,
    referencias: list[Path] | None = None,
    aplicar_sufixo: bool = True,
) -> list[ImagemGerada]:
    if proporcao not in PROPORCOES_VALIDAS:
        raise ValueError(f"Proporção inválida: {proporcao}. Use uma de {sorted(PROPORCOES_VALIDAS)}")
    if tamanho and tamanho not in TAMANHOS_VALIDOS:
        raise ValueError(f"Tamanho inválido: {tamanho}. Use {sorted(TAMANHOS_VALIDOS)}")

    texto = prompt + (SUFIXO_PADRAO if aplicar_sufixo else "") + f"\nAspect ratio: {proporcao}."
    conteudo: list[dict] = [{"type": "text", "text": texto}]
    for ref in referencias or []:
        conteudo.append({"type": "image_url", "image_url": {"url": _data_url(Path(ref))}})

    image_config: dict = {"aspect_ratio": proporcao}
    if tamanho:
        image_config["image_size"] = tamanho

    data = cliente.post(
        {
            "model": modelo or cliente.cfg.modelo_imagem,
            "messages": [{"role": "user", "content": conteudo}],
            "modalities": ["image", "text"],
            "image_config": image_config,
        }
    )
    msg = data["choices"][0]["message"]
    imagens = msg.get("images") or []
    if not imagens:
        raise ErroLLM(f"O modelo não retornou imagem. Resposta em texto: {str(msg.get('content'))[:500]}")

    texto_modelo = msg.get("content") or ""
    saida = []
    for img in imagens:
        url = (img.get("image_url") or {}).get("url", "")
        dados, ext = _decodificar(url)
        saida.append(ImagemGerada(dados=dados, extensao=ext, texto_modelo=str(texto_modelo)))
    return saida
