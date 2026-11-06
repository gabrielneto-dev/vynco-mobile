"""Exporta peças, calendários, revisões e análises em Markdown legível para o responsável."""

from __future__ import annotations

from collections import Counter

from agente.guardrails import Achado, Nivel
from agente.schemas import PESO_PILAR, Analise, Brief, Calendario, Peca, Pilar, Revisao

ICONE = {Nivel.bloqueio: "⛔", Nivel.revisao_humana: "🟡", Nivel.aviso: "ℹ️"}
ROTULO_FONTE = {"fato_confirmado": "✅ fato confirmado", "hipotese_criativa": "💡 hipótese criativa", "informacao_pendente": "⏳ pendente"}


def _achados_md(achados: list[Achado]) -> list[str]:
    if not achados:
        return ["Nenhum ponto encontrado pelas verificações automáticas."]
    linhas = []
    for a in achados:
        trecho = f" — _“{a.trecho}”_" if a.trecho else ""
        linhas.append(f"- {ICONE[a.nivel]} **{a.nivel.value}** `{a.regra}`: {a.mensagem}{trecho}")
    return linhas


def peca_md(peca_id: str, versao: int, peca: Peca, brief: Brief, achados: list[Achado], modelo: str) -> str:
    L = [
        f"# {peca.titulo_interno}",
        "",
        f"**ID:** {peca_id} · **Versão:** v{versao} · **Modelo:** {modelo}",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Pilar | {brief.pilar.value} |",
        f"| Frente | {brief.frente.value} |",
        f"| Formato | {brief.formato.value} |",
        f"| Público | {brief.publico.value} |",
        f"| Etapa | {brief.etapa.value} |",
        f"| Produto | {brief.produto_id or '—'} |",
        "",
        "> ⚠️ Conteúdo gerado por IA. Publicação somente após aprovação humana.",
        "",
        "## 1. Objetivo",
        peca.objetivo,
        "",
        "## 2. Público e objeção/interesse",
        peca.objecao_ou_interesse,
        "",
        "## 3. Ideia central",
        peca.ideia_central,
        "",
        f"**Justificativa:** {peca.justificativa_estrategica}",
        "",
        "## 4. Ganchos",
        *[f"{i}. {g}" for i, g in enumerate(peca.ganchos, 1)],
        "",
        "## 5. Copy, legenda e CTA",
        "**Copy principal**",
        "",
        peca.copy_principal,
        "",
        "**Legenda**",
        "",
        peca.legenda,
        "",
        f"**CTA:** {peca.cta}",
        "",
        "## 6. Roteiro / slides",
    ]
    for c in peca.roteiro:
        dur = f" ({c.duracao_s:g}s)" if c.duracao_s else ""
        L.append(f"**{c.ordem}.{dur}** {c.visual}")
        if c.texto_tela:
            L.append(f"   - Texto na tela: {c.texto_tela}")
        if c.narracao:
            L.append(f"   - Narração: {c.narracao}")
    d = peca.direcao_arte
    L += [
        "",
        "## 7. Direção de arte",
        f"- **Proporção:** {d.proporcao} · **Dimensões:** {d.dimensoes_px}",
        f"- **Hierarquia:** {d.hierarquia}",
        f"- **Paleta:** {d.paleta}",
        f"- **Tipografia:** {d.tipografia}",
        f"- **Zonas seguras:** {d.zonas_seguras}",
        f"- **Fonte das imagens:** {d.fonte_imagens}",
        "- **Elementos:**",
        *[f"  - {e}" for e in d.elementos_visuais],
        "",
        "## 8. Prompt de imagem",
        f"```\n{peca.prompt_imagem}\n```" if peca.prompt_imagem else "_Sem prompt: esta peça exige foto real._",
        "",
        "## 9. Variações para teste",
    ]
    for v in peca.variacoes:
        L += [f"### {v.nome} — eixo: {v.eixo}", f"- **Hipótese:** {v.hipotese}", f"- **Gancho:** {v.gancho}", f"- **Copy:** {v.texto}", ""]
    L += ["## 10. Checklist de validação humana"]
    L += [f"- [ ] **{i.campo}** — {i.motivo} ({ROTULO_FONTE.get(i.status.value, i.status.value)})" for i in peca.checklist_validacao]
    L += ["", "### Afirmações da peça"]
    L += [f"- {ROTULO_FONTE.get(a.status.value, a.status.value)}: {a.texto}" + (f" _(fonte: {a.fonte})_" if a.fonte else "") for a in peca.afirmacoes]
    L += ["", "### Verificações automáticas", *_achados_md(achados)]
    m = peca.metrica
    L += ["", "## 11. Métrica", f"- **Principal:** {m.principal}", f"- **Apoio:** {', '.join(m.apoio)}", f"- **Critério:** {m.criterio_avaliacao}", ""]
    return "\n".join(L)


def distribuicao_pilares(cal: Calendario) -> dict:
    total = len(cal.itens) or 1
    cont = Counter(i.pilar for i in cal.itens)
    return {
        p.value: {"itens": cont.get(p, 0), "real_pct": round(100 * cont.get(p, 0) / total, 1), "alvo_pct": round(100 * PESO_PILAR[p], 1)}
        for p in Pilar
    }


def calendario_md(cal_id: str, cal: Calendario, distribuicao: dict, avisos: list[str]) -> str:
    L = [f"# Calendário {cal_id}", "", f"**Período:** {cal.periodo}", "", "## Premissas", *[f"- {p}" for p in cal.premissas], ""]
    L += ["## Distribuição por pilar", "", "| Pilar | Itens | Real | Alvo inicial |", "|---|---:|---:|---:|"]
    L += [f"| {p} | {d['itens']} | {d['real_pct']}% | {d['alvo_pct']}% |" for p, d in distribuicao.items()]
    L += ["", f"**Estoque:** {cal.observacao_estoque}", ""]
    if avisos:
        L += ["## Avisos", *[f"- ⚠️ {a}" for a in avisos], ""]
    L += ["## Pauta", "", "| # | Data | Pilar | Frente | Formato | Público | Etapa | Tema | Gancho | CTA |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, i in enumerate(cal.itens, 1):
        L.append(f"| {n} | {i.data} | {i.pilar.value} | {i.frente.value} | {i.formato.value} | {i.publico.value} | {i.etapa.value} | {i.tema} | {i.gancho_sugerido} | {i.cta} |")
    L += ["", "## Justificativas e dependências"]
    for n, i in enumerate(cal.itens, 1):
        dep = f" · **Depende de:** {', '.join(i.depende_de)}" if i.depende_de else ""
        serie = f" · **Série:** {i.serie}" if i.serie else ""
        L.append(f"{n}. {i.justificativa}{serie}{dep}")
    L += ["", "## Stories sugeridos", *[f"- {s}" for s in cal.stories_sugeridos], "", "## Pendências", *[f"- {p}" for p in cal.pendencias], ""]
    return "\n".join(L)


def revisao_md(alvo: str, rev: Revisao, achados: list[Achado]) -> str:
    L = [f"# Revisão — {alvo}", "", f"**Veredito:** {rev.veredito}", "", rev.resumo, "", "## Problemas"]
    for p in rev.problemas:
        L += [f"- **[{p.severidade}] {p.categoria}** — _“{p.trecho}”_", f"  - {p.explicacao}", f"  - Sugestão: {p.sugestao}"]
    L += ["", "## Pontos fortes", *[f"- {s}" for s in rev.pontos_fortes]]
    L += ["", "## Campos para validar", *[f"- [ ] {c}" for c in rev.campos_para_validar]]
    L += ["", "## Verificações automáticas", *_achados_md(achados)]
    if rev.versao_revisada:
        L += ["", "## Versão revisada", "", rev.versao_revisada]
    return "\n".join(L) + "\n"


def analise_md(an: Analise, agregados: dict) -> str:
    L = ["# Análise de desempenho", "", an.resumo, "", f"**Base suficiente para conclusões:** {'sim' if an.base_suficiente else 'não'}", ""]
    L += ["## Comparações", *[f"- **{c.grupo}:** {c.observacao} _({c.evidencia})_" for c in an.comparacoes]]
    L += ["", "## Aprendizados", *[f"- {a}" for a in an.aprendizados]]
    L += ["", "## Hipóteses", *[f"- **{h.status}** — {h.hipotese} _({h.evidencia})_" for h in an.hipoteses]]
    L += ["", "## Recomendações", *[f"- **[{r.prioridade}]** {r.acao} — {r.motivo}" for r in an.recomendacoes]]
    L += ["", "## Limitações", *[f"- {x}" for x in an.limitacoes], ""]
    return "\n".join(L)
