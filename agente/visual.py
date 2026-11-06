"""Exibição no terminal (rich), compartilhada pela CLI e pelo menu interativo."""

from __future__ import annotations

import sys
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.markup import escape as esc
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agente.guardrails import Achado, Nivel
from agente.schemas import Analise, Revisao

# Console do Windows: garante UTF-8 para acentos e emojis.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

# Paleta do terminal (combina com o sistema visual neutro do projeto).
DESTAQUE = "#7dcfff"
SUAVE = "grey58"
COR = {Nivel.bloqueio: "red", Nivel.revisao_humana: "yellow", Nivel.aviso: "cyan"}
ICONE_NIVEL = {Nivel.bloqueio: "⛔", Nivel.revisao_humana: "🟡", Nivel.aviso: "ℹ"}
COR_STATUS = {
    "ideia": "grey58",
    "em_criacao": "grey70",
    "revisao": "yellow",
    "aprovado": "green",
    "publicado": "cyan",
    "analisado": "blue",
    "reutilizavel": "magenta",
    "arquivado": "grey42",
}
NOME_STATUS = {
    "ideia": "ideia",
    "em_criacao": "em criação",
    "revisao": "em revisão",
    "aprovado": "aprovado",
    "publicado": "publicado",
    "analisado": "analisado",
    "reutilizavel": "reutilizável",
    "arquivado": "arquivado",
}
COR_VEREDITO = {"bloqueado": "red", "ajustes_necessarios": "yellow", "pronto_para_aprovacao_humana": "green"}

NOME_MODELO = {
    "anthropic/claude-sonnet-5.5": "Sonnet 5.5",
    "anthropic/claude-haiku-5.5": "Haiku 5.5",
    "anthropic/claude-opus-5.5": "Opus 5.5",
    "google/gemini-3.1-flash-image": "Nano Banana 2",
    "google/gemini-3-pro-image": "Nano Banana Pro",
    "google/gemini-2.5-flash-image": "Nano Banana",
}


def nome_modelo(modelo_id: str) -> str:
    return NOME_MODELO.get(modelo_id, modelo_id)


def em_reais(usd: float, cotacao: float) -> str:
    """Valor aproximado em reais, com vírgula decimal."""
    return "R$ " + f"{usd * cotacao:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def selo_status(status: str) -> str:
    return f"[{COR_STATUS.get(status, 'white')}]● {NOME_STATUS.get(status, status)}[/]"


def caminho_curto(p: Path | str) -> str:
    """Caminho relativo à pasta atual quando possível (mais legível)."""
    try:
        return str(Path(p).resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------- blocos
def mostrar_achados(achados: list[Achado]) -> None:
    if not achados:
        console.print("[green]✓ Verificações automáticas: nenhum ponto encontrado.[/]")
        return
    t = Table(title="Verificações automáticas", box=box.ROUNDED, title_style="bold", header_style=SUAVE, expand=True)
    t.add_column("", width=2)
    t.add_column("Nível", no_wrap=True)
    t.add_column("Regra", no_wrap=True, style=SUAVE)
    t.add_column("Mensagem", ratio=2)
    t.add_column("Trecho", ratio=3, overflow="fold", style="italic")
    for a in achados:
        t.add_row(ICONE_NIVEL[a.nivel], f"[{COR[a.nivel]}]{a.nivel.value}[/]", a.regra, esc(a.mensagem), esc(a.trecho))
    console.print(t)


def mostrar_peca(r) -> None:
    """r: ResultadoPeca (de agente.modos)."""
    b = r.brief
    cab = Text.from_markup(
        f"[{SUAVE}]{b.pilar.value} · {b.frente.value} · {b.formato.value} · público {b.publico.value} · {b.etapa.value}"
        + (f" · produto {esc(b.produto_id)}" if b.produto_id else "")
        + "[/]"
    )
    ganchos = Text.from_markup("\n".join(f"[bold {DESTAQUE}]{i}.[/] {esc(g)}" for i, g in enumerate(r.peca.ganchos, 1)))
    corpo = Group(
        cab,
        Text(""),
        Text.from_markup("[bold]Ganchos[/]"),
        ganchos,
        Text(""),
        Text.from_markup(f"[bold]CTA[/]  {esc(r.peca.cta)}"),
        Text.from_markup(f"[bold]Métrica[/]  {esc(r.peca.metrica.principal)}"),
    )
    console.print(
        Panel(
            corpo,
            title=f"[bold]{r.id}[/] [dim]v{r.versao}[/]",
            subtitle=f"[{SUAVE}]{esc(caminho_curto(r.caminho_md))}[/]",
            border_style=DESTAQUE,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print(f"[bold]{esc(r.peca.titulo_interno)}[/]")
    mostrar_achados(r.achados)


def mostrar_uso(ag) -> None:
    u = ag.cliente.uso_acumulado
    if u["prompt_tokens"] or u["completion_tokens"]:
        tokens = f"{int(u['prompt_tokens']):,} entrada / {int(u['completion_tokens']):,} saída".replace(",", ".")
        console.print(f"[{SUAVE}]Tokens: {tokens} · custo ≈ {em_reais(u['custo_usd'], ag.cfg.cotacao_dolar)} (US$ {u['custo_usd']:.4f})[/]")


def mostrar_calendario(r) -> None:
    """r: ResultadoCalendario."""
    t = Table(title=f"Calendário {r.id} — {esc(r.calendario.periodo)}", box=box.ROUNDED, header_style=SUAVE, expand=True)
    for col, kw in (("#", {"width": 3}), ("Data", {"no_wrap": True}), ("Pilar", {}), ("Frente", {}), ("Formato", {}), ("Púb.", {"width": 4}), ("Tema", {"ratio": 3})):
        t.add_column(col, overflow="fold", **kw)
    for n, i in enumerate(r.calendario.itens, 1):
        t.add_row(str(n), i.data, i.pilar.value, i.frente.value, i.formato.value, i.publico.value, esc(i.tema))
    console.print(t)

    d = Table(title="Distribuição por pilar", box=box.SIMPLE_HEAVY, header_style=SUAVE)
    for col in ("Pilar", "Itens", "Real", "Alvo inicial"):
        d.add_column(col, justify="right" if col != "Pilar" else "left")
    for p, v in r.distribuicao.items():
        d.add_row(p, str(v["itens"]), f"{v['real_pct']}%", f"{v['alvo_pct']}%")
    console.print(d)
    for a in r.avisos:
        console.print(f"[yellow]⚠ {esc(a)}[/]")
    console.print(f"[green]Salvo em:[/] {esc(caminho_curto(r.caminho))} (e .md)")


def mostrar_revisao(rev: Revisao, achados: list[Achado], caminho: Path) -> None:
    cor = COR_VEREDITO.get(rev.veredito, "white")
    console.print(Panel(esc(rev.resumo), title=f"Veredito: [bold {cor}]{rev.veredito}[/]", border_style=cor, box=box.ROUNDED, padding=(1, 2)))
    if rev.problemas:
        t = Table(box=box.ROUNDED, header_style=SUAVE, expand=True, title="Problemas apontados")
        t.add_column("Sev.", no_wrap=True)
        t.add_column("Categoria", no_wrap=True)
        t.add_column("Trecho", ratio=2, style="italic", overflow="fold")
        t.add_column("Sugestão", ratio=3, overflow="fold")
        cores = {"alta": "red", "media": "yellow", "baixa": "cyan"}
        for p in rev.problemas:
            t.add_row(f"[{cores.get(p.severidade, 'white')}]{esc(p.severidade)}[/]", esc(p.categoria), esc(p.trecho), esc(p.sugestao))
        console.print(t)
    mostrar_achados(achados)
    console.print(f"[green]Salvo em:[/] {esc(caminho_curto(caminho))}")


def mostrar_analise(an: Analise, caminho: Path) -> None:
    console.print(Panel(esc(an.resumo), title="[bold]Análise de desempenho[/]", border_style=DESTAQUE, box=box.ROUNDED, padding=(1, 2)))
    if not an.base_suficiente:
        console.print("[yellow]⚠ Base de dados insuficiente para conclusões firmes.[/]")
    t = Table(box=box.ROUNDED, header_style=SUAVE, expand=True, title="Recomendações")
    t.add_column("Prioridade", no_wrap=True)
    t.add_column("Ação", ratio=3, overflow="fold")
    t.add_column("Motivo", ratio=2, overflow="fold", style=SUAVE)
    cores = {"alta": "red", "media": "yellow", "baixa": "cyan"}
    for r in an.recomendacoes:
        t.add_row(f"[{cores.get(r.prioridade, 'white')}]{esc(r.prioridade)}[/]", esc(r.acao), esc(r.motivo))
    console.print(t)
    console.print(f"[green]Salvo em:[/] {esc(caminho_curto(caminho))}")


def tabela_pecas(itens: list[dict]) -> Table:
    t = Table(title=f"Peças ({len(itens)})", box=box.ROUNDED, header_style=SUAVE, expand=True)
    t.add_column("ID", no_wrap=True, style=f"bold {DESTAQUE}")
    t.add_column("v", justify="right", width=2)
    t.add_column("Status", no_wrap=True)
    t.add_column("Formato", no_wrap=True)
    t.add_column("Frente", no_wrap=True)
    t.add_column("Bloq.", justify="right", width=5)
    t.add_column("Título", ratio=1, overflow="ellipsis", no_wrap=True)
    for i in itens:
        b = i.get("bloqueios", 0)
        t.add_row(i["id"], str(i["versao_atual"]), selo_status(i["status"]), i["formato"], i["frente"], f"[red]{b}[/]" if b else f"[{SUAVE}]0[/]", esc(i["titulo"]))
    return t


def mostrar_pendencias(ag) -> None:
    pend = Table.grid(padding=(0, 2))
    pend.add_column()
    pend.add_column()
    for k in ag.ctx.negocio_pendente:
        pend.add_row("[yellow]⏳[/]", k)
    for k, v in ag.ctx.negocio_confirmado.items():
        pend.add_row("[green]✓[/]", f"{k}: [dim]{esc(str(v))}[/]")
    console.print(Panel(pend, title="[bold]Dados do negócio[/] [dim](dados/negocio.json)[/]", border_style="yellow", box=box.ROUNDED))

    disp = ag.ctx.estoque_disponivel
    if not disp:
        corpo = Text("Nenhuma unidade disponível — ofertas de venda ficam bloqueadas.", style="yellow")
    else:
        corpo = Table(box=box.SIMPLE, header_style=SUAVE)
        for col in ("ID", "Modelo", "GB", "Bateria", "Preço"):
            corpo.add_column(col)
        for a in disp:
            corpo.add_row(
                esc(a.id), esc(a.modelo), str(a.armazenamento_gb or "?"), f"{a.saude_bateria_pct or '?'}%",
                "[green]aprovado[/]" if a.preco_aprovado_brl else f"[yellow]{esc('[PENDENTE]')}[/]",
            )
    console.print(Panel(corpo, title="[bold]Estoque[/] [dim](dados/estoque.json)[/]", border_style=DESTAQUE, box=box.ROUNDED))

    chave = "[green]✓ configurada[/]" if ag.cfg.api_key else "[red]✗ FALTANDO no .env[/]"
    console.print(
        Panel(
            f"Texto: [bold]{esc(nome_modelo(ag.cfg.modelo_texto))}[/] [dim]({esc(ag.cfg.modelo_texto)})[/]\n"
            f"Imagem: [bold]{esc(nome_modelo(ag.cfg.modelo_imagem))}[/] [dim]({esc(ag.cfg.modelo_imagem)})[/]\n"
            f"Chave OpenRouter: {chave}",
            title="[bold]Configuração[/]",
            border_style=SUAVE,
            box=box.ROUNDED,
        )
    )


def painel_erro(msg: str) -> Panel:
    return Panel(esc(msg), title="[bold red]Erro[/]", border_style="red", box=box.ROUNDED, padding=(1, 2))
