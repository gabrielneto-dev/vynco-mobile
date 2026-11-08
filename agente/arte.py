"""Arte pronta para postar: compõe os PNGs finais (texto, CTA, marca) sobre a imagem de fundo.

Processamento local (Pillow), sem custo de API. Três estilos do padrão visual (docs/padrao_visual.md):
editorial (arte_editorial.py), nativo (arte_nativo.py) e oferta (arte_oferta.py). Regras do briefing embutidas:
  - [PENDENTE] nunca vai para a arte final (só em modo rascunho, com tarja);
  - peça de unidade real do estoque só usa foto real;
  - fundo gerado por IA recebe selo discreto "Imagem ilustrativa";
  - texto sempre dentro das zonas seguras (design.ZONAS); toda arte sai validada (validacao_design.py).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image

from agente import design
from agente.arte_base import (  # noqa: F401 — reexportados para quem importa de agente.arte
    PALETA_PROVISORIA,
    Contexto,
    ErroArte,
    Paleta,
    _quebrar,
    _tarja_rascunho,
    estruturar,
    faixas_livres,
    fonte,
    limpar,
)
from agente.arte_editorial import capa, cartela_reel, slide_texto
from agente.arte_nativo import capa_nativa, slide_nativo
from agente.arte_oferta import capa_oferta
from agente.cadastro import resolver_caminho
from agente.schemas import Brief, Formato, Frente

TAMANHOS = design.TAMANHOS
ZONAS = design.ZONAS
_RE_PENDENTE = re.compile(r"\[\s*PENDENTE[^\]]*\]", re.IGNORECASE)


# ---------------------------------------------------------------------- orquestração
@dataclass
class ResultadoArte:
    pasta: Path
    arquivos: list[Path]
    rascunho: bool
    fundo: str
    avisos: list[str] = field(default_factory=list)
    estilo: str = "editorial"
    validacao: object | None = None   # validacao_design.Relatorio


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


def _paginas(c: Contexto, estilo: str, formato: Formato, titulo: str, apoio: str | None, cta: str, cenas: list[str],
             imagem: Path | None, produto) -> list[tuple[str, Image.Image, list]]:
    """Desenha as páginas no estilo escolhido. Cada item: (arquivo, imagem, elementos do layout)."""
    saida: list[tuple[str, Image.Image, list]] = []

    def pagina(nome: str, desenhar) -> None:
        c.nova_pagina()
        img = desenhar()
        saida.append((nome, img, list(c.elementos)))

    def desenhar_capa(com_apoio: bool, com_cta: bool):
        if estilo == "oferta":
            return capa_oferta(c, produto, cta if com_cta else None, imagem)
        if estilo == "nativo":
            return capa_nativa(c, titulo, cta if com_cta else None, imagem)
        return capa(c, titulo, apoio if com_apoio else None, cta if com_cta else None, imagem)

    def desenhar_slide(i: int, total: int, texto: str, final: bool, cta_final: str | None):
        if estilo == "nativo":
            return slide_nativo(c, i, total, texto, final=final, cta=cta_final, imagem=imagem)
        return slide_texto(c, i, total, texto, final=final, cta=cta_final)

    if formato in (Formato.imagem, Formato.anuncio):
        pagina("01.png", lambda: desenhar_capa(True, True))
    elif formato in (Formato.carrossel, Formato.stories):
        internas = [t for t in cenas[1:] if t]
        ultima_e_cta = bool(internas) and _normalizar(cta)[:25] in _normalizar(internas[-1])
        total = 1 + len(internas) + (0 if ultima_e_cta else 1)
        pagina("01.png", lambda: desenhar_capa(False, False))
        for i, t in enumerate(internas, 2):
            final = ultima_e_cta and i == len(internas) + 1
            pagina(f"{i:02d}.png", lambda i=i, t=t, final=final: desenhar_slide(i, total, t, final, None))
        if not ultima_e_cta:
            pagina(f"{total:02d}.png", lambda: desenhar_slide(total, total, "", True, cta))
    elif formato == Formato.reel:
        pagina("00-capa.png", lambda: desenhar_capa(False, False))
        for i, t in enumerate(cenas, 1):
            if t:
                pagina(f"{i:02d}-cartela.png", lambda t=t: cartela_reel(c, t))
    return saida


def montar_arte(ag, peca_id: str, *, gancho: int = 1, rascunho: bool = False, fundo: str = "auto",
                estilo: str = "auto", validar: bool = True) -> ResultadoArte:
    peca, brief, _, doc = ag.registro.carregar_modelos(peca_id)
    negocio = ag.ctx.negocio
    if not 1 <= gancho <= len(peca.ganchos):
        raise ErroArte(f"Gancho {gancho} não existe (1 a {len(peca.ganchos)}).")
    titulo = limpar(peca.ganchos[gancho - 1])
    cta = limpar(peca.cta)
    cenas = [limpar(c.texto_tela) for c in sorted(peca.roteiro, key=lambda c: c.ordem)]
    imagem, tipo_fundo = escolher_fundo(ag, peca_id, brief, fundo)

    formato = brief.formato
    esperado = design.estilo_padrao(formato, brief.frente, brief.produto_id)
    estilo = esperado if estilo in ("auto", "", None) else estilo
    if estilo not in design.ESTILOS:
        raise ErroArte(f"Estilo {estilo!r} não existe. Use: auto, {', '.join(design.ESTILOS)}.")
    produto = ag.ctx.produto(brief.produto_id) if brief.produto_id else None
    if estilo == "oferta" and not (produto and tipo_fundo == "foto_real"):
        raise ErroArte("O estilo oferta é só para unidade real do estoque, com foto real (📱 Estoque).")

    if formato in (Formato.reel, Formato.stories):
        proporcao = "9:16"
    else:
        p = peca.direcao_arte.proporcao.strip().replace(" ", "")[:4]
        proporcao = p if p in TAMANHOS and p != "9:16" else "4:5"
    zona = ZONAS["reel" if formato == Formato.reel else "stories" if formato == Formato.stories else proporcao]

    # O que vai aparecer na arte (para checar pendências).
    apoio = None
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
    paginas = _paginas(c, estilo, formato, titulo, apoio, cta, cenas, imagem, produto)
    if rascunho:
        for _, img, _ in paginas:
            _tarja_rascunho(img)

    rotulo = f"v{doc['versao']}-g{gancho}-{estilo}-{tipo_fundo}" + ("-rascunho" if rascunho else "")
    pasta = ag.registro.dir_peca(peca_id) / "arte" / rotulo
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.png"):
        antigo.unlink()
    arquivos = []
    for nome, img, _ in paginas:
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
        "frente": brief.frente.value,
        "produto_id": brief.produto_id,
        "estilo": estilo,
        "estilo_esperado": esperado,
        "proporcao": proporcao,
        "zona": list(zona),
        "titulo": titulo,
        "gancho": gancho,
        "cta": cta,
        "fundo": {"tipo": tipo_fundo, "arquivo": str(imagem) if imagem else None},
        "selo_ativo": c.selo,
        "rascunho": rascunho,
        "pendencias": pend,
        "arquivos": [a.name for a in arquivos],
        "paginas": [{"arquivo": nome, "elementos": [e.como_dict() for e in els]} for nome, _, els in paginas],
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    (pasta / "arte.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    ag.registro.registrar_arte(peca_id, pasta, rascunho=rascunho)

    relatorio = None
    if validar:
        from agente.validacao_design import validar_pasta

        relatorio = validar_pasta(pasta)
        if relatorio.falhas or relatorio.avisos:
            avisos.append(f"Padrão visual: {relatorio.resumo()} — detalhes em validacao.md.")
    return ResultadoArte(pasta, arquivos, rascunho, tipo_fundo, avisos, estilo, relatorio)
