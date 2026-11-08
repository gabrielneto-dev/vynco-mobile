"""Arte pronta para postar: compõe os PNGs finais (texto, CTA, marca) sobre a imagem de fundo.

Processamento local (Pillow), sem custo de API. Regras do briefing embutidas:
  - [PENDENTE] nunca vai para a arte final (só em modo rascunho, com tarja);
  - peça de unidade real do estoque só usa foto real;
  - fundo gerado por IA recebe selo discreto "Imagem ilustrativa";
  - texto sempre dentro das zonas seguras do CREATIVE_STANDARDS.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

from agente.cadastro import PALETA_PROVISORIA, resolver_caminho
from agente.schemas import Brief, Formato, Frente, Peca

# ---------------------------------------------------------------------- medidas
TAMANHOS = {"4:5": (1080, 1350), "1:1": (1080, 1080), "9:16": (1080, 1920)}
# Margens seguras (topo, direita, base, esquerda) em px.
ZONAS = {
    "4:5": (80, 80, 80, 80),
    "1:1": (80, 80, 80, 80),
    "stories": (260, 80, 260, 80),     # ~250 px livres no topo e na base
    "reel": (280, 150, 680, 80),       # fora dos ~14% do topo e ~35% da base; direita livre para os botões
}
_RE_PENDENTE = re.compile(r"\[\s*PENDENTE[^\]]*\]", re.IGNORECASE)
_RE_ETAPAS = re.compile(r"\s+(?:>|→|->|»)\s+")             # "Conversa > avaliação > Pix"
_RE_NUMERO_ITEM = re.compile(r"^\s*(\d{1,2})[.)º°]?\s+")     # "1. Bateria" / "2) Face ID"
_RE_TELEFONE = re.compile(r"\(\d{2}\)[\s ]?\d{4,5}-\d{4}")
LIMIAR_BORDA = 28        # intensidade de borda (0–255) acima da qual a linha da foto "tem objeto"
TITULO_MIN_FAIXA = 58   # px: abaixo disso o título da capa sai da faixa livre e vai para o topo com véu
ESCALA_ANALISE = 4       # a foto é reduzida 4x para achar as faixas livres (rápido e ignora granulação)


class ErroArte(ValueError):
    pass


# ---------------------------------------------------------------------- fontes
_CANDIDATAS = {
    "bold": [
        os.getenv("FONTE_TITULO", ""),
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        os.getenv("FONTE_TEXTO", ""),
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


@lru_cache(maxsize=256)
def fonte(peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in _CANDIDATAS[peso]:
        if caminho and Path(caminho).is_file():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(tamanho)


# ---------------------------------------------------------------------- cores
def _rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminancia(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@dataclass
class Paleta:
    fundo: tuple[int, int, int]
    texto: tuple[int, int, int]
    destaque: tuple[int, int, int]

    @property
    def texto_sobre_destaque(self) -> tuple[int, int, int]:
        return (20, 20, 24) if _luminancia(self.destaque) > 0.6 else (255, 255, 255)

    @classmethod
    def do_negocio(cls, negocio: dict) -> "Paleta":
        p = negocio.get("paleta_cores") or PALETA_PROVISORIA
        return cls(_rgb(p["fundo"]), _rgb(p["texto"]), _rgb(p["destaque"]))


# ---------------------------------------------------------------------- texto
def limpar(texto: str | None) -> str:
    """Remove markdown simples e transforma ' | ' em quebras de linha."""
    t = (texto or "").replace("**", "").replace("__", "").strip()
    t = re.sub(r"\s*\|\s*", "\n", t)
    # Telefone nunca quebra no meio: "(17) 99782-2073" fica numa linha só (espaço não separável).
    t = re.sub(r"\((\d{2})\)\s+(\d)", "(\\1) \\2", t)
    return t.strip()


def _quebrar_guloso(draw: ImageDraw.ImageDraw, paragrafo: str, f: ImageFont.FreeTypeFont, largura: int) -> list[str]:
    palavras, atual, linhas = [p for p in paragrafo.split(" ") if p], "", []  # split(" ") preserva o espaço não separável
    if not palavras:
        return [""]
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if draw.textlength(teste, font=f) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    return linhas


def _quebrar(draw: ImageDraw.ImageDraw, texto: str, f: ImageFont.FreeTypeFont, largura: int) -> list[str]:
    """Quebra em linhas equilibradas: usa a menor largura que mantém o mesmo número de linhas.
    Evita palavra órfã na última linha ("iPhone 13, 14 ou / 15")."""
    linhas: list[str] = []
    for paragrafo in texto.split("\n"):
        melhor = _quebrar_guloso(draw, paragrafo, f, largura)
        if len(melhor) > 1:
            menor, maior = int(largura * 0.5), largura
            while maior - menor > 6:
                meio = (menor + maior) // 2
                teste = _quebrar_guloso(draw, paragrafo, f, meio)
                if len(teste) <= len(melhor) and all(draw.textlength(l, font=f) <= meio for l in teste):
                    melhor, maior = teste, meio
                else:
                    menor = meio
        linhas.extend(melhor)
    return linhas


def _capitalizar(item: str) -> str:
    """'bateria acima de 80%' → 'Bateria acima de 80%' (mas 'iPhone' continua 'iPhone')."""
    if len(item) > 1 and item[0].islower() and not item[1].isupper():
        return item[0].upper() + item[1:]
    return item


def estruturar(texto: str) -> tuple[str, list[str]]:
    """Reconhece a forma do texto da cena: ('lista' | 'etapas' | 'paragrafo', itens).
    Linhas ('a | b | c') viram lista; numeradas ou 'a > b > c' viram etapas."""
    linhas = [l.strip(" -•·") for l in texto.split("\n") if l.strip(" -•·")]
    if len(linhas) >= 2:
        if all(_RE_NUMERO_ITEM.match(l) for l in linhas):
            return "etapas", [_capitalizar(_RE_NUMERO_ITEM.sub("", l)) for l in linhas]
        return "lista", [_capitalizar(l) for l in linhas]
    partes = [p.strip() for p in _RE_ETAPAS.split(texto) if p.strip()]
    if len(partes) >= 2:
        return "etapas", [_capitalizar(p) for p in partes]
    return "paragrafo", [texto.strip()]


def ajustar(draw, texto: str, largura: int, altura: int, peso: str, maximo: int, minimo: int, entrelinha: float = 1.18):
    """Maior fonte (entre máximo e mínimo) em que o texto cabe na caixa. Retorna (fonte, linhas, altura usada)."""
    tamanho = maximo
    while True:
        f = fonte(peso, tamanho)
        linhas = _quebrar(draw, texto, f, largura)
        alt = int(len(linhas) * tamanho * entrelinha)
        largura_ok = all(draw.textlength(l, font=f) <= largura for l in linhas)
        if (alt <= altura and largura_ok) or tamanho <= minimo:
            return f, linhas, alt
        tamanho -= 2


def _escrever(draw, linhas, f, x, y, cor, entrelinha=1.18) -> int:
    passo = int(f.size * entrelinha)
    for i, l in enumerate(linhas):
        draw.text((x, y + i * passo), l, font=f, fill=cor)
    return len(linhas) * passo


# ---------------------------------------------------------------------- blocos visuais
def _fundo(tamanho, paleta: Paleta, imagem: Path | None) -> Image.Image:
    if imagem:
        img = Image.open(imagem).convert("RGB")
        return ImageOps.fit(img, tamanho, method=Image.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
    base = Image.new("RGBA", tamanho, paleta.fundo + (255,))
    # Assinatura discreta da marca: filete na cor de destaque na borda inferior.
    w, h = tamanho
    ImageDraw.Draw(base).rectangle((0, h - 10, w, h), fill=paleta.destaque + (255,))
    return base


def _cartao(img: Image.Image, caixa, cor, alfa=232, raio=36) -> None:
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(camada).rounded_rectangle(caixa, radius=raio, fill=cor + (alfa,))
    img.alpha_composite(camada)


def _veu(img: Image.Image, y0: int, y1: int, cor, alfa_max: int) -> None:
    """Véu suave (degradê vertical que some nas bordas) atrás do texto sobre foto: dá leitura sem caixa dura."""
    if alfa_max <= 0 or y1 <= y0:
        return
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    altura = y1 - y0
    borda = max(1, int(altura * 0.3))
    for y in range(max(0, y0), min(img.height, y1)):
        dist = min(y - y0, y1 - y)
        t = min(1.0, dist / borda)
        d.line((0, y, img.width, y), fill=cor + (int(alfa_max * t * t * (3 - 2 * t)),))
    img.alpha_composite(camada)


def faixas_livres(img: Image.Image, x0: int, x1: int) -> list[tuple[int, int]]:
    """Faixas horizontais da foto sem objeto (só fundo liso), em px: [(y_inicio, y_fim), ...].
    Mede a borda mais forte de cada linha entre x0 e x1; linha com borda fraca é fundo."""
    e = ESCALA_ANALISE
    p = (
        img.convert("L")
        .resize((max(1, img.width // e), max(1, img.height // e)), Image.BILINEAR)
        .filter(ImageFilter.GaussianBlur(1))
        .filter(ImageFilter.FIND_EDGES)
    )
    a, b = max(2, x0 // e), min(p.width - 2, x1 // e)
    if b <= a:
        return []
    calmas = [p.crop((a, y, b, y + 1)).getextrema()[1] < LIMIAR_BORDA for y in range(p.height)]
    if len(calmas) > 2:  # FIND_EDGES marca a primeira e a última linha da imagem: herdam a vizinha
        calmas[0], calmas[-1] = calmas[1], calmas[-2]
    faixas, inicio = [], None
    for y, calma in enumerate(calmas + [False]):
        if calma and inicio is None:
            inicio = y
        elif not calma and inicio is not None:
            faixas.append((inicio * e, y * e))
            inicio = None
    return faixas


def _melhor_faixa(img: Image.Image, y_min: int, y_max: int, x0: int, x1: int, altura_min: int) -> tuple[int, int] | None:
    """Maior faixa livre dentro de [y_min, y_max] com pelo menos altura_min px; None se não houver."""
    candidatas = []
    for a, b in faixas_livres(img, x0, x1):
        a, b = max(a, y_min), min(b, y_max)
        if b - a >= altura_min:
            candidatas.append((b - a, -a, (a, b)))  # maior primeiro; empate: a mais alta
    return max(candidatas)[2] if candidatas else None


def _cor_legivel(img: Image.Image, caixa, paleta: Paleta) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """(cor do texto, cor do véu) com mais contraste sobre a região da foto, usando as cores da paleta."""
    lum = ImageStat.Stat(img.crop(caixa).convert("L")).mean[0] / 255
    claro, escuro = sorted((paleta.fundo, paleta.texto), key=_luminancia, reverse=True)
    if _luminancia(escuro) > 0.35:
        escuro = (20, 20, 24)
    if _luminancia(claro) < 0.65:
        claro = (255, 255, 255)
    return (escuro, claro) if lum >= 0.5 else (claro, escuro)


def _pilula(img, texto, x, y_base, largura_max, paleta: Paleta, tam=40) -> tuple[int, int]:
    """Botão de CTA na cor de destaque, com a base em y_base. Retorna (largura, altura)."""
    d = ImageDraw.Draw(img)
    f, linhas, _ = ajustar(d, texto, largura_max - 64, tam * 3, "bold", tam, 26)
    largura = int(max(d.textlength(l, font=f) for l in linhas)) + 64
    altura = int(len(linhas) * f.size * 1.18) + 36
    y = y_base - altura
    _cartao(img, (x, y, x + largura, y_base), paleta.destaque, alfa=255, raio=altura // 2 if len(linhas) == 1 else 28)
    _escrever(ImageDraw.Draw(img), linhas, f, x + 32, y + 16, paleta.texto_sobre_destaque)
    return largura, altura


def _altura_pilula(tam: int) -> int:
    return int(tam * 1.18) + 36


def _marca(img, negocio: dict, cfg, x, y_base, paleta: Paleta, *, direita: bool = False, selo: bool = False) -> None:
    """Logo (se houver) ou nome da loja, com a base em y_base. direita=True: x é a borda direita.
    selo=True: desenha sobre um fundo translúcido (legível sobre fotos)."""
    logo = negocio.get("logotipo")
    conteudo: Image.Image | str | None = None
    if logo and resolver_caminho(cfg, logo).is_file():
        conteudo = Image.open(resolver_caminho(cfg, logo)).convert("RGBA")
        conteudo.thumbnail((260, 72), Image.LANCZOS)
        w, h = conteudo.size
    else:
        conteudo = negocio.get("nome_loja") or negocio.get("instagram")
        if not conteudo:
            return
        f = fonte("bold", 32)
        w, h = int(ImageDraw.Draw(img).textlength(conteudo, font=f)), 40
    pad = 16 if selo else 0
    x0 = (x - w - 2 * pad) if direita else x
    y0 = y_base - h - 2 * pad
    if selo:
        _cartao(img, (x0, y0, x0 + w + 2 * pad, y_base), paleta.fundo, alfa=225, raio=18)
    if isinstance(conteudo, Image.Image):
        img.alpha_composite(conteudo, (x0 + pad, y0 + pad))
    else:
        ImageDraw.Draw(img).text((x0 + pad, y0 + pad - 2), conteudo, font=fonte("bold", 32), fill=paleta.texto)


def _selo_ilustrativa(img, x_direita: int, y_base: int) -> None:
    """Selo "Imagem ilustrativa" com a borda direita em x_direita e a base em y_base."""
    f = fonte("regular", 22)
    d = ImageDraw.Draw(img)
    texto = "Imagem ilustrativa"
    w = d.textlength(texto, font=f)
    y_base = min(y_base, img.height - 8)
    x, y = x_direita - 14 - w, y_base - 32
    _cartao(img, (x - 14, y - 6, x + w + 14, y_base), (0, 0, 0), alfa=110, raio=14)
    ImageDraw.Draw(img).text((x, y), texto, font=f, fill=(255, 255, 255))


def _barra_destaque(img, x: int, y: int, paleta: Paleta) -> None:
    ImageDraw.Draw(img).rounded_rectangle((x, y, x + 120, y + 12), radius=6, fill=paleta.destaque)


def _tarja_rascunho(img) -> None:
    f = fonte("bold", 34)
    texto = "RASCUNHO — NÃO PUBLICAR"
    _cartao(img, (0, 0, img.width, 64), (200, 30, 30), alfa=235, raio=0)
    d = ImageDraw.Draw(img)
    d.text(((img.width - d.textlength(texto, font=f)) / 2, 12), texto, font=f, fill=(255, 255, 255))


# ---------------------------------------------------------------------- layouts
@dataclass
class Contexto:
    paleta: Paleta
    negocio: dict
    cfg: object
    zona: tuple[int, int, int, int]
    tamanho: tuple[int, int]
    fundo_ia: bool = False
    rascunho: bool = False
    selo: bool = True
    paginacao: bool = True   # carrossel: número do slide e "arraste →"; stories já têm a barra de progresso


def _bloco_titulo(d, titulo: str, apoio: str | None, largura: int, altura: int, tam_max: int):
    """Ajusta título (+ apoio) à caixa. Retorna (ft, lt, at, fa, la, aa) com a altura total em at + aa."""
    vao = 24 if apoio else 0
    ft, lt, at = ajustar(d, titulo, largura, int(altura * (0.66 if apoio else 1.0)), "bold", tam_max, 44)
    fa = la = None
    aa = 0
    if apoio:
        fa, la, aa = ajustar(d, apoio, largura, max(60, altura - at - vao), "regular", 42, 26, 1.25)
        aa += vao
    return ft, lt, at, fa, la, aa


def capa(c: Contexto, titulo: str, apoio: str | None, cta: str | None, imagem: Path | None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, imagem)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    tam_max = 92 if w / h < 0.7 else 84
    y_base = h - base
    rodape = (_altura_pilula(40) if cta else 72) + 48     # CTA/marca + respiro
    y_lim = y_base - rodape

    cor_texto, cor_veu, alfa_veu, faixa = c.paleta.texto, c.paleta.fundo, 0, None
    if imagem:
        # Título na maior faixa livre da foto (sem cobrir o aparelho); sem faixa livre, no topo com véu forte.
        faixa = _melhor_faixa(img, top, y_lim, esq, w - dir_, altura_min=int(h * 0.13))
        if faixa and _bloco_titulo(d, titulo, apoio, largura, faixa[1] - faixa[0] - 48, tam_max)[0].size < TITULO_MIN_FAIXA:
            faixa = None  # faixa livre estreita demais: título miúdo é pior que um véu sobre a foto
        y0, y1 = faixa or (top, top + int((y_lim - top) * 0.5))
        alfa_veu = 150 if faixa else 225
    else:
        y0, y1 = top, y_lim
    ft, lt, at, fa, la, aa = _bloco_titulo(d, titulo, apoio, largura, y1 - y0 - 48, tam_max)
    bloco = 36 + at + aa                                  # barra de destaque + título + apoio
    y = y0 + max(0, int((y1 - y0 - bloco) * (0.35 if imagem else 0.38)))
    if imagem:
        cor_texto, cor_veu = _cor_legivel(img, (esq, y, w - dir_, y + bloco), c.paleta)
        # Na faixa livre o véu não passa dela (não encosta no aparelho); sem faixa, cobre o topo inteiro.
        v0, v1 = (max(y0, y - 70), min(y1, y + bloco + 70)) if faixa else (0, y + bloco + 90)
        _veu(img, v0, v1, cor_veu, alfa_veu)
    d = ImageDraw.Draw(img)
    _barra_destaque(img, esq, y, c.paleta)
    y += 36
    y += _escrever(d, lt, ft, esq, y, cor_texto)
    if apoio:
        _escrever(d, la, fa, esq, y + 24, cor_texto, 1.25)

    # Rodapé: CTA à esquerda e marca à direita; sem CTA, marca à esquerda e selo à direita na mesma linha.
    if cta:
        _pilula(img, cta, esq, y_base, int(largura * 0.68), c.paleta)
        _marca(img, c.negocio, c.cfg, w - dir_, y_base, c.paleta, direita=True, selo=bool(imagem))
        y_selo = min(h - 12, y_base + 52)
    else:
        _marca(img, c.negocio, c.cfg, esq, y_base, c.paleta, selo=bool(imagem))
        y_selo = y_base
    if c.fundo_ia and c.selo and imagem:
        _selo_ilustrativa(img, w - dir_, y_selo)
    return img


def _ajustar_itens(d, itens: list[str], largura: int, altura: int, maximo: int = 76, minimo: int = 34):
    """Maior fonte em que a lista cabe. Retorna (fonte, blocos de linhas, altura de cada item, ícone, vão)."""
    for tam in range(maximo, minimo - 1, -2):
        f = fonte("bold", tam)
        icone = int(tam * 1.05)
        recuo = icone + int(tam * 0.55)
        vao = int(tam * 0.75)
        blocos = [_quebrar(d, it, f, largura - recuo) for it in itens]
        alturas = [max(int(len(b) * tam * 1.18), icone) for b in blocos]
        cabe = sum(alturas) + vao * (len(itens) - 1) <= altura
        # Até 80% do tamanho máximo, prefere diminuir a fonte a quebrar um item em duas linhas.
        sem_quebra = all(len(b) == 1 for b in blocos) or tam <= int(maximo * 0.8)
        if (cabe and sem_quebra) or tam <= minimo:
            return f, blocos, alturas, icone, vao


def _misturar(a, b, t: float) -> tuple[int, int, int]:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _desenhar_itens(img, c: Contexto, tipo: str, itens: list[str], x: int, y_min: int, y_max: int, largura: int, *, barra: bool) -> None:
    d = ImageDraw.Draw(img)
    topo = 56 if barra else 0  # barra de destaque logo acima da lista
    f, blocos, alturas, icone, vao = _ajustar_itens(d, itens, largura, y_max - y_min - topo)
    total = topo + sum(alturas) + vao * (len(itens) - 1)
    y = y_min + max(0, int((y_max - y_min - total) * 0.42))
    if barra:
        _barra_destaque(img, x, y, c.paleta)
        y += topo
    recuo = icone + int(f.size * 0.55)
    linha_cor = _misturar(c.paleta.destaque, c.paleta.fundo, 0.6)
    centros = []
    for linhas, alt in zip(blocos, alturas):
        centros.append(y + int(f.size * 1.18) // 2)  # ícone alinhado à primeira linha do item
        _escrever(d, linhas, f, x + recuo, y, c.paleta.texto)
        y += alt + vao
    r = icone // 2
    if tipo == "etapas":  # linha que liga as etapas, atrás dos círculos
        for a, b in zip(centros, centros[1:]):
            d.line((x + r, a + r, x + r, b - r), fill=linha_cor, width=max(4, icone // 12))
    f_num = fonte("bold", int(icone * 0.55))
    for i, cy in enumerate(centros, 1):
        d.ellipse((x, cy - r, x + icone, cy + r), fill=c.paleta.destaque)
        cor = c.paleta.texto_sobre_destaque
        if tipo == "etapas":
            n = str(i)
            d.text((x + r - d.textlength(n, font=f_num) / 2, cy - f_num.size * 0.62), n, font=f_num, fill=cor)
        else:  # visto (✓) desenhado com linhas: não depende da fonte ter o glifo
            e = max(4, icone // 10)
            d.line(((x + r * 0.55, cy + r * 0.02), (x + r * 0.88, cy + r * 0.36), (x + r * 1.48, cy - r * 0.34)), fill=cor, width=e, joint="curve")


def slide_texto(c: Contexto, numero: int, total: int, texto: str, final: bool = False, cta: str | None = None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, None)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_

    if c.paginacao and not final:
        d.text((esq, top - 10), f"{numero:02d}", font=fonte("bold", 96), fill=c.paleta.destaque)
        y_min = top + 140
    else:
        y_min = top + 20
    y_max = h - base - 110  # acima do rodapé

    # Último slide: o telefone sai do texto e vira o botão de destaque.
    telefone = None
    if final and (m := _RE_TELEFONE.search(texto or "")):
        telefone = m.group(0)
        texto = (texto[: m.start()] + texto[m.end() :]).strip(" :–- ")
    botao = None
    if telefone:
        zap = re.sub(r"\D", "", c.negocio.get("whatsapp_comercial") or "")
        botao = ("WhatsApp " if zap and zap == re.sub(r"\D", "", telefone) else "") + telefone
    elif final and cta:
        botao = cta
    alt_botao = (_altura_pilula(48) + 56) if botao else 0

    tipo, itens = estruturar(texto) if texto else ("paragrafo", [])
    if tipo == "paragrafo":
        tam_max = 84 if final else 76
        f, linhas, alt = ajustar(d, itens[0], largura, y_max - y_min - alt_botao - 36, "bold", tam_max, 34, 1.2) if itens else (None, [], 0)
        bloco = 36 + alt + alt_botao
        y = y_min + max(0, int((y_max - y_min - bloco) * 0.42))
        if not c.paginacao or final:
            _barra_destaque(img, esq, y, c.paleta)
        y += 36
        if linhas:
            y += _escrever(d, linhas, f, esq, y, c.paleta.texto, 1.2)
        if botao:
            _pilula(img, botao, esq, y + alt_botao, largura, c.paleta, tam=48)
    else:
        _desenhar_itens(img, c, tipo, itens, esq, y_min, y_max - alt_botao, largura, barra=not c.paginacao)
        if botao:
            _pilula(img, botao, esq, y_max, largura, c.paleta, tam=48)

    d = ImageDraw.Draw(img)
    _marca(img, c.negocio, c.cfg, esq, h - base, c.paleta)
    if c.paginacao:
        f_rod = fonte("regular", 28)
        rodape = f"{numero}/{total}" + ("   arraste →" if not final else "")
        d.text((w - dir_ - d.textlength(rodape, font=f_rod), h - base - 36), rodape, font=f_rod, fill=c.paleta.texto)
    return img


def cartela_reel(c: Contexto, texto: str) -> Image.Image:
    """PNG transparente para sobrepor no vídeo (texto dentro da zona segura do Reels)."""
    img = Image.new("RGBA", c.tamanho, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    pad = 36
    f, linhas, alt = ajustar(d, texto, largura - 2 * pad, int((h - top - base) * 0.6), "bold", 72, 36)
    y = top + int((h - top - base - alt - 2 * pad) * 0.35)
    _cartao(img, (esq, y, esq + largura, y + alt + 2 * pad), c.paleta.fundo, alfa=245)
    _escrever(ImageDraw.Draw(img), linhas, f, esq + pad, y + pad, c.paleta.texto)
    return img


# ---------------------------------------------------------------------- orquestração
@dataclass
class ResultadoArte:
    pasta: Path
    arquivos: list[Path]
    rascunho: bool
    fundo: str
    avisos: list[str] = field(default_factory=list)


def pendencias_no_texto(textos: list[str]) -> list[str]:
    vistos: list[str] = []
    for t in textos:
        for m in _RE_PENDENTE.findall(t or ""):
            if m not in vistos:
                vistos.append(m)
    return vistos


def _normalizar(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip(" .!")


def _redundante(texto: str, titulo: str) -> bool:
    """Texto de apoio que só repete o título (≥60% das palavras) não entra na arte."""
    a = set(re.findall(r"\w+", _normalizar(texto)))
    b = set(re.findall(r"\w+", _normalizar(titulo)))
    return not a or len(a & b) / len(a) >= 0.6


def escolher_fundo(ag, peca_id: str, brief: Brief, preferencia: str = "auto") -> tuple[Path | None, str]:
    """Retorna (caminho, tipo) com tipo em: foto_real | ia | liso."""
    if brief.frente == Frente.venda and brief.produto_id:
        produto = ag.ctx.produto(brief.produto_id)
        if not produto:
            raise ErroArte(f"Unidade {brief.produto_id} não está no estoque.")
        if preferencia == "liso":
            return None, "liso"
        fotos = [resolver_caminho(ag.cfg, f) for f in produto.fotos]
        fotos = [f for f in fotos if f.is_file()]
        if not fotos:
            raise ErroArte(f"Peça de unidade real: cadastre fotos reais de {brief.produto_id} (📱 Estoque → Adicionar fotos). Imagem gerada não é permitida.")
        return fotos[0], "foto_real"
    if preferencia == "liso":
        return None, "liso"
    imagens = ag.registro.entrada(peca_id).get("imagens", [])
    if imagens:
        return ag.registro.dir / imagens[-1], "ia"
    if preferencia == "ia":
        raise ErroArte("Esta peça ainda não tem imagem gerada (🎨 Gerar imagem) — ou escolha fundo liso.")
    return None, "liso"


def montar_arte(ag, peca_id: str, *, gancho: int = 1, rascunho: bool = False, fundo: str = "auto") -> ResultadoArte:
    peca, brief, _, doc = ag.registro.carregar_modelos(peca_id)
    negocio = ag.ctx.negocio
    if not 1 <= gancho <= len(peca.ganchos):
        raise ErroArte(f"Gancho {gancho} não existe (1 a {len(peca.ganchos)}).")
    titulo = limpar(peca.ganchos[gancho - 1])
    cta = limpar(peca.cta)
    cenas = [limpar(c.texto_tela) for c in sorted(peca.roteiro, key=lambda c: c.ordem)]
    imagem, tipo_fundo = escolher_fundo(ag, peca_id, brief, fundo)

    formato = brief.formato
    if formato in (Formato.reel, Formato.stories):
        proporcao = "9:16"
    else:
        p = peca.direcao_arte.proporcao.strip().replace(" ", "")[:4]
        proporcao = p if p in TAMANHOS and p != "9:16" else "4:5"
    zona = ZONAS["reel" if formato == Formato.reel else "stories" if formato == Formato.stories else proporcao]

    # O que vai aparecer na arte (para checar pendências).
    if formato in (Formato.imagem, Formato.anuncio):
        apoio = cenas[0] if cenas and not _redundante(cenas[0], titulo) else None
        textos = [titulo, apoio or "", cta]
    else:
        textos = [titulo, cta] + cenas[1:]
    pend = pendencias_no_texto(textos)
    if pend and not rascunho:
        raise ErroArte(
            "A arte não pode ir ao ar com campos pendentes: " + ", ".join(pend)
            + ". Preencha em 🏪 Dados do negócio (peças novas já saem completas) ou gere como rascunho."
        )

    c = Contexto(
        paleta=Paleta.do_negocio(negocio),
        negocio=negocio,
        cfg=ag.cfg,
        zona=zona,
        tamanho=TAMANHOS[proporcao],
        fundo_ia=tipo_fundo == "ia",
        rascunho=rascunho,
        selo=os.getenv("SELO_ILUSTRATIVA", "1") != "0",
        paginacao=formato == Formato.carrossel,
    )

    paginas: list[tuple[str, Image.Image]] = []
    if formato in (Formato.imagem, Formato.anuncio):
        paginas.append(("01.png", capa(c, titulo, apoio, cta, imagem)))
    elif formato in (Formato.carrossel, Formato.stories):
        internas = [t for t in cenas[1:] if t]
        ultima_e_cta = bool(internas) and _normalizar(cta)[:25] in _normalizar(internas[-1])
        total = 1 + len(internas) + (0 if ultima_e_cta else 1)
        paginas.append(("01.png", capa(c, titulo, None, None, imagem)))
        for i, t in enumerate(internas, 2):
            final = ultima_e_cta and i == len(internas) + 1
            paginas.append((f"{i:02d}.png", slide_texto(c, i, total, t, final=final, cta=None)))
        if not ultima_e_cta:
            paginas.append((f"{total:02d}.png", slide_texto(c, total, total, "", final=True, cta=cta)))
    elif formato == Formato.reel:
        paginas.append(("00-capa.png", capa(c, titulo, None, None, imagem)))
        for i, t in enumerate(cenas, 1):
            if t:
                paginas.append((f"{i:02d}-cartela.png", cartela_reel(c, t)))

    if rascunho:
        for _, img in paginas:
            _tarja_rascunho(img)

    rotulo = f"v{doc['versao']}-g{gancho}-{tipo_fundo}" + ("-rascunho" if rascunho else "")
    pasta = ag.registro.dir_peca(peca_id) / "arte" / rotulo
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.png"):
        antigo.unlink()
    arquivos = []
    for nome, img in paginas:
        destino = pasta / nome
        (img if nome.endswith("cartela.png") else img.convert("RGB")).save(destino, optimize=True)
        arquivos.append(destino)

    avisos = []
    if not (negocio.get("logotipo") or negocio.get("nome_loja") or negocio.get("instagram")):
        avisos.append("Sem logo nem nome da loja cadastrados: a arte saiu sem assinatura.")
    if not negocio.get("paleta_cores"):
        avisos.append("Paleta provisória (neutra) — cadastre a paleta oficial em 🏪 Dados do negócio.")
    if formato == Formato.reel:
        avisos.append("Reel: use 00-capa.png como capa e sobreponha as cartelas no vídeo, na ordem das cenas.")

    meta = {
        "peca": peca_id,
        "versao_peca": doc["versao"],
        "formato": formato.value,
        "proporcao": proporcao,
        "titulo": titulo,
        "gancho": gancho,
        "cta": cta,
        "fundo": {"tipo": tipo_fundo, "arquivo": str(imagem) if imagem else None},
        "rascunho": rascunho,
        "pendencias": pend,
        "arquivos": [a.name for a in arquivos],
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    (pasta / "arte.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    ag.registro.registrar_arte(peca_id, pasta, rascunho=rascunho)
    return ResultadoArte(pasta, arquivos, rascunho, tipo_fundo, avisos)
