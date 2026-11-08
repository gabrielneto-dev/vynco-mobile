"""Geração de imagens com Nano Banana (Gemini Image) via OpenRouter."""

from __future__ import annotations

import base64
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path

from agente.llm import ClienteOpenRouter, ErroLLM

PROPORCOES_VALIDAS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
TAMANHOS_VALIDOS = {"1K", "2K", "4K"}  # suportado pelo Nano Banana Pro / 2

# ---------------------------------------------------------------------- montagem do prompt
# O LLM descreve a cena; o código acrescenta o que não pode depender dele lembrar ou acertar:
# fidelidade do modelo de iPhone, enquadramento casado com o layout da arte, padrão fotográfico e restrições.

# Características físicas que o gerador costuma errar (ex.: desenhar 3 câmeras num iPhone 15).
_TRASEIRA_DUPLA_DIAGONAL = "exactly two rear camera lenses arranged diagonally inside a square camera bump, with the flash beside them"
_NAO_PRO = "It is NOT a Pro model: there is no third lens and no large triangular three-lens camera."
ESPECS_IPHONE = {
    "se": "a single rear camera lens at the top-left corner, a round Home button below the screen, thick top and bottom bezels",
    "11": "two rear camera lenses stacked vertically inside a square camera bump with a rounded frame, notch at the top of the screen",
    "12": "two rear camera lenses stacked vertically inside a square camera bump, flat aluminum sides, notch at the top of the screen",
    "13": f"{_TRASEIRA_DUPLA_DIAGONAL}, flat aluminum sides, small notch at the top of the screen",
    "14": f"{_TRASEIRA_DUPLA_DIAGONAL}, flat aluminum sides, notch at the top of the screen",
    "15": f"{_TRASEIRA_DUPLA_DIAGONAL}, matte frosted color-infused back glass, slightly rounded aluminum edges, Dynamic Island at the top of the screen, USB-C port",
    "16": "exactly two rear camera lenses stacked vertically inside a tall pill-shaped camera bump, aluminum sides, Dynamic Island at the top of the screen",
    "pro": "three rear camera lenses in a triangular arrangement inside a large square camera bump, plus flash and a small sensor",
}
_RE_IPHONE = re.compile(r"\biphone\s*(se|1[1-6])(?:\s*(pro\s*max|pro|plus|mini))?", re.IGNORECASE)

# Enquadramento casado com arte.py: título no topo e marca/CTA na base; o aparelho fica no meio-baixo.
COMPOSICAO = {
    "9:16": (
        "Composition: vertical frame. The phone sits in the middle-lower part of the frame (roughly from 40% to 80% of the height), "
        "fully visible and never cropped, about 45% of the frame width. The top 35% of the frame is an empty, smooth, evenly lit "
        "continuation of the background, reserved for a headline. The bottom 15% is also empty background."
    ),
    "padrao": (
        "Composition: the phone sits in the lower-middle area of the frame (roughly from 40% to 85% of the height), fully visible "
        "and never cropped. The top 35% of the frame is an empty, smooth, evenly lit continuation of the background, reserved "
        "for a headline. Keep the bottom strip calm as well."
    ),
}
ESTILO = (
    "Style: high-end commercial product photography, shot with a 100mm lens at f/8, soft diffused key light from the upper "
    "left with gentle fill, realistic soft contact shadow, crisp edges, true-to-life materials, colors and reflections, "
    "clean minimal tech aesthetic, one single focal point."
)
RESTRICOES = (
    "Avoid: any text, letters, numbers, icons or interface elements; logos, badges or seals of any brand "
    "(no 'official' or 'authorized' marks, no Apple logo emphasis); cracks, scratches, dents or damage; people's faces; "
    "watermarks; extra devices that were not described."
)


def precisao_aparelho(prompt: str) -> str:
    """Linhas 'Device accuracy' para cada iPhone citado no prompt (vazio se nenhum)."""
    linhas, vistos = [], set()
    for m in _RE_IPHONE.finditer(prompt):
        geracao, variante = m.group(1).lower(), re.sub(r"\s+", " ", (m.group(2) or "").lower())
        chave = (geracao, "pro" if "pro" in variante else variante)
        if chave in vistos:
            continue
        vistos.add(chave)
        nome = f"iPhone {geracao.upper() if geracao == 'se' else geracao}" + (f" {variante.title()}" if variante else "")
        if "pro" in variante:
            linhas.append(f"Device accuracy ({nome}): {ESPECS_IPHONE['pro']}.")
        else:
            nao_pro = f" {_NAO_PRO}" if geracao not in ("se", "11", "12") else ""
            linhas.append(f"Device accuracy ({nome}): {ESPECS_IPHONE[geracao]}.{nao_pro}")
    return "\n".join(linhas)


def montar_prompt(prompt: str, proporcao: str, *, paleta: dict | None = None, composicao: bool = True) -> str:
    """Prompt final enviado ao gerador: cena do LLM + fidelidade do aparelho + enquadramento + estilo + restrições."""
    partes = [prompt.strip()]
    if precisao := precisao_aparelho(prompt):
        partes.append(precisao)
    if composicao:
        partes.append(COMPOSICAO.get(proporcao, COMPOSICAO["padrao"]))
    if paleta:
        partes.append(
            f"Color: neutral background close to {paleta['fundo']}; at most a faint hint of {paleta['destaque']} "
            "as a soft reflection or background gradient, never as a logo or graphic."
        )
    partes += [ESTILO, RESTRICOES, f"Aspect ratio: {proporcao}."]
    return "\n\n".join(partes)


@dataclass
class ImagemGerada:
    dados: bytes
    extensao: str
    texto_modelo: str
    prompt_final: str = ""


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
    paleta: dict | None = None,
    composicao: bool = True,
) -> list[ImagemGerada]:
    if proporcao not in PROPORCOES_VALIDAS:
        raise ValueError(f"Proporção inválida: {proporcao}. Use uma de {sorted(PROPORCOES_VALIDAS)}")
    if tamanho and tamanho not in TAMANHOS_VALIDOS:
        raise ValueError(f"Tamanho inválido: {tamanho}. Use {sorted(TAMANHOS_VALIDOS)}")

    texto = montar_prompt(prompt, proporcao, paleta=paleta, composicao=composicao) if aplicar_sufixo else f"{prompt}\n\nAspect ratio: {proporcao}."
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
        saida.append(ImagemGerada(dados=dados, extensao=ext, texto_modelo=str(texto_modelo), prompt_final=texto))
    return saida
