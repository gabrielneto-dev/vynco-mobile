"""Primitivas de desenho da arte (Pillow) e registro de layout usado pelo validador de design.

Cada texto, botão, marca ou selo desenhado é anotado em `Contexto.elementos` (papel, caixa, fonte,
cor do texto e cor do fundo sob ele). `validacao_design.py` confere essas anotações contra o padrão.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

from agente import design
from agente.cadastro import PALETA_PROVISORIA, resolver_caminho

_RE_ETAPAS = re.compile(r"\s+(?:>|→|->|»)\s+")             # "Conversa > avaliação > Pix"
_RE_NUMERO_ITEM = re.compile(r"^\s*(\d{1,2})[.)º°]?\s+")     # "1. Bateria" / "2) Face ID"
RE_TELEFONE = re.compile(r"\(\d{2}\)[\s\u00a0]?\d{4,5}-\d{4}")
LIMIAR_BORDA = 28        # intensidade de borda (0–255) acima da qual a linha da foto "tem objeto"
TITULO_MIN_FAIXA = 58    # px: abaixo disso o título da capa sai da faixa livre e vai para o topo com véu
ESCALA_ANALISE = 4       # a foto é reduzida 4x para achar as faixas livres (rápido e ignora granulação)

Cor = tuple[int, int, int]


class ErroArte(ValueError):
    pass


# ---------------------------------------------------------------------- fontes
def _candidatas(peso: str) -> list[str]:
    env = os.getenv("FONTE_TITULO" if peso in ("bold", "black") else "FONTE_TEXTO", "")
    projeto = str(design.DIR_FONTES / design.ARQUIVOS_FONTE[peso])
    sistema = {
        "regular": [r"C:\Windows\Fonts\segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
        "bold": [r"C:\Windows\Fonts\segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
        "black": [r"C:\Windows\Fonts\seguibl.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    }[peso]
    return [env, projeto, *sistema]


@lru_cache(maxsize=512)
def fonte(peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in _candidatas(peso):
        if caminho and Path(caminho).is_file():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(tamanho)


# ---------------------------------------------------------------------- cores
def _rgb(hexa: str) -> Cor:
    h = hexa.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminancia(rgb: Cor) -> float:
    r, g, b = (c / 255 for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _misturar(a, b, t: float) -> Cor:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


@dataclass
class Paleta:
    fundo: Cor
    texto: Cor
    destaque: Cor

    @property
    def texto_sobre_destaque(self) -> Cor:
        return (20, 20, 24) if _luminancia(self.destaque) > 0.6 else (255, 255, 255)

    @classmethod
    def do_negocio(cls, negocio: dict) -> "Paleta":
        p = negocio.get("paleta_cores") or PALETA_PROVISORIA
        return cls(_rgb(p["fundo"]), _rgb(p["texto"]), _rgb(p["destaque"]))


# ---------------------------------------------------------------------- contexto + registro de layout
@dataclass
class Elemento:
    papel: str                      # titulo | apoio | corpo | item | numero | cta | marca | selo | etiqueta | local | rodape
    caixa: tuple[int, int, int, int]
    tamanho: int = 0                # px da fonte (0 = não é texto, ex.: logo em imagem)
    cor: Cor | None = None
    fundo: Cor | None = None        # cor sob o texto (média medida antes de desenhar, ou cor da pílula)
    texto: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


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
    paginacao: bool = True   # carrossel: número do slide e "arraste ›"; stories já têm a barra de progresso
    elementos: list[Elemento] = field(default_factory=list)

    def registrar(self, papel: str, caixa, *, tamanho: int = 0, cor=None, fundo=None, texto: str = "") -> None:
        caixa = tuple(int(v) for v in caixa)
        self.elementos.append(Elemento(papel, caixa, tamanho, tuple(cor[:3]) if cor else None, tuple(fundo[:3]) if fundo else None, texto))

    def nova_pagina(self) -> None:
        self.elementos = []


# ---------------------------------------------------------------------- texto
def limpar(texto: str | None) -> str:
    """Remove markdown simples e transforma ' | ' em quebras de linha."""
    t = (texto or "").replace("**", "").replace("__", "").strip()
    t = re.sub(r"\s*\|\s*", "\n", t)
    # Telefone nunca quebra no meio: "(17) 99782-2073" fica numa linha só (espaço não separável).
    t = re.sub(r"\((\d{2})\)\s+(\d)", "(\\1)\u00a0\\2", t)
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


def estruturar_slide(texto: str, final: bool) -> tuple[str, list[str]]:
    """Como estruturar(), mas o último slide é fechamento: linhas viram frase (sem ✓ nem números)."""
    if not texto:
        return "paragrafo", []
    tipo, itens = estruturar(texto)
    if final and tipo != "paragrafo":
        return "paragrafo", ["\n".join(itens)]
    return tipo, itens


def separar_telefone(texto: str, negocio: dict) -> tuple[str, str | None]:
    """'Envie modelo: (17) 99782-2073' → ('Envie modelo', 'WhatsApp (17) 99782-2073')."""
    m = RE_TELEFONE.search(texto or "")
    if not m:
        return texto, None
    zap = re.sub(r"\D", "", negocio.get("whatsapp_comercial") or "")
    rotulo = "WhatsApp " if zap and zap == re.sub(r"\D", "", m.group(0)) else ""
    return (texto[: m.start()] + texto[m.end() :]).strip(" :–-\u00a0"), rotulo + m.group(0)


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


def _media(img: Image.Image, caixa) -> Cor:
    x0, y0, x1, y1 = (int(v) for v in caixa)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, max(x1, x0 + 1)), min(img.height, max(y1, y0 + 1))
    return tuple(int(v) for v in ImageStat.Stat(img.convert("RGB").crop((x0, y0, x1, y1))).mean[:3])  # type: ignore[return-value]


def escrever(c: Contexto | None, img, papel: str, linhas, f, x, y, cor, entrelinha=1.18, *, destaque: dict[int, Cor] | None = None) -> int:
    """Escreve as linhas, anota o elemento no layout e devolve a altura usada.
    destaque={i: cor} pinta a primeira palavra da linha i (ex.: numeral "3" na cor de destaque)."""
    passo = int(f.size * entrelinha)
    d = ImageDraw.Draw(img)
    largura = max((d.textlength(l, font=f) for l in linhas), default=0)
    caixa = (x, y, x + largura, y + len(linhas) * passo)
    fundo = _media(img, caixa) if c is not None else None
    for i, l in enumerate(linhas):
        if destaque and i in destaque and " " in l:
            primeira, resto = l.split(" ", 1)
            d.text((x, y + i * passo), primeira, font=f, fill=destaque[i])
            d.text((x + d.textlength(primeira + " ", font=f), y + i * passo), resto, font=f, fill=cor)
        else:
            d.text((x, y + i * passo), l, font=f, fill=cor)
    if c is not None and linhas:
        c.registrar(papel, caixa, tamanho=f.size, cor=cor, fundo=fundo, texto=" ".join(linhas))
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
    ImageDraw.Draw(camada).rounded_rectangle(caixa, radius=raio, fill=tuple(cor[:3]) + (alfa,))
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
        d.line((0, y, img.width, y), fill=tuple(cor[:3]) + (int(alfa_max * t * t * (3 - 2 * t)),))
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


def _cor_legivel(img: Image.Image, caixa, paleta: Paleta) -> tuple[Cor, Cor]:
    """(cor do texto, cor do véu) com mais contraste sobre a região da foto, usando as cores da paleta."""
    lum = ImageStat.Stat(img.crop(caixa).convert("L")).mean[0] / 255
    claro, escuro = sorted((paleta.fundo, paleta.texto), key=_luminancia, reverse=True)
    if _luminancia(escuro) > 0.35:
        escuro = (20, 20, 24)
    if _luminancia(claro) < 0.65:
        claro = (255, 255, 255)
    return (escuro, claro) if lum >= 0.5 else (claro, escuro)


def _altura_pilula(tam: int) -> int:
    return int(tam * 1.18) + 36


def _pilula(img, texto, x, y_base, largura_max, paleta: Paleta, tam=40, *, c: Contexto | None = None, papel: str = "cta",
            cor_fundo: Cor | None = None, cor_texto: Cor | None = None, centro: bool = False) -> tuple[int, int]:
    """Pílula (CTA/etiqueta) com a base em y_base. centro=True: x é o centro. Retorna (largura, altura)."""
    d = ImageDraw.Draw(img)
    f, linhas, _ = ajustar(d, texto, largura_max - 64, tam * 3, "bold", tam, 26)
    largura = int(max(d.textlength(l, font=f) for l in linhas)) + 64
    altura = int(len(linhas) * f.size * 1.18) + 36
    x0 = int(x - largura / 2) if centro else x
    y = y_base - altura
    fundo = cor_fundo or paleta.destaque
    texto_cor = cor_texto or paleta.texto_sobre_destaque
    _cartao(img, (x0, y, x0 + largura, y_base), fundo, alfa=255, raio=altura // 2 if len(linhas) == 1 else 28)
    escrever(None, img, papel, linhas, f, x0 + 32, y + 16, texto_cor)
    if c is not None:
        c.registrar(papel, (x0, y, x0 + largura, y_base), tamanho=f.size, cor=texto_cor, fundo=fundo, texto=" ".join(linhas))
    return largura, altura


def _marca(img, negocio: dict, cfg, x, y_base, paleta: Paleta, *, direita: bool = False, selo: bool = False,
           c: Contexto | None = None, tam: int = 32) -> None:
    """Logo (se houver) ou nome da loja, com a base em y_base. direita=True: x é a borda direita.
    selo=True: desenha sobre um fundo claro (legível sobre fotos)."""
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
        f = fonte("bold", tam)
        w, h = int(ImageDraw.Draw(img).textlength(conteudo, font=f)), int(tam * 1.25)
    pad = 16 if selo else 0
    x0 = (x - w - 2 * pad) if direita else x
    y0 = y_base - h - 2 * pad
    fundo = paleta.fundo if selo else _media(img, (x0, y0, x0 + w, y_base))
    if selo:
        _cartao(img, (x0, y0, x0 + w + 2 * pad, y_base), paleta.fundo, alfa=240, raio=18)
    if isinstance(conteudo, Image.Image):
        img.alpha_composite(conteudo, (x0 + pad, y0 + pad))
        if c is not None:
            c.registrar("marca", (x0, y0, x0 + w + 2 * pad, y_base), texto="logo")
    else:
        ImageDraw.Draw(img).text((x0 + pad, y0 + pad - 2), conteudo, font=fonte("bold", tam), fill=paleta.texto)
        if c is not None:
            c.registrar("marca", (x0, y0, x0 + w + 2 * pad, y_base), tamanho=tam, cor=paleta.texto, fundo=fundo, texto=conteudo)


def altura_marca(tam: int = 32, selo: bool = False) -> int:
    return int(tam * 1.25) + (32 if selo else 0)


def marca_no_topo(img, c: Contexto, x: int, y_topo: int, *, selo: bool, tam: int = 30) -> int:
    """Marca com a borda de cima em y_topo (dentro da zona segura). Retorna a altura ocupada."""
    alt = altura_marca(tam, selo)
    _marca(img, c.negocio, c.cfg, x, y_topo + alt, c.paleta, selo=selo, c=c, tam=tam)
    return alt


def _selo_ilustrativa(img, x_direita: int, y_base: int, *, c: Contexto | None = None) -> None:
    """Selo "Imagem ilustrativa" com a borda direita em x_direita e a base em y_base."""
    f = fonte("regular", 22)
    d = ImageDraw.Draw(img)
    texto = "Imagem ilustrativa"
    w = d.textlength(texto, font=f)
    y_base = min(y_base, img.height - 8)
    x, y = x_direita - 14 - w, y_base - 32
    _cartao(img, (x - 14, y - 6, x + w + 14, y_base), (0, 0, 0), alfa=150, raio=14)
    fundo = _media(img, (x - 14, y - 6, x + w + 14, y_base))
    ImageDraw.Draw(img).text((x, y), texto, font=f, fill=(255, 255, 255))
    if c is not None:
        c.registrar("selo", (x - 14, y - 6, x + w + 14, y_base), tamanho=22, cor=(255, 255, 255), fundo=fundo, texto=texto)


def _barra_destaque(img, x: int, y: int, paleta: Paleta) -> None:
    ImageDraw.Draw(img).rounded_rectangle((x, y, x + 120, y + 12), radius=6, fill=paleta.destaque)


def _seta(d: ImageDraw.ImageDraw, x: int, y_meio: int, cor, tam: int = 18) -> None:
    """Seta › desenhada (a fonte do projeto não tem o glifo →)."""
    e = max(3, tam // 6)
    d.line(((x, y_meio - tam // 2), (x + tam // 2, y_meio), (x, y_meio + tam // 2)), fill=cor, width=e, joint="curve")


def _visto(d: ImageDraw.ImageDraw, x: int, cy: int, r: int, cor) -> None:
    """✓ desenhado com linhas dentro de um círculo de raio r começando em x."""
    e = max(4, r // 5)
    d.line(((x + r * 0.55, cy + r * 0.02), (x + r * 0.88, cy + r * 0.36), (x + r * 1.48, cy - r * 0.34)), fill=cor, width=e, joint="curve")


def _tarja_rascunho(img) -> None:
    f = fonte("bold", 34)
    texto = "RASCUNHO — NÃO PUBLICAR"
    _cartao(img, (0, 0, img.width, 64), (200, 30, 30), alfa=235, raio=0)
    d = ImageDraw.Draw(img)
    d.text(((img.width - d.textlength(texto, font=f)) / 2, 12), texto, font=f, fill=(255, 255, 255))
