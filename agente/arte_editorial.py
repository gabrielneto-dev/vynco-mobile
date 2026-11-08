"""Estilo editorial (carrossel educativo e capa de feed orgânico), base @iplace — docs/padrao_visual.md §4.1."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

from agente import design
from agente.arte_base import (
    TITULO_MIN_FAIXA,
    Contexto,
    _altura_pilula,
    _barra_destaque,
    _cartao,
    _cor_legivel,
    _fundo,
    _marca,
    _melhor_faixa,
    _misturar,
    _pilula,
    _quebrar,
    _selo_ilustrativa,
    _seta,
    _veu,
    _visto,
    ajustar,
    altura_marca,
    marca_no_topo,
    escrever,
    estruturar_slide,
    fonte,
    separar_telefone,
)

RESPIRO_MARCA = 40     # entre a marca (topo) e o título
RESPIRO_OBJETO = 48    # entre o título e o aparelho na foto


def _bloco_titulo(d, titulo: str, apoio: str | None, largura: int, altura: int, tam_max: int):
    """Ajusta título (+ apoio) à caixa. Retorna (ft, lt, at, fa, la, aa) com a altura total em at + aa."""
    vao = 24 if apoio else 0
    ft, lt, at = ajustar(d, titulo, largura, int(altura * (0.66 if apoio else 1.0)), "black", tam_max, 44)
    fa = la = None
    aa = 0
    if apoio:
        fa, la, aa = ajustar(d, apoio, largura, max(60, altura - at - vao), "regular", 42, design.CORPO_MIN, 1.25)
        aa += vao
    return ft, lt, at, fa, la, aa


def _numeral_em_destaque(titulo: str, paleta) -> dict | None:
    """'3 erros ao comprar…' → o '3' sai na cor de destaque (padrão de listas da iPlace)."""
    return {0: paleta.destaque} if re.match(r"^\d{1,2}\s", titulo) else None


def capa(c: Contexto, titulo: str, apoio: str | None, cta: str | None, imagem: Path | None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, imagem)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    tam_max = design.TITULO_MAX["vertical" if w / h < 0.7 else "feed"]
    y_base = h - base
    rodape = (_altura_pilula(40) if cta else 40) + 48     # CTA (ou selo) + respiro
    y_topo = top + altura_marca(30, bool(imagem)) + RESPIRO_MARCA   # abaixo da marca
    y_lim = y_base - rodape

    cor_texto, cor_veu, alfa_veu, faixa = c.paleta.texto, c.paleta.fundo, 0, None
    if imagem:
        # Título na maior faixa livre da foto (sem cobrir o aparelho); sem faixa livre, no topo com véu forte.
        faixa = _melhor_faixa(img, y_topo, y_lim, esq, w - dir_, altura_min=int(h * 0.13))
        if faixa and _bloco_titulo(d, titulo, apoio, largura, faixa[1] - faixa[0] - 48, tam_max)[0].size < TITULO_MIN_FAIXA:
            faixa = None  # faixa livre estreita demais: título miúdo é pior que um véu sobre a foto
        if faixa:  # a faixa termina onde começa o aparelho: deixa um respiro
            faixa = (faixa[0], faixa[1] - RESPIRO_OBJETO if faixa[1] < y_lim else faixa[1])
        y0, y1 = faixa or (y_topo, y_topo + int((y_lim - y_topo) * 0.5))
        alfa_veu = 150 if faixa else 225
    else:
        y0, y1 = y_topo, y_lim
    ft, lt, at, fa, la, aa = _bloco_titulo(d, titulo, apoio, largura, y1 - y0 - 48, tam_max)
    bloco = 36 + at + aa                                  # barra de destaque + título + apoio
    y = y0 + max(0, int((y1 - y0 - bloco) * (0.35 if imagem else 0.38)))
    if imagem:
        cor_texto, cor_veu = _cor_legivel(img, (esq, y, w - dir_, y + bloco), c.paleta)
        # Na faixa livre o véu não passa dela (não encosta no aparelho); sem faixa, cobre o topo inteiro.
        v0, v1 = (max(y0, y - 70), min(y1, y + bloco + 70)) if faixa else (0, y + bloco + 90)
        _veu(img, v0, v1, cor_veu, alfa_veu)
    _barra_destaque(img, esq, y, c.paleta)
    y += 36
    y += escrever(c, img, "titulo", lt, ft, esq, y, cor_texto, destaque=_numeral_em_destaque(titulo, c.paleta))
    if apoio:
        escrever(c, img, "apoio", la, fa, esq, y + 24, cor_texto, 1.25)

    # Marca pequena no topo à esquerda; CTA à esquerda na base e selo de imagem ilustrativa à direita.
    marca_no_topo(img, c, esq, top, selo=bool(imagem), tam=30)
    if cta:
        _pilula(img, cta, esq, y_base, int(largura * 0.68), c.paleta, c=c)
    if c.fundo_ia and c.selo and imagem:
        _selo_ilustrativa(img, w - dir_, y_base, c=c)
    return img


def _ajustar_itens(d, itens: list[str], largura: int, altura: int, maximo: int = 76, minimo: int = 40):
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


def desenhar_itens(img, c: Contexto, tipo: str, itens: list[str], x: int, y_min: int, y_max: int, largura: int, *,
                   barra: bool, cor_texto=None, cor_linha=None) -> None:
    """Lista com ✓ ou etapas numeradas ligadas por uma linha, centralizadas no espaço vertical."""
    d = ImageDraw.Draw(img)
    cor_texto = cor_texto or c.paleta.texto
    topo = 56 if barra else 0  # barra de destaque logo acima da lista
    f, blocos, alturas, icone, vao = _ajustar_itens(d, itens, largura, y_max - y_min - topo)
    total = topo + sum(alturas) + vao * (len(itens) - 1)
    y = y_min + max(0, int((y_max - y_min - total) * 0.42))
    if barra:
        _barra_destaque(img, x, y, c.paleta)
        y += topo
    recuo = icone + int(f.size * 0.55)
    linha_cor = cor_linha or _misturar(c.paleta.destaque, c.paleta.fundo, 0.6)
    centros = []
    for linhas, alt in zip(blocos, alturas):
        centros.append(y + int(f.size * 1.18) // 2)  # ícone alinhado à primeira linha do item
        escrever(c, img, "item", linhas, f, x + recuo, y, cor_texto)
        y += alt + vao
    d = ImageDraw.Draw(img)
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
        else:
            _visto(d, x, cy, r, cor)


def slide_texto(c: Contexto, numero: int, total: int, texto: str, final: bool = False, cta: str | None = None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, None)
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_

    if c.paginacao and not final:
        f_num = fonte("black", 96)
        escrever(c, img, "numero", [f"{numero:02d}"], f_num, esq, top, c.paleta.destaque)
        y_min = top + 150
    else:
        y_min = top + 20
    y_max = h - base - 110  # acima do rodapé

    # Último slide: o telefone sai do texto e vira o botão de destaque.
    botao = None
    if final:
        texto, botao = separar_telefone(texto or "", c.negocio)
        botao = botao or cta
    alt_botao = (_altura_pilula(48) + 56) if botao else 0

    tipo, itens = estruturar_slide(texto, final)
    if tipo == "paragrafo":
        tam_max = 84 if final else 76
        f, linhas, alt = ajustar(d, itens[0], largura, y_max - y_min - alt_botao - 36, "bold", tam_max, 40, 1.2) if itens else (None, [], 0)
        bloco = 36 + alt + alt_botao
        y = y_min + max(0, int((y_max - y_min - bloco) * 0.42))
        if not c.paginacao or final:
            _barra_destaque(img, esq, y, c.paleta)
        y += 36
        if linhas:
            y += escrever(c, img, "corpo", linhas, f, esq, y, c.paleta.texto, 1.2)
        if botao:
            _pilula(img, botao, esq, y + alt_botao, largura, c.paleta, tam=48, c=c)
    else:
        desenhar_itens(img, c, tipo, itens, esq, y_min, y_max - alt_botao, largura, barra=not c.paginacao)
        if botao:
            _pilula(img, botao, esq, y_max, largura, c.paleta, tam=48, c=c)

    _marca(img, c.negocio, c.cfg, esq, h - base, c.paleta, c=c)
    if c.paginacao:
        f_rod = fonte("regular", 28)
        rodape = f"{numero}/{total}" + ("   arraste" if not final else "")
        d = ImageDraw.Draw(img)
        x_seta = w - dir_ - (22 if not final else 0)
        x = x_seta - d.textlength(rodape, font=f_rod) - (10 if not final else 0)
        escrever(c, img, "rodape", [rodape], f_rod, x, h - base - 36, c.paleta.texto)
        if not final:
            _seta(ImageDraw.Draw(img), x_seta, h - base - 36 + 18, c.paleta.texto, 20)
    return img


def cartela_reel(c: Contexto, texto: str) -> Image.Image:
    """PNG transparente para sobrepor no vídeo (texto dentro da zona segura do Reels)."""
    img = Image.new("RGBA", c.tamanho, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    pad = 36
    f, linhas, alt = ajustar(d, texto, largura - 2 * pad, int((h - top - base) * 0.6), "bold", 72, 40)
    y = top + int((h - top - base - alt - 2 * pad) * 0.35)
    _cartao(img, (esq, y, esq + largura, y + alt + 2 * pad), c.paleta.fundo, alfa=245)
    largura_txt = max(ImageDraw.Draw(img).textlength(l, font=f) for l in linhas)
    escrever(None, img, "corpo", linhas, f, esq + pad, y + pad, c.paleta.texto)
    c.registrar("corpo", (esq + pad, y + pad, esq + pad + largura_txt, y + pad + alt), tamanho=f.size,
                cor=c.paleta.texto, fundo=c.paleta.fundo, texto=" ".join(linhas))
    return img
