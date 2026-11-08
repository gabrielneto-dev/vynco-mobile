"""Estilo oferta: ficha de uma unidade real do estoque sobre a foto real dela — docs/padrao_visual.md §4.3.

Só entra o que está confirmado no estoque/cadastro: cada selo some se o dado for None.
Preço só com `preco_aprovado_brl`. Nunca usa imagem gerada (montar_arte garante foto real).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from agente.arte_base import Contexto, _cartao, _fundo, _media, _pilula, ajustar, escrever, fonte, marca_no_topo
from agente.schemas import Aparelho

BRANCO = (255, 255, 255)


def preco_brl(valor: float) -> str:
    inteiro = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + (inteiro[:-3] if inteiro.endswith(",00") else inteiro)


def selos_da_unidade(produto: Aparelho, negocio: dict) -> list[str]:
    """Até 3 selos, só com dados confirmados."""
    selos = []
    if produto.saude_bateria_pct:
        selos.append(f"Bateria {produto.saude_bateria_pct}%")
    garantia = produto.garantia or negocio.get("garantia_oferecida")
    if garantia and len(garantia) <= 22:
        selos.append(f"Garantia {garantia}" if not garantia.lower().startswith("garantia") else garantia)
    if produto.condicao and len(produto.condicao) <= 22:
        selos.append(produto.condicao[:1].upper() + produto.condicao[1:])
    return selos[:3]


def _degrade_base(img: Image.Image, inicio: float, alfa_max: int = 225) -> None:
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    y0 = int(img.height * inicio)
    for y in range(y0, img.height):
        t = (y - y0) / max(1, img.height - y0)
        d.line((0, y, img.width, y), fill=(8, 8, 12, int(alfa_max * min(1.0, t * 1.4))))
    img.alpha_composite(camada)


def capa_oferta(c: Contexto, produto: Aparelho, cta: str | None, imagem: Path | None) -> Image.Image:
    img = _fundo(c.tamanho, c.paleta, imagem)
    top, dir_, base, esq = c.zona
    w, h = c.tamanho
    largura = w - esq - dir_
    _degrade_base(img, 0.42)
    d = ImageDraw.Draw(img)

    y = h - base
    if cta:
        _, alt = _pilula(img, cta, esq, y, int(largura * 0.7), c.paleta, tam=40, c=c)
        y -= alt + 36
    if produto.preco_aprovado_brl:
        _, alt = _pilula(img, preco_brl(produto.preco_aprovado_brl), esq, y, largura, c.paleta, tam=56, c=c, papel="preco",
                         cor_fundo=BRANCO, cor_texto=(20, 20, 24))
        y -= alt + 30

    selos = selos_da_unidade(produto, c.negocio)
    if selos:
        f = fonte("bold", 30)
        x = esq
        alt = int(30 * 1.2) + 24
        for s in selos:
            tw = d.textlength(s, font=f)
            caixa = (x, y - alt, int(x + tw + 40), y)
            _cartao(img, caixa, (255, 255, 255), alfa=46, raio=alt // 2)
            fundo = _media(img, caixa)
            d = ImageDraw.Draw(img)
            d.text((x + 20, y - alt + 10), s, font=f, fill=BRANCO)
            c.registrar("item", caixa, tamanho=30, cor=BRANCO, fundo=fundo, texto=s)
            x = caixa[2] + 14
        y -= alt + 30

    if produto.armazenamento_gb:
        _, alt = _pilula(img, f"{produto.armazenamento_gb} GB", esq, y, 300, c.paleta, tam=34, c=c, papel="apoio")
        y -= alt + 18

    ft, linhas, at = ajustar(d, produto.modelo, largura, 260, "black", 112, 64, 1.05)
    escrever(c, img, "titulo", linhas, ft, esq, y - at, BRANCO, 1.05)

    marca_no_topo(img, c, esq, top, selo=True, tam=28)
    return img
