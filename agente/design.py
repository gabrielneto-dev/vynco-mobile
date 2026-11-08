"""Tokens do padrão visual da Vynco (docs/padrao_visual.md).

Fonte única para quem desenha (arte_*.py) e para quem confere (validacao_design.py):
mudar um número aqui muda a arte e a validação juntas.
"""

from __future__ import annotations

from pathlib import Path

from agente.schemas import Formato, Frente

# ---------------------------------------------------------------------- tipografia
DIR_FONTES = Path(__file__).resolve().parent / "fontes"
ARQUIVOS_FONTE = {  # Inter (OFL) — mesma tipografia em Linux e Windows
    "regular": "Inter-Regular.ttf",
    "bold": "Inter-Bold.ttf",
    "black": "Inter-ExtraBold.ttf",
}
TITULO_MAX = {"vertical": 92, "feed": 84}   # px, arte de 1080 de largura
TITULO_MIN = 56
ETIQUETA_MAX, ETIQUETA_MIN = 64, TITULO_MIN  # título em etiqueta (estilo nativo); nunca abaixo do mínimo de título
CORPO_MIN = 30
RODAPE_MIN = 22
ALTURA_MAIUSCULA = 0.727                    # altura da maiúscula da Inter / tamanho da fonte

# ---------------------------------------------------------------------- medidas
TAMANHOS = {"4:5": (1080, 1350), "1:1": (1080, 1080), "9:16": (1080, 1920)}
# Margens seguras (topo, direita, base, esquerda) em px.
# Stories/Reels seguem o diagrama de anúncios da Meta (2026): 14% topo, 6% laterais;
# base de 35% no Reels; no Stories orgânico 20% (as fontes divergem; conferir no Gerenciador antes de impulsionar).
ZONAS = {
    "4:5": (80, 80, 80, 80),
    "1:1": (80, 80, 80, 80),
    "stories": (269, 80, 384, 80),
    "reel": (269, 150, 672, 80),   # direita livre para os botões do Reels
}

# ---------------------------------------------------------------------- limites do padrão
PALAVRAS_TITULO = 7
ITENS_POR_SLIDE = 4
PALAVRAS_POR_ITEM = 5
AREA_TEXTO_MAX = 0.30
CONTRASTE_CORPO = 4.5
CONTRASTE_TITULO = 3.0
HIERARQUIA_MIN = 1.6          # título ≥ 1,6× o corpo
LARGURA_MINIATURA = 375       # largura do feed no celular (px CSS)
ALTURA_LETRA_MINIATURA = 14   # altura mínima da maiúscula do título na miniatura
TEXTO_GRANDE_PX = 53          # ≥ isso (bold, em 1080) conta como "texto grande" para contraste

# ---------------------------------------------------------------------- estilos
ESTILOS = ("editorial", "nativo", "oferta")
DESCRICAO_ESTILO = {
    "editorial": "Editorial (carrossel/capa da marca, base iPlace)",
    "nativo": "Nativo (cara de post: foto cheia + etiquetas, base Biblioteca de Anúncios)",
    "oferta": "Oferta (ficha da unidade: modelo, GB, selos e preço confirmados)",
}


def estilo_padrao(formato: Formato, frente: Frente, produto_id: str | None) -> str:
    """Estilo esperado pelo padrão para a peça (docs/padrao_visual.md, seção 2)."""
    if frente == Frente.venda and produto_id and formato in (Formato.imagem, Formato.anuncio):
        return "oferta"
    if formato in (Formato.stories, Formato.anuncio):
        return "nativo"
    return "editorial"


# ---------------------------------------------------------------------- cor
def _canal(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminancia_relativa(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_canal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Razão de contraste WCAG 2.x (1 a 21)."""
    la, lb = sorted((luminancia_relativa(a), luminancia_relativa(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
