"""Estilo nativo (Stories e anúncios): foto cheia + etiquetas no jeito do Instagram.

Base: o que domina e dura na Biblioteca de Anúncios (foto real do aparelho na mão, quase sem texto,
etiquetas brancas e figurinha de localização) — docs/padrao_visual.md §4.2.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from agente import design
from agente.arte_base import (
    Contexto,
    _altura_pilula,
    _cartao,
    _fundo,
    _melhor_faixa,
    _pilula,
    _quebrar,
    _selo_ilustrativa,
    _visto,
    altura_marca,
    estruturar_slide,
    marca_no_topo,
    fonte,
    separar_telefone,
)

BRANCO = (255, 255, 255)
GRAFITE = (20, 20, 24)
PAD_X, PAD_Y = 26, 12
MAX_LINHAS_TITULO = 3


def _ajustar_etiqueta(d, texto: str, largura: int, maximo: int, minimo: int, max_linhas: int = MAX_LINHAS_TITULO):
    for tam in range(maximo, minimo - 1, -2):
        f = fonte("bold", tam)
        linhas = _quebrar(d, texto, f, largura - 2 * PAD_X)
        if len(linhas) <= max_linhas and all(d.textlength(l, font=f) <= largura - 2 * PAD_X for l in linhas):
            return f, linhas
    return fonte("bold", minimo), _quebrar(d, texto, fonte("bold", minimo), largura - 2 * PAD_X)


def _altura_linha(f) -> int:
    return int(f.size * 1.22) + 2 * PAD_Y


def etiquetas(img, c: Contexto, papel: str, linhas: list[str], f, cx: int, y: int, *, fundo=BRANCO, cor=GRAFITE) -> int:
    """Uma pílula por linha, centralizadas em cx (como o texto com fundo do Instagram). Retorna a altura."""
    d = ImageDraw.Draw(img)
    lh = _altura_linha(f)
    caixas = []
    for i, l in enumerate(linhas):
        tw = d.textlength(l, font=f)
        caixas.append((int(cx - tw / 2 - PAD_X), y + i * (lh - 4), int(cx + tw / 2 + PAD_X), y + i * (lh - 4) + lh))
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    for cx0 in caixas:
        dc.rounded_rectangle(cx0, radius=int(lh * 0.32), fill=tuple(fundo) + (255,))
    img.alpha_composite(camada)
    d = ImageDraw.Draw(img)
    topo_glifo = d.textbbox((0, 0), "ÁHgy", font=f)
    alt_glifo = topo_glifo[3] - topo_glifo[1]
    for (x0, y0, x1, y1), l in zip(caixas, linhas):
        d.text((x0 + PAD_X, y0 + (lh - alt_glifo) / 2 - topo_glifo[1]), l, font=f, fill=cor)
    uniao = (min(b[0] for b in caixas), caixas[0][1], max(b[2] for b in caixas), caixas[-1][3])
    c.registrar(papel, uniao, tamanho=f.size, cor=cor, fundo=fundo, texto=" ".join(linhas))
    return uniao[3] - uniao[1]


def _pino(d: ImageDraw.ImageDraw, x: int, cy: int, r: int, cor) -> None:
    """Alfinete de localização desenhado (círculo + ponta)."""
    d.polygon(((x, cy - r * 0.2), (x + 2 * r, cy - r * 0.2), (x + r, cy + r * 1.5)), fill=cor)
    d.ellipse((x, cy - r * 1.1, x + 2 * r, cy + r * 0.9), fill=cor)
    d.ellipse((x + r * 0.55, cy - r * 0.65, x + r * 1.45, cy + r * 0.25), fill=BRANCO)


def etiqueta_local(img, c: Contexto, texto: str, cx: int, y: int, tam: int = 32) -> int:
    """Figurinha de localização: pílula branca com alfinete na cor de destaque. Retorna a altura."""
    d = ImageDraw.Draw(img)
    f = fonte("bold", tam)
    r = tam // 3
    tw = d.textlength(texto, font=f)
    largura = tw + 2 * r + 12 + 2 * PAD_X
    lh = _altura_linha(f)
    x0 = int(cx - largura / 2)
    _cartao(img, (x0, y, x0 + largura, y + lh), BRANCO, alfa=255, raio=lh // 2)
    d = ImageDraw.Draw(img)
    _pino(d, x0 + PAD_X, y + lh // 2, r, c.paleta.destaque)
    caixa_txt = d.textbbox((0, 0), "ÁHgy", font=f)
    d.text((x0 + PAD_X + 2 * r + 12, y + (lh - (caixa_txt[3] - caixa_txt[1])) / 2 - caixa_txt[1]), texto, font=f, fill=GRAFITE)
    c.registrar("local", (x0, y, x0 + largura, y + lh), tamanho=tam, cor=GRAFITE, fundo=BRANCO, texto=texto)
    return lh


def _local(c: Contexto) -> str | None:
    return (c.negocio.get("cidade_regiao_atendimento") or "").strip() or None


def capa_nativa(c: Contexto, titulo: str, cta: str | None, imagem: Path | None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, imagem)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    cx = esq + largura // 2
    y_base = h - base

    local = _local(c)
    alt_local = _altura_linha(fonte("bold", 32)) if local else 0
    y_min = top + altura_marca(28, True) + 36            # abaixo da marca
    y_max = y_base - ((_altura_pilula(44) + 40) if cta else 40)

    # Título (e localização logo abaixo) na maior faixa livre da foto, diminuindo a etiqueta até caber;
    # se não couberem juntos, a localização desce para perto do CTA.
    # Sem faixa livre, as etiquetas ficam no topo no tamanho máximo (têm fundo próprio).
    escolha = None
    if imagem:
        for com_local in ((True, False) if local else (False,)):
            for tam in range(design.ETIQUETA_MAX, design.ETIQUETA_MIN - 1, -4):
                f, linhas = _ajustar_etiqueta(d, titulo, largura, tam, tam)
                if len(linhas) > MAX_LINHAS_TITULO:
                    continue
                alt_titulo = len(linhas) * (_altura_linha(f) - 4) + 4
                bloco = alt_titulo + ((alt_local + 22) if com_local else 0)
                if faixa := _melhor_faixa(img, y_min, y_max, esq, w - dir_, altura_min=bloco + 40):
                    escolha = (f, linhas, alt_titulo, faixa, local and not com_local)
                    break
            if escolha:
                break
    if escolha:
        f, linhas, alt_titulo, faixa, local_embaixo = escolha
    else:
        f, linhas = _ajustar_etiqueta(d, titulo, largura, design.ETIQUETA_MAX, design.ETIQUETA_MIN)
        alt_titulo, faixa, local_embaixo = len(linhas) * (_altura_linha(f) - 4) + 4, None, bool(local and imagem)
    bloco = alt_titulo + (0 if local_embaixo or not local else alt_local + 22)
    y0, y1 = faixa or (y_min, y_min + bloco + 80)
    y = y0 + max(0, int((y1 - y0 - bloco) * 0.35))

    y += etiquetas(img, c, "titulo", linhas, f, cx, y)
    if local:
        etiqueta_local(img, c, local, cx, (y_max - alt_local - 24) if local_embaixo else y + 22)

    marca_no_topo(img, c, esq, top, selo=True, tam=28)
    if cta:
        _pilula(img, cta, cx, y_base, largura, c.paleta, tam=44, c=c, centro=True)
    if c.fundo_ia and c.selo and imagem:
        _selo_ilustrativa(img, w - dir_, min(h - 12, y_base + 52) if cta else y_base, c=c)
    return img


def _fundo_sequencia(c: Contexto, imagem: Path | None) -> Image.Image:
    """Stories seguintes: a mesma foto desfocada e escurecida (a sequência parece uma coisa só)."""
    if not imagem:
        return _fundo(c.tamanho, c.paleta, None)
    base = _fundo(c.tamanho, c.paleta, imagem).filter(ImageFilter.GaussianBlur(30))
    base.alpha_composite(Image.new("RGBA", base.size, (10, 10, 14, 150)))
    return base


def _itens_em_etiquetas(img, c: Contexto, tipo: str, itens: list[str], x: int, y_min: int, y_max: int, largura: int) -> None:
    d = ImageDraw.Draw(img)
    for tam in range(56, 39, -2):
        f = fonte("bold", tam)
        icone = int(tam * 0.95)
        livre = largura - 2 * PAD_X - icone - 18
        blocos = [_quebrar(d, it, f, livre) for it in itens]
        alturas = [max(len(b) * int(tam * 1.2), icone) + 2 * PAD_Y + 6 for b in blocos]
        vao = int(tam * 0.4)
        total = sum(alturas) + vao * (len(itens) - 1)
        if total <= y_max - y_min and all(len(b) == 1 for b in blocos):
            break
    y = y_min + max(0, int((y_max - y_min - total) * 0.42))
    for i, (linhas, alt) in enumerate(zip(blocos, alturas), 1):
        tw = max(d.textlength(l, font=f) for l in linhas)
        caixa = (x, y, int(x + 2 * PAD_X + icone + 18 + tw), y + alt)
        _cartao(img, caixa, BRANCO, alfa=255, raio=min(alt // 2, 36))
        d = ImageDraw.Draw(img)
        r = icone // 2
        cy = y + alt // 2
        d.ellipse((x + PAD_X, cy - r, x + PAD_X + icone, cy + r), fill=c.paleta.destaque)
        if tipo == "etapas":
            fn = fonte("bold", int(icone * 0.55))
            n = str(i)
            d.text((x + PAD_X + r - d.textlength(n, font=fn) / 2, cy - fn.size * 0.62), n, font=fn, fill=c.paleta.texto_sobre_destaque)
        else:
            _visto(d, x + PAD_X, cy, r, c.paleta.texto_sobre_destaque)
        bb = d.textbbox((0, 0), "ÁHgy", font=f)
        passo = int(f.size * 1.2)
        y_txt = y + (alt - len(linhas) * passo) / 2 + (passo - (bb[3] - bb[1])) / 2 - bb[1]
        for j, l in enumerate(linhas):
            d.text((x + PAD_X + icone + 18, y_txt + j * passo), l, font=f, fill=GRAFITE)
        c.registrar("item", caixa, tamanho=f.size, cor=GRAFITE, fundo=BRANCO, texto=" ".join(linhas))
        y += alt + vao


def slide_nativo(c: Contexto, numero: int, total: int, texto: str, final: bool = False, cta: str | None = None,
                 imagem: Path | None = None) -> Image.Image:
    img = _fundo_sequencia(c, imagem)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    cx = esq + largura // 2
    y_min, y_max = top + altura_marca(28, True) + 40, h - base - 30

    botao = None
    if final:
        texto, botao = separar_telefone(texto or "", c.negocio)
        botao = botao or cta
    alt_botao = (_altura_pilula(48) + 48) if botao else 0

    tipo, itens = estruturar_slide(texto, final)
    if tipo == "paragrafo":
        f, linhas = _ajustar_etiqueta(d, itens[0], largura, 60, design.ETIQUETA_MIN, 4) if itens and itens[0] else (None, [])
        alt = (len(linhas) * (_altura_linha(f) - 4) + 4) if linhas else 0
        y = y_min + max(0, int((y_max - y_min - alt - alt_botao) * 0.42))
        if linhas:
            y += etiquetas(img, c, "corpo", linhas, f, cx, y)
        if botao:
            _pilula(img, botao, cx, y + alt_botao, largura, c.paleta, tam=48, c=c, centro=True)
    else:
        _itens_em_etiquetas(img, c, tipo, itens, esq, y_min, y_max - alt_botao, largura)
        if botao:
            _pilula(img, botao, cx, y_max, largura, c.paleta, tam=48, c=c, centro=True)

    marca_no_topo(img, c, esq, top, selo=True, tam=28)
    return img
