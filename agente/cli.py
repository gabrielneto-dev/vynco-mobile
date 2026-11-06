"""Interface de linha de comando: `python -m agente <comando>`; sem comando, abre o menu interativo."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.table import Table

from agente.armazenamento import ErroRegistro
from agente.guardrails import Nivel
from agente.llm import ErroLLM
from agente.modos import Agente, ErroAgente, ResultadoPeca
from agente.schemas import (
    ETAPA_POR_PILAR,
    FRENTE_POR_PILAR,
    PUBLICO_POR_PILAR,
    Brief,
    Etapa,
    Formato,
    Frente,
    Pilar,
    Publico,
    StatusPeca,
)
from agente.visual import (
    COR,
    caminho_curto,
    console,
    esc,
    mostrar_analise,
    mostrar_calendario,
    mostrar_peca,
    mostrar_pendencias,
    mostrar_revisao,
    mostrar_uso,
    tabela_pecas,
)

app = typer.Typer(
    help="Agente de conteúdo para loja de iPhones — planejar, criar, adaptar, revisar e analisar. Sem comando, abre o menu.",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.callback(invoke_without_command=True)
def principal(ctx: typer.Context):
    """Sem subcomando: abre o menu interativo."""
    if ctx.invoked_subcommand is None:
        from agente.menu import executar_menu

        executar_menu()


@app.command()
def menu():
    """Abre o menu interativo."""
    from agente.menu import executar_menu

    executar_menu()


def _agente() -> Agente:
    return Agente.padrao()


def _falhar(msg: str) -> None:
    console.print(f"[bold red]Erro:[/] {esc(msg)}")
    raise typer.Exit(1)


def _executar(fn):
    try:
        return fn()
    except (ErroAgente, ErroLLM, ErroRegistro, ValueError, FileNotFoundError) as erro:
        _falhar(str(erro))


# ====================================================================== PLANEJAR
@app.command()
def planejar(
    semanas: int = typer.Option(4, help="Número de semanas."),
    inicio: Optional[str] = typer.Option(None, help="Data inicial AAAA-MM-DD (padrão: hoje)."),
    por_semana: int = typer.Option(4, help="Publicações de feed/Reels por semana."),
    foco: Optional[str] = typer.Option(None, help="Observações do responsável (campanha, sazonalidade, prioridade)."),
    modelo: Optional[str] = typer.Option(None, help="Modelo OpenRouter (sobrescreve MODELO_TEXTO)."),
):
    """Monta um calendário editorial respeitando pilares, frentes e estoque."""
    ag = _agente()
    data_inicio = date.fromisoformat(inicio) if inicio else None
    with console.status("Planejando calendário..."):
        r = _executar(lambda: ag.planejar(semanas=semanas, inicio=data_inicio, publicacoes_semana=por_semana, foco=foco, modelo=modelo))
    mostrar_calendario(r)
    console.print(f"[dim]Para gerar as peças: python -m agente lote {r.id}[/]")
    mostrar_uso(ag)


# ====================================================================== CRIAR
@app.command()
def criar(
    pilar: Pilar = typer.Option(..., help="atracao | educacao | relacionamento | conversao | captacao"),
    formato: Formato = typer.Option(..., help="reel | carrossel | imagem | stories | anuncio"),
    objetivo: str = typer.Option(..., help="Tema/objetivo da peça, em uma frase."),
    publico: Optional[Publico] = typer.Option(None, help="A | B | C | D (padrão conforme o pilar)."),
    etapa: Optional[Etapa] = typer.Option(None, help="Etapa do funil (padrão conforme o pilar)."),
    frente: Optional[Frente] = typer.Option(None, help="venda | captacao | marca (padrão conforme o pilar)."),
    produto: Optional[str] = typer.Option(None, help="ID da unidade em dados/estoque.json (ofertas reais)."),
    generico: bool = typer.Option(False, help="Permite peça de venda sem unidade específica (sem preço/disponibilidade)."),
    regiao: Optional[str] = typer.Option(None),
    oferta: Optional[str] = typer.Option(None, help="Somente ofertas aprovadas pelo responsável."),
    cta: Optional[str] = typer.Option(None),
    serie: Optional[str] = typer.Option(None, help="Ex.: 'iPhone sem cilada'."),
    restricoes: Optional[str] = typer.Option(None),
    referencias: Optional[str] = typer.Option(None),
    imagem: bool = typer.Option(False, "--imagem", help="Gera a imagem com Nano Banana em seguida (se permitido)."),
    modelo: Optional[str] = typer.Option(None, help="Modelo de texto OpenRouter."),
):
    """Cria uma peça completa (11 campos da saída padrão) e roda as verificações."""
    ag = _agente()
    brief = Brief(
        objetivo=objetivo,
        pilar=pilar,
        frente=frente or FRENTE_POR_PILAR[pilar],
        publico=publico or PUBLICO_POR_PILAR[pilar],
        etapa=etapa or ETAPA_POR_PILAR[pilar],
        formato=formato,
        produto_id=produto,
        regiao=regiao,
        oferta=oferta,
        cta=cta,
        serie=serie,
        restricoes=restricoes,
        referencias=referencias,
    )
    if brief.pilar == Pilar.captacao and brief.publico != Publico.C:
        console.print("[yellow]⚠ Captação normalmente fala com o público C (vendedor de usado).[/]")
    with console.status("Criando peça..."):
        r = _executar(lambda: ag.criar(brief, generico=generico, modelo=modelo))
    mostrar_peca(r)
    if imagem:
        _gerar_imagem_peca(ag, r.id, None, 1, None, None, [])
    mostrar_uso(ag)


# ====================================================================== LOTE
@app.command()
def lote(
    calendario: str = typer.Argument(..., help="ID do calendário (C-...) ou caminho do JSON."),
    limite: Optional[int] = typer.Option(None, help="Gera só os N primeiros itens."),
    generico_vendas: bool = typer.Option(False, help="Gera itens de venda como conteúdo genérico, sem unidade."),
    refazer: bool = typer.Option(False, help="Gera de novo itens que já viraram peça."),
    modelo: Optional[str] = typer.Option(None),
):
    """Gera as peças de todos os itens de um calendário (retoma de onde parou)."""
    ag = _agente()
    t = Table(title=f"Lote {calendario}", box=box.ROUNDED, expand=True)
    for col in ("#", "Tema", "Resultado", "Bloqueios"):
        t.add_column(col, overflow="fold")
    try:
        for n, item, res in ag.lote(calendario, limite=limite, generico_vendas=generico_vendas, refazer=refazer, modelo=modelo):
            if isinstance(res, ResultadoPeca):
                bloq = sum(1 for a in res.achados if a.nivel == Nivel.bloqueio)
                t.add_row(str(n), esc(item.tema), f"[green]{res.id}[/]", f"[red]{bloq}[/]" if bloq else "0")
                console.print(f"[green]✓[/] {n}. {esc(item.tema)} → {res.id}")
            else:
                t.add_row(str(n), esc(item.tema), f"[yellow]{esc(res)}[/]", "-")
                console.print(f"[yellow]•[/] {n}. {esc(item.tema)} → {esc(res)}")
    except ErroRegistro as erro:
        _falhar(str(erro))
    console.print(t)
    mostrar_uso(ag)


# ====================================================================== ADAPTAR / REVERIFICAR
@app.command()
def adaptar(
    peca_id: str = typer.Argument(...),
    formato: Formato = typer.Option(..., help="Formato de destino."),
    observacoes: Optional[str] = typer.Option(None),
    modelo: Optional[str] = typer.Option(None),
):
    """Transforma uma peça existente em Reel, Stories, carrossel, imagem ou anúncio."""
    ag = _agente()
    with console.status(f"Adaptando {peca_id} para {formato.value}..."):
        r = _executar(lambda: ag.adaptar(peca_id, formato, observacoes=observacoes, modelo=modelo))
    mostrar_peca(r)
    mostrar_uso(ag)


@app.command()
def reverificar(peca_id: str = typer.Argument(...)):
    """Reaplica as verificações automáticas (sem custo de API) e grava nova versão."""
    ag = _agente()
    r = _executar(lambda: ag.reverificar(peca_id))
    mostrar_peca(r)


# ====================================================================== REVISAR / ANALISAR
@app.command()
def revisar(
    alvo: str = typer.Argument(..., help="ID de peça, caminho de arquivo .txt/.md ou texto entre aspas."),
    contexto: Optional[str] = typer.Option(None, help="Informações extras para o revisor."),
    modelo: Optional[str] = typer.Option(None),
):
    """Auditoria de clareza, veracidade, marca, objetivo e conformidade."""
    ag = _agente()
    with console.status("Revisando..."):
        rev, achados, caminho = _executar(lambda: ag.revisar(alvo, contexto_extra=contexto, modelo=modelo))
    mostrar_revisao(rev, achados, caminho)
    mostrar_uso(ag)


@app.command()
def analisar(
    csv_path: Path = typer.Argument(..., exists=True, help="CSV de resultados (ver exemplos/resultados_exemplo.csv)."),
    modelo: Optional[str] = typer.Option(None),
):
    """Compara desempenho com dados reais e recomenda ajustes."""
    ag = _agente()
    with console.status("Analisando resultados..."):
        an, _, caminho = _executar(lambda: ag.analisar(csv_path, modelo=modelo))
    mostrar_analise(an, caminho)
    mostrar_uso(ag)


# ====================================================================== IMAGENS
def _gerar_imagem_peca(ag: Agente, peca_id, proporcao, quantidade, modelo, tamanho, referencias):
    with console.status("Gerando imagem com Nano Banana..."):
        caminhos, achados = _executar(
            lambda: ag.imagem_da_peca(peca_id, proporcao=proporcao, quantidade=quantidade, modelo=modelo, tamanho=tamanho, referencias=referencias)
        )
    for a in achados:
        console.print(f"[{COR[a.nivel]}]{a.nivel.value}: {esc(a.mensagem)}[/]")
    for c in caminhos:
        console.print(f"[green]Imagem:[/] {esc(caminho_curto(c))}")
    console.print("[dim]Imagem gerada por IA: só para conceitos/campanhas gerais, nunca para representar a unidade vendida.[/]")


@app.command()
def imagem(
    peca_id: str = typer.Argument(...),
    proporcao: Optional[str] = typer.Option(None, help="Ex.: 9:16, 4:5, 1:1 (padrão: a da direção de arte)."),
    quantidade: int = typer.Option(1, min=1, max=4),
    modelo: Optional[str] = typer.Option(None, help="google/gemini-3.1-flash-image (padrão), google/gemini-3-pro-image, ..."),
    tamanho: Optional[str] = typer.Option(None, help="1K | 2K | 4K (modelos que suportam)."),
    referencia: list[Path] = typer.Option([], exists=True, help="Imagem de referência (logo, cenário). Repetível."),
):
    """Gera a imagem de uma peça a partir do prompt dela (Nano Banana via OpenRouter)."""
    ag = _agente()
    _gerar_imagem_peca(ag, peca_id, proporcao, quantidade, modelo, tamanho, referencia)
    mostrar_uso(ag)


@app.command("imagem-livre")
def imagem_livre(
    prompt: str = typer.Argument(..., help="Prompt (de preferência em inglês)."),
    proporcao: str = typer.Option("4:5"),
    quantidade: int = typer.Option(1, min=1, max=4),
    modelo: Optional[str] = typer.Option(None),
    tamanho: Optional[str] = typer.Option(None),
    referencia: list[Path] = typer.Option([], exists=True),
):
    """Gera uma imagem conceitual avulsa."""
    ag = _agente()
    with console.status("Gerando imagem com Nano Banana..."):
        caminhos, achados = _executar(lambda: ag.imagem_livre(prompt, proporcao=proporcao, quantidade=quantidade, modelo=modelo, tamanho=tamanho, referencias=referencia))
    for a in achados:
        console.print(f"[{COR[a.nivel]}]{a.nivel.value}: {esc(a.mensagem)}[/]")
    for c in caminhos:
        console.print(f"[green]Imagem:[/] {esc(caminho_curto(c))}")
    mostrar_uso(ag)


@app.command()
def arte(
    peca_id: str = typer.Argument(...),
    gancho: int = typer.Option(1, help="Qual dos 3 ganchos vira o título."),
    fundo: str = typer.Option("auto", help="auto | ia | liso (peça de unidade real usa sempre foto real)."),
    rascunho: bool = typer.Option(False, help="Gera mesmo com [PENDENTE], com tarja de rascunho."),
):
    """Monta a arte final (PNG pronto para postar) — processamento local, sem custo."""
    from agente.arte import ErroArte, montar_arte

    ag = _agente()
    try:
        r = montar_arte(ag, peca_id, gancho=gancho, fundo=fundo, rascunho=rascunho)
    except (ErroArte, ErroRegistro) as erro:
        _falhar(str(erro))
    console.print(f"[green]{len(r.arquivos)} arquivo(s){' (RASCUNHO)' if r.rascunho else ''}:[/] {esc(caminho_curto(r.pasta))}")
    for a in r.avisos:
        console.print(f"[dim]• {esc(a)}[/]")


# ====================================================================== REGISTRO / FLUXO
@app.command()
def listar(
    status: Optional[StatusPeca] = typer.Option(None),
    frente: Optional[Frente] = typer.Option(None),
):
    """Lista as peças registradas."""
    ag = _agente()
    console.print(tabela_pecas(ag.registro.listar(status.value if status else None, frente.value if frente else None)))


@app.command()
def status(
    peca_id: str = typer.Argument(...),
    novo: StatusPeca = typer.Argument(..., help="ideia | em_criacao | revisao | aprovado | publicado | analisado | reutilizavel | arquivado"),
    responsavel: str = typer.Option(..., help="Nome de quem está decidindo."),
    nota: Optional[str] = typer.Option(None),
):
    """Muda o status de uma peça (aprovação exige responsável humano e zero bloqueios)."""
    ag = _agente()
    _executar(lambda: ag.registro.atualizar_status(peca_id, novo, responsavel, nota))
    console.print(f"[green]{peca_id} → {novo.value}[/] (por {esc(responsavel)})")


@app.command()
def publicado(
    peca_id: str = typer.Argument(...),
    data: str = typer.Option(..., help="Data da publicação AAAA-MM-DD."),
    responsavel: str = typer.Option(...),
    url: Optional[str] = typer.Option(None, help="URL ou ID do post/anúncio."),
    campanha: Optional[str] = typer.Option(None),
    criativo: Optional[str] = typer.Option(None, help="Nome/ID do criativo ou variação usada."),
):
    """Registra uma publicação feita MANUALMENTE (o agente não publica)."""
    ag = _agente()
    _executar(lambda: ag.registro.registrar_publicacao(peca_id, url=url, data=data, campanha=campanha, criativo=criativo, responsavel=responsavel))
    console.print(f"[green]{peca_id} registrada como publicada em {data}.[/]")


@app.command()
def pendencias():
    """Mostra o que falta em dados/negocio.json, o estoque disponível e a configuração."""
    mostrar_pendencias(_agente())


if __name__ == "__main__":
    app()
