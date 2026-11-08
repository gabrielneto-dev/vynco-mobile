"""Confere uma arte montada contra o padrão visual (docs/padrao_visual.md §6). Grátis, local.

Lê `arte.json` (com o registro de layout de cada página) e os PNGs da pasta da arte e grava
`validacao.json` + `validacao.md`. Falha não bloqueia: a decisão de publicar continua humana.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from agente import design
from agente.schemas import Formato, Frente

OK, AVISO, FALHA = "ok", "aviso", "falha"
TEXTO = {"titulo", "apoio", "corpo", "item", "numero", "cta", "preco", "etiqueta", "local", "rodape", "marca", "selo"}
FORA_DA_ZONA_PERMITIDO = {"selo"}        # selo de transparência pode ficar na margem
MIN_POR_PAPEL = {"titulo": design.TITULO_MIN, "corpo": design.CORPO_MIN, "item": design.CORPO_MIN, "apoio": design.CORPO_MIN,
                 "cta": design.CORPO_MIN, "preco": design.CORPO_MIN, "local": design.CORPO_MIN,
                 "rodape": design.RODAPE_MIN, "selo": design.RODAPE_MIN, "marca": design.RODAPE_MIN}
INVASAO_AVISO, INVASAO_FALHA = 16, 40   # px de texto sobre o objeto principal da foto
REGRAS = {
    "tamanho": "Tamanho do canvas",
    "zona": "Zona segura",
    "contraste": "Contraste",
    "fonte_minima": "Fonte mínima",
    "miniatura": "Legível em miniatura",
    "quantidade_texto": "Quantidade de texto",
    "hierarquia": "Hierarquia",
    "aparelho": "Aparelho não coberto",
    "marca": "Marca e transparência",
    "estilo": "Coerência de estilo",
}


@dataclass
class Achado:
    regra: str
    nivel: str
    mensagem: str
    pagina: str = ""


@dataclass
class Relatorio:
    pasta: str
    estilo: str
    achados: list[Achado] = field(default_factory=list)

    @property
    def falhas(self) -> list[Achado]:
        return [a for a in self.achados if a.nivel == FALHA]

    @property
    def avisos(self) -> list[Achado]:
        return [a for a in self.achados if a.nivel == AVISO]

    @property
    def aprovado(self) -> bool:
        return not self.falhas

    def resumo(self) -> str:
        return f"{len(self.falhas)} falha(s), {len(self.avisos)} aviso(s)"

    def por_regra(self) -> dict[str, str]:
        """Pior nível por regra (para a tabela-resumo)."""
        ordem = {OK: 0, AVISO: 1, FALHA: 2}
        pior = {r: OK for r in REGRAS}
        for a in self.achados:
            if ordem[a.nivel] > ordem[pior.get(a.regra, OK)]:
                pior[a.regra] = a.nivel
        return pior


# ---------------------------------------------------------------------- utilidades
def _palavras(t: str) -> int:
    return len(re.findall(r"[\wÀ-ÿ%$]+", t or ""))


def _dentro(caixa, zona_px) -> bool:
    x0, y0, x1, y1 = caixa
    zx0, zy0, zx1, zy1 = zona_px
    folga = 2
    return x0 >= zx0 - folga and y0 >= zy0 - folga and x1 <= zx1 + folga and y1 <= zy1 + folga


def _area(caixa) -> int:
    x0, y0, x1, y1 = caixa
    return max(0, x1 - x0) * max(0, y1 - y0)


def mascara_objeto(foto: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int] | None]:
    """Caixa do objeto principal num fundo liso (bordas fortes), em px da arte. None se não houver."""
    e = 8
    p = foto.convert("L").resize((max(1, foto.width // e), max(1, foto.height // e)), Image.BILINEAR)
    p = p.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    p = p.crop((2, 2, p.width - 2, p.height - 2)).point(lambda v: 255 if v > 28 else 0)
    caixa = p.getbbox()
    if not caixa:
        return p, None
    x0, y0, x1, y1 = caixa
    return p, ((x0 + 2) * e, (y0 + 2) * e, (x1 + 2) * e, (y1 + 2) * e)


# ---------------------------------------------------------------------- regras
def _regras_pagina(meta: dict, nome: str, img: Image.Image, elementos: list[dict], foto: Image.Image | None) -> list[Achado]:
    achados: list[Achado] = []
    A = lambda regra, nivel, msg: achados.append(Achado(regra, nivel, msg, nome))  # noqa: E731
    w, h = img.size
    esperado = design.TAMANHOS[meta["proporcao"]]

    # 1. Tamanho
    if (w, h) != tuple(esperado):
        A("tamanho", FALHA, f"{w}×{h}; o formato pede {esperado[0]}×{esperado[1]}.")

    # 2. Zona segura
    top, dir_, base, esq = meta["zona"]
    zona_px = (esq, top, w - dir_, h - base)
    for e in elementos:
        if e["papel"] in FORA_DA_ZONA_PERMITIDO:
            if not _dentro(e["caixa"], (0, 0, w, h)):
                A("zona", FALHA, f"{e['papel']} sai da arte.")
            continue
        if not _dentro(e["caixa"], zona_px):
            A("zona", FALHA, f"{e['papel']} '{e['texto'][:30]}' fora da área segura {zona_px}.")

    textos = [e for e in elementos if e["papel"] in TEXTO and e.get("tamanho")]
    # 3. Contraste
    for e in textos:
        if not (e.get("cor") and e.get("fundo")):
            continue
        razao = design.contraste(tuple(e["cor"]), tuple(e["fundo"]))
        grande = e["tamanho"] >= design.TEXTO_GRANDE_PX
        minimo = design.CONTRASTE_TITULO if grande else design.CONTRASTE_CORPO
        if razao < minimo:
            A("contraste", FALHA if razao < minimo * 0.8 else AVISO,
              f"{e['papel']} '{e['texto'][:30]}': contraste {razao:.1f}:1 (mínimo {minimo}:1).")

    # 4. Fonte mínima
    for e in textos:
        minimo = MIN_POR_PAPEL.get(e["papel"])
        if minimo and e["tamanho"] < minimo:
            A("fonte_minima", FALHA, f"{e['papel']} '{e['texto'][:30]}' em {e['tamanho']} px (mínimo {minimo} px).")

    # 5. Miniatura (título reduzido à largura do feed no celular)
    titulos = [e for e in textos if e["papel"] == "titulo"]
    for e in titulos:
        altura = e["tamanho"] * design.ALTURA_MAIUSCULA * design.LARGURA_MINIATURA / w
        if altura < design.ALTURA_LETRA_MINIATURA:
            A("miniatura", FALHA, f"Título com {altura:.0f} px de altura de letra no celular (mínimo {design.ALTURA_LETRA_MINIATURA}).")

    # 6. Quantidade de texto
    for e in titulos:
        n = _palavras(e["texto"])
        if n > design.PALAVRAS_TITULO:
            A("quantidade_texto", AVISO, f"Título com {n} palavras (padrão: até {design.PALAVRAS_TITULO}).")
    itens = [e for e in textos if e["papel"] == "item"]
    if len(itens) > design.ITENS_POR_SLIDE:
        A("quantidade_texto", AVISO, f"{len(itens)} itens no slide (padrão: até {design.ITENS_POR_SLIDE}).")
    for e in itens:
        n = _palavras(e["texto"])
        if n > design.PALAVRAS_POR_ITEM:
            A("quantidade_texto", AVISO, f"Item '{e['texto'][:30]}' com {n} palavras (padrão: até {design.PALAVRAS_POR_ITEM}).")
    area = sum(_area(e["caixa"]) for e in textos if e["papel"] not in ("marca", "selo", "rodape")) / (w * h)
    if area > design.AREA_TEXTO_MAX:
        A("quantidade_texto", AVISO, f"Texto ocupa {area:.0%} da arte (padrão: até {design.AREA_TEXTO_MAX:.0%}).")

    # 7. Hierarquia
    corpo = [e["tamanho"] for e in textos if e["papel"] in ("apoio", "corpo")]
    if titulos and corpo:
        razao = titulos[0]["tamanho"] / max(corpo)
        if razao < design.HIERARQUIA_MIN:
            A("hierarquia", AVISO, f"Título só {razao:.1f}× maior que o corpo (padrão: ≥ {design.HIERARQUIA_MIN}×).")

    # 8. Aparelho não coberto (só na capa com foto nítida)
    if foto is not None:
        mascara, objeto = mascara_objeto(foto)
        if objeto and _area(objeto) < 0.7 * w * h:   # fundo liso com um objeto: dá para medir
            ox0, oy0, ox1, oy1 = objeto
            for e in textos:
                if e["papel"] not in ("titulo", "apoio", "corpo", "local", "item"):
                    continue
                x0, y0, x1, y1 = e["caixa"]
                larg = max(0, min(x1, ox1) - max(x0, ox0))
                alt = max(0, min(y1, oy1) - max(y0, oy0))
                frac = larg * alt / max(1, _area(e["caixa"]))
                if frac > 0.35 or (larg and alt >= INVASAO_FALHA):
                    A("aparelho", FALHA, f"{e['papel']} '{e['texto'][:30]}' cobre o aparelho ({alt} px).")
                elif larg and alt >= INVASAO_AVISO:
                    A("aparelho", AVISO, f"{e['papel']} '{e['texto'][:30]}' invade {alt} px do aparelho.")
    return achados


def _regras_peca(meta: dict, paginas: list[dict]) -> list[Achado]:
    achados = []
    capa = paginas[0] if paginas else {"arquivo": "", "elementos": []}
    papeis_capa = {e["papel"] for e in capa["elementos"]}
    if "marca" not in {e["papel"] for p in paginas for e in p["elementos"]}:
        achados.append(Achado("marca", AVISO, "Nenhuma página tem a assinatura da loja (cadastre nome ou logo).", capa["arquivo"]))
    if meta["fundo"]["tipo"] == "ia" and "selo" not in papeis_capa:
        nivel = AVISO if not meta.get("selo_ativo", True) else FALHA
        achados.append(Achado("marca", nivel, "Fundo gerado por IA sem o selo 'Imagem ilustrativa'.", capa["arquivo"]))

    formato, frente = Formato(meta["formato"]), Frente(meta.get("frente", "marca"))
    esperado = design.estilo_padrao(formato, frente, meta.get("produto_id"))
    if meta["estilo"] != esperado:
        achados.append(Achado("estilo", AVISO, f"Estilo {meta['estilo']} numa peça em que o padrão é {esperado}.", ""))
    if frente == Frente.venda and meta.get("produto_id") and meta["fundo"]["tipo"] == "ia":
        achados.append(Achado("estilo", FALHA, "Unidade real à venda com imagem gerada.", ""))
    return achados


def _foto_da_capa(meta: dict) -> Image.Image | None:
    arq = meta["fundo"].get("arquivo")
    if not arq or not Path(arq).is_file():
        return None
    tamanho = design.TAMANHOS[meta["proporcao"]]
    return ImageOps.fit(Image.open(arq).convert("RGB"), tamanho, method=Image.LANCZOS, centering=(0.5, 0.5))


def validar_pasta(pasta: Path) -> Relatorio:
    pasta = Path(pasta)
    meta = json.loads((pasta / "arte.json").read_text(encoding="utf-8"))
    paginas = meta.get("paginas") or [{"arquivo": a, "elementos": []} for a in meta.get("arquivos", [])]
    rel = Relatorio(str(pasta), meta.get("estilo", "editorial"))
    foto = _foto_da_capa(meta)
    for i, p in enumerate(paginas):
        img = Image.open(pasta / p["arquivo"])
        capa_com_foto = foto if i == 0 and not p["arquivo"].endswith("cartela.png") else None
        rel.achados += _regras_pagina(meta, p["arquivo"], img, p["elementos"], capa_com_foto)
    rel.achados += _regras_peca(meta, paginas)
    _gravar(rel, pasta, meta)
    return rel


def _gravar(rel: Relatorio, pasta: Path, meta: dict) -> None:
    dados = {"estilo": rel.estilo, "aprovado": rel.aprovado, "resumo": rel.resumo(), "regras": rel.por_regra(),
             "achados": [asdict(a) for a in rel.achados]}
    (pasta / "validacao.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    simbolo = {OK: "✅", AVISO: "⚠️", FALHA: "❌"}
    linhas = [
        f"# Validação de design — {meta['peca']} ({meta['formato']}, estilo {rel.estilo})",
        "",
        f"**Resultado:** {'dentro do padrão' if rel.aprovado else 'fora do padrão'} — {rel.resumo()}.",
        "Padrão: `docs/padrao_visual.md`. Falha não bloqueia, mas deve ser corrigida antes de publicar.",
        "",
        "| Regra | Resultado |",
        "|---|---|",
        *[f"| {REGRAS[r]} | {simbolo[n]} {n} |" for r, n in rel.por_regra().items()],
    ]
    if rel.achados:
        linhas += ["", "## Detalhes", ""]
        linhas += [f"- {simbolo[a.nivel]} **{REGRAS[a.regra]}**{f' ({a.pagina})' if a.pagina else ''}: {a.mensagem}" for a in rel.achados]
    linhas += ["", "## Revisão humana (não automatizável)", "",
               "- Dá para entender a mensagem em 2 s, no celular?",
               "- O aparelho é do modelo certo, sem defeito inventado?",
               "- Parece da mesma marca das artes anteriores?"]
    (pasta / "validacao.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def validar_peca(ag, peca_id: str) -> Relatorio:
    """Valida a arte mais recente da peça."""
    artes = ag.registro.entrada(peca_id).get("artes") or []
    if not artes:
        raise ValueError(f"A peça {peca_id} ainda não tem arte montada (🧩 Montar arte final).")
    return validar_pasta(ag.registro.dir / artes[-1]["pasta"])
