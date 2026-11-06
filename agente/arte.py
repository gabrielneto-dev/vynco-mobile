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

from PIL import Image, ImageDraw, ImageFont, ImageOps

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
    return t.strip()


def _quebrar(draw: ImageDraw.ImageDraw, texto: str, f: ImageFont.FreeTypeFont, largura: int) -> list[str]:
    linhas: list[str] = []
    for paragrafo in texto.split("\n"):
        palavras, atual = paragrafo.split(), ""
        if not palavras:
            linhas.append("")
            continue
        for p in palavras:
            teste = f"{atual} {p}".strip()
            if draw.textlength(teste, font=f) <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = p
        linhas.append(atual)
    return linhas


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
    # Detalhe discreto na cor de destaque, no canto inferior direito, longe do texto.
    # (Camada separada: desenhar com alfa direto na imagem substituiria os pixels em vez de misturar.)
    camada = Image.new("RGBA", tamanho, (0, 0, 0, 0))
    w, h = tamanho
    ImageDraw.Draw(camada).ellipse((w * 0.68, h * 0.78, w * 1.3, h * 1.25), fill=paleta.destaque + (30,))
    base.alpha_composite(camada)
    return base


def _cartao(img: Image.Image, caixa, cor, alfa=232, raio=36) -> None:
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(camada).rounded_rectangle(caixa, radius=raio, fill=cor + (alfa,))
    img.alpha_composite(camada)


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


def _selo_ilustrativa(img, zona, cor=(255, 255, 255)) -> None:
    f = fonte("regular", 22)
    d = ImageDraw.Draw(img)
    texto = "Imagem ilustrativa"
    w = d.textlength(texto, font=f)
    x, y = img.width - zona[1] - w, img.height - zona[2] + 28
    if y + 30 > img.height:
        y = img.height - 40
    _cartao(img, (x - 14, y - 6, x + w + 14, y + 32), (0, 0, 0), alfa=110, raio=14)
    ImageDraw.Draw(img).text((x, y), texto, font=f, fill=cor)


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


def capa(c: Contexto, titulo: str, apoio: str | None, cta: str | None, imagem: Path | None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, imagem)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    pad = 44

    # Cartão com título (e texto de apoio) no terço superior da área segura.
    alt_max = int((h - top - base) * (0.55 if imagem else 0.7))
    ft, lt, at = ajustar(d, titulo, largura - 2 * pad, int(alt_max * (0.62 if apoio else 1.0)), "bold", 92 if w / h < 0.7 else 84, 40)
    fa = la = None
    aa = 0
    if apoio:
        fa, la, aa = ajustar(d, apoio, largura - 2 * pad, alt_max - at - 20, "regular", 42, 26, 1.25)
    alt_cartao = pad * 2 + at + (aa + 20 if apoio else 0)
    _cartao(img, (esq, top, esq + largura, top + alt_cartao), c.paleta.fundo, alfa=250 if imagem else 0)
    d = ImageDraw.Draw(img)
    if not imagem:  # capa sem foto: barra de destaque acima do título
        d.rounded_rectangle((esq + pad, top + pad - 34, esq + pad + 140, top + pad - 22), radius=6, fill=c.paleta.destaque)
    y = top + pad
    y += _escrever(d, lt, ft, esq + pad, y, c.paleta.texto)
    if apoio:
        _escrever(d, la, fa, esq + pad, y + 20, c.paleta.texto, 1.25)

    # CTA à esquerda e marca à direita, na base da área segura.
    y_base = h - base
    if cta:
        _pilula(img, cta, esq, y_base, int(largura * 0.68), c.paleta)
    _marca(img, c.negocio, c.cfg, w - dir_, y_base, c.paleta, direita=True, selo=bool(imagem))
    if c.fundo_ia and c.selo and imagem:
        _selo_ilustrativa(img, c.zona)
    return img


def slide_texto(c: Contexto, numero: int, total: int, texto: str, final: bool = False, cta: str | None = None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, None)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_

    if not final:
        f_num = fonte("bold", 120)
        d.text((esq, top - 10), f"{numero:02d}", font=f_num, fill=c.paleta.destaque)
        y_min = top + 170
    else:
        y_min = top + 40
    y_max = h - base - 110  # acima do rodapé
    alt_pilula = (44 * 2 + 36 + 50) if (final and cta) else 0
    f, linhas, alt = ajustar(d, texto, largura, y_max - y_min - alt_pilula, "bold", 92, 34, 1.2) if texto else (None, [], 0)
    # Bloco (texto + CTA) centralizado verticalmente no espaço disponível, levemente acima do centro.
    bloco = alt + alt_pilula
    y_texto = y_min + max(0, int((y_max - y_min - bloco) * 0.4))
    if linhas:
        _escrever(d, linhas, f, esq, y_texto, c.paleta.texto, 1.2)

    if final and cta:
        _pilula(img, cta, esq, y_texto + bloco, largura, c.paleta, tam=44)
    d = ImageDraw.Draw(img)
    # Rodapé: marca à esquerda, paginação/arraste à direita.
    _marca(img, c.negocio, c.cfg, esq, h - base, c.paleta)
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
        apoio = cenas[0] if cenas and _normalizar(cenas[0]) != _normalizar(titulo) else None
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
