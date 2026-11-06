"""Menu interativo no terminal: `python -m agente` (sem argumentos) ou `python -m agente menu`.

Organização:
  - Perguntas: camada fina sobre o questionary (setas + Enter). Nos testes é trocada por respostas roteirizadas.
  - fluxo_*: cada opção do menu. Pergunta, confirma o custo estimado e chama os métodos de agente.modos.Agente.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

import questionary
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agente.armazenamento import ErroRegistro
from agente.contexto import carregar_contexto
from agente.guardrails import Nivel, bloqueio_imagem
from agente.llm import ErroLLM
from agente.modos import Agente, ErroAgente, ResultadoPeca, _proporcao_da_peca
from agente.schemas import (
    ETAPA_POR_PILAR,
    FRENTE_POR_PILAR,
    PUBLICO_POR_PILAR,
    Brief,
    Etapa,
    Formato,
    Pilar,
    Publico,
    StatusPeca,
)
from agente.visual import (
    COR,
    DESTAQUE,
    NOME_STATUS,
    SUAVE,
    caminho_curto,
    console,
    em_reais,
    esc,
    mostrar_analise,
    mostrar_calendario,
    mostrar_peca,
    mostrar_pendencias,
    mostrar_revisao,
    nome_modelo,
    painel_erro,
    selo_status,
    tabela_pecas,
)

ERROS = (ErroAgente, ErroLLM, ErroRegistro, ValueError, FileNotFoundError)


class Voltar(Exception):
    """Usuário pediu para voltar (Ctrl+C, 'Voltar' ou recusou o custo)."""


class Aviso(Exception):
    """Nada a fazer (ex.: lista vazia): mostra a mensagem e pausa antes de voltar."""


# ====================================================================== textos
DESC_PILAR = {
    Pilar.atracao: ("🧲 Atração", "Descoberta e compartilhamento · peso inicial 30% · frente marca"),
    Pilar.educacao: ("🎓 Educação", "Autoridade e confiança · peso inicial 25% · frente marca"),
    Pilar.relacionamento: ("💬 Relacionamento", "Recorrência e comunidade · peso inicial 15% · frente marca"),
    Pilar.conversao: ("🛒 Conversão (venda)", "Unidade real do estoque ou venda genérica · peso inicial 20% · frente venda"),
    Pilar.captacao: ("📥 Captação (compra de usados)", "Atrair donos de iPhone 13/14/15 · peso inicial 10% · frente captação"),
}
DESC_FORMATO = {
    Formato.reel: ("🎬 Reel", "Vídeo vertical 9:16 · descoberta, demonstração, comparativos"),
    Formato.carrossel: ("🗂 Carrossel", "Slides 4:5 · checklists, tutoriais, conteúdo salvável"),
    Formato.imagem: ("🖼 Imagem estática", "4:5 · oferta, captação, informação rápida"),
    Formato.stories: ("📲 Stories", "Sequência 9:16 · bastidores, perguntas, relacionamento"),
    Formato.anuncio: ("📣 Anúncio (Meta Ads)", "Conversas/leads · exige aprovação explícita"),
}
DESC_PUBLICO = {
    Publico.A: ("A · Comprador econômico", "Quer iPhone confiável com bom custo-benefício"),
    Publico.B: ("B · Quer trocar de modelo", "Busca atualização e ganho real entre gerações"),
    Publico.C: ("C · Vendedor de usado", "Quer vender o próprio iPhone com segurança"),
    Publico.D: ("D · Seguidor em formação", "Interessado em dicas; futuro potencial comercial"),
}
NOME_ETAPA = {
    Etapa.descoberta: "Descoberta",
    Etapa.interesse: "Interesse",
    Etapa.confianca: "Confiança",
    Etapa.intencao: "Intenção",
    Etapa.conversao: "Conversão",
    Etapa.fidelizacao: "Fidelização",
}
SERIES = ["iPhone sem cilada", "Vale o upgrade?", "Seu iPhone vale quanto?", "Mito ou verdade?", "Por dentro da avaliação"]

MODELOS_TEXTO = [
    ("anthropic/claude-haiku-5.5", "Econômico (padrão) — ≈ R$ 0,02 por peça; bom para o dia a dia"),
    ("anthropic/claude-sonnet-5.5", "Qualidade — ≈ R$ 0,35 por peça; texto mais refinado para peças finais"),
]
MODELOS_IMAGEM = [
    ("google/gemini-3.1-flash-image", "Padrão — bom custo/qualidade (≈ R$ 0,37 por imagem 1K)"),
    ("google/gemini-2.5-flash-image", "Mais barato (≈ R$ 0,21 por imagem) — ótimo para testar ideias"),
    ("google/gemini-3-pro-image", "Mais qualidade e melhor texto na imagem (≈ R$ 0,74 por imagem 1K)"),
]

# ====================================================================== custo estimado
# US$ por 1M de tokens (entrada, saída) — tabela do OpenRouter em 11/2026.
PRECO_TEXTO = {"anthropic/claude-sonnet-5.5": (2.0, 10.0), "anthropic/claude-haiku-5.5": (0.10, 0.50)}
# Tokens medidos nos testes reais após as otimizações (entrada, saída sem raciocínio).
TOKENS_ACAO = {
    "criar": (11_500, 3_200),
    "adaptar": (14_500, 3_200),
    "revisar": (13_000, 2_500),
    "analisar": (13_000, 3_000),
    "planejar_semana": (11_000, 3_000),
}
# Modelos que raciocinam antes de responder geram mais saída (medido: Sonnet 5.5 com esforço "low").
FATOR_SAIDA = {"anthropic/claude-sonnet-5.5": 1.35}
PRECO_TOKEN_IMAGEM = {"google/gemini-3.1-flash-image": 6e-5, "google/gemini-3-pro-image": 1.2e-4, "google/gemini-2.5-flash-image": 3e-5}
TOKENS_IMAGEM = {None: 1_120, "2K": 1_680, "4K": 2_520}


def estimar_texto(acao: str, modelo: str, vezes: int = 1, semanas: int = 1) -> float | None:
    if modelo not in PRECO_TEXTO:
        return None
    p_in, p_out = PRECO_TEXTO[modelo]
    if acao == "planejar":
        t_in, t_out = TOKENS_ACAO["planejar_semana"][0], 1_000 + 2_000 * semanas
    else:
        t_in, t_out = TOKENS_ACAO[acao]
    t_out *= FATOR_SAIDA.get(modelo, 1.0)
    return vezes * (t_in * p_in + t_out * p_out) / 1_000_000


def estimar_imagem(modelo: str, tamanho: str | None = None, quantidade: int = 1) -> float | None:
    if modelo not in PRECO_TOKEN_IMAGEM:
        return None
    tokens = 1_290 if modelo == "google/gemini-2.5-flash-image" else TOKENS_IMAGEM.get(tamanho, 1_120)
    return quantidade * tokens * PRECO_TOKEN_IMAGEM[modelo]


def somar(*valores: float | None) -> float | None:
    return None if any(v is None for v in valores) else sum(valores)  # type: ignore[arg-type]


# ====================================================================== perguntas
ESTILO = questionary.Style(
    [
        ("qmark", f"fg:{DESTAQUE} bold"),
        ("question", "bold"),
        ("answer", "fg:#9ece6a bold"),
        ("pointer", f"fg:{DESTAQUE} bold"),
        ("highlighted", f"fg:{DESTAQUE} bold"),
        ("selected", "fg:#9ece6a"),
        ("separator", "fg:#565f89"),
        ("instruction", "fg:#565f89 italic"),
        ("text", ""),
        ("disabled", "fg:#565f89 italic"),
    ]
)
def _traduzir_descricao() -> None:
    """O questionary escreve 'Description:' fixo em inglês; troca por um ícone discreto e em cinza."""
    from questionary.prompts.common import InquirerControl

    original = InquirerControl._get_choice_tokens
    if getattr(original, "_traduzido", False):
        return

    def _tokens(self):
        return [
            ("class:instruction", "  ℹ  " + t[1][len("  Description: "):]) if t[1].startswith("  Description: ") else t
            for t in original(self)
        ]

    _tokens._traduzido = True  # type: ignore[attr-defined]
    InquirerControl._get_choice_tokens = _tokens


_traduzir_descricao()


class Separador:
    def __init__(self, texto: str):
        self.texto = texto


class Perguntas:
    """Perguntas reais no terminal (questionary)."""

    def _perguntar(self, pergunta) -> Any:
        try:
            resposta = pergunta.unsafe_ask()
        except KeyboardInterrupt:
            raise Voltar()
        if resposta is None:
            raise Voltar()
        return resposta

    def escolher(self, mensagem: str, opcoes: list, padrao: Any = None) -> Any:
        escolhas = []
        for o in opcoes:
            if isinstance(o, Separador):
                escolhas.append(questionary.Separator(f"  {o.texto}"))
            else:
                titulo, valor, *desc = o
                escolhas.append(questionary.Choice(titulo, value=valor, description=desc[0] if desc else None))
        valores = [c.value for c in escolhas if isinstance(c, questionary.Choice)]
        return self._perguntar(
            questionary.select(
                mensagem,
                choices=escolhas,
                default=padrao if padrao in valores else None,
                style=ESTILO,
                qmark="›",
                pointer="❯",
                instruction="(↑↓ e Enter · Ctrl+C volta)",
            )
        )

    def texto(self, mensagem: str, padrao: str = "", obrigatorio: bool = False, validar: Callable[[str], Any] | None = None, multilinha: bool = False) -> str:
        def _validar(v: str):
            if obrigatorio and not v.strip():
                return "Campo obrigatório."
            return validar(v) if validar else True

        instrucao = " (Esc e depois Enter para concluir)" if multilinha else ""
        return self._perguntar(
            questionary.text(mensagem + instrucao, default=padrao, validate=_validar, style=ESTILO, qmark="›", multiline=multilinha)
        ).strip()

    def caminho(self, mensagem: str, padrao: str = "") -> str:
        def _validar(v: str):
            return True if v.strip() and Path(v.strip().strip('"')).is_file() else "Arquivo não encontrado."

        return self._perguntar(questionary.path(mensagem, default=padrao, validate=_validar, style=ESTILO, qmark="›")).strip().strip('"')

    def confirmar(self, mensagem: str, padrao: bool = True) -> bool:
        opcoes = [("Sim", True), ("Não", False)]
        return self.escolher(mensagem, opcoes, padrao=padrao)

    def pausar(self) -> None:
        try:
            questionary.press_any_key_to_continue("Pressione qualquer tecla para continuar...", style=ESTILO).unsafe_ask()
        except KeyboardInterrupt:
            pass


# ====================================================================== sessão
@dataclass
class Sessao:
    ag: Agente
    p: Perguntas
    modelo_texto: str
    modelo_imagem: str
    responsavel: str | None = None
    limpar_tela: bool = True
    extras: dict = field(default_factory=dict)

    @classmethod
    def nova(cls, perguntas: Perguntas | None = None) -> "Sessao":
        ag = Agente.padrao()
        return cls(ag=ag, p=perguntas or Perguntas(), modelo_texto=ag.cfg.modelo_texto, modelo_imagem=ag.cfg.modelo_imagem)

    def recarregar(self) -> None:
        """Relê negocio.json e estoque.json (o usuário pode ter editado fora do menu)."""
        self.ag.ctx = carregar_contexto(self.ag.cfg)

    def limpar(self) -> None:
        if self.limpar_tela:
            console.clear()


# ====================================================================== cabeçalho
ORDEM_STATUS = ["revisao", "aprovado", "publicado", "analisado", "arquivado"]


def cabecalho(s: Sessao) -> Panel:
    ag = s.ag
    pecas = ag.registro.listar()
    cont = Counter(p["status"] for p in pecas)
    pend = len(ag.ctx.negocio_pendente)
    disp = len(ag.ctx.estoque_disponivel)
    custo = ag.cliente.uso_acumulado["custo_usd"]

    g = Table.grid(padding=(0, 2), expand=True)
    g.add_column(style=SUAVE, no_wrap=True)
    g.add_column(ratio=1)
    g.add_column(style=SUAVE, no_wrap=True)
    g.add_column(ratio=1)
    g.add_row(
        "Texto", f"[bold]{esc(nome_modelo(s.modelo_texto))}[/]",
        "Imagem", f"[bold]{esc(nome_modelo(s.modelo_imagem))}[/]",
    )
    g.add_row(
        "OpenRouter", "[green]✓ chave configurada[/]" if ag.cfg.api_key else "[red]✗ chave faltando no .env[/]",
        "Sessão", f"{em_reais(custo, ag.cfg.cotacao_dolar)} [{SUAVE}](US$ {custo:.4f})[/]",
    )
    g.add_row(
        "Negócio", f"[yellow]{pend} informações pendentes[/]" if pend else "[green]✓ completo[/]",
        "Estoque", f"[green]{disp} unidade(s)[/]" if disp else "[yellow]vazio · vendas bloqueadas[/]",
    )
    resumo = "  ".join(f"{selo_status(st)} {cont[st]}" for st in ORDEM_STATUS if cont.get(st)) or f"[{SUAVE}]nenhuma ainda[/]"
    g.add_row("Peças", resumo, "", "")

    titulo = Text.from_markup(f"[bold {DESTAQUE}]📱  Agente de Conteúdo[/]  [{SUAVE}]·  Loja de iPhones[/]")
    lema = Text.from_markup(f"[italic {SUAVE}]Comprar e vender iPhones com mais informação, segurança e negociação justa.[/]")
    return Panel(
        Group(titulo, lema, Text(""), g),
        box=box.ROUNDED,
        border_style=DESTAQUE,
        padding=(1, 2),
        subtitle=f"[{SUAVE}]planejar · criar · adaptar · revisar · analisar[/]",
    )


def opcoes_menu(s: Sessao) -> list:
    return [
        Separador("─── Planejamento ───"),
        ("📅  Planejar calendário", "planejar", "Monta a pauta respeitando pilares, frentes e estoque"),
        ("📦  Gerar peças de um calendário", "lote", "Cria as peças de um calendário salvo (retoma de onde parou)"),
        Separador("─── Criação ───"),
        ("📝  Criar peça", "criar", "Assistente passo a passo: pilar, formato, público, tema"),
        ("🔀  Adaptar peça para outro formato", "adaptar", "Ex.: carrossel → Stories, anúncio → Reel"),
        ("🎨  Gerar imagem de uma peça", "imagem", "Nano Banana a partir do prompt da peça"),
        ("✨  Imagem livre", "imagem_livre", "Imagem conceitual a partir de um prompt seu"),
        Separador("─── Qualidade ───"),
        ("🔍  Revisar com IA", "revisar", "Auditoria de clareza, veracidade, marca e conformidade"),
        ("🔄  Reverificar regras", "reverificar", "Reaplica as verificações automáticas · grátis"),
        Separador("─── Gestão ───"),
        ("📋  Peças e aprovação", "pecas", "Ver, abrir, aprovar, registrar publicação, arquivar"),
        ("📊  Analisar resultados", "analisar", "Compara desempenho a partir de um CSV de métricas"),
        Separador("─── Sistema ───"),
        (f"🧠  Modelo de texto: {nome_modelo(s.modelo_texto)}", "modelo", "Sonnet para peças finais, Haiku para rascunhos"),
        ("🧰  Pendências e configuração", "config", "Dados do negócio, estoque, modelo de imagem, pastas"),
        ("🚪  Sair", "sair"),
    ]


# ====================================================================== utilidades
def abrir_arquivo(caminho: Path | str) -> None:
    caminho = str(caminho)
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
        console.print(f"[green]Abrindo[/] {esc(caminho_curto(caminho))}")
    except OSError as erro:
        console.print(f"[yellow]Não consegui abrir automaticamente ({esc(str(erro))}). Caminho: {esc(caminho)}[/]")


def confirmar_custo(s: Sessao, valor: float | None, modelo: str) -> None:
    if valor is None:
        console.print(f"[{SUAVE}]💰 Custo estimado indisponível para {esc(nome_modelo(modelo))}.[/]")
    else:
        console.print(f"[{SUAVE}]💰 Custo estimado ≈[/] [bold]{em_reais(valor, s.ag.cfg.cotacao_dolar)}[/] [{SUAVE}](US$ {valor:.3f} · {esc(nome_modelo(modelo))})[/]")
    if not s.p.confirmar("Continuar?", padrao=True):
        raise Voltar()


def titulo_secao(texto: str) -> None:
    console.print()
    console.rule(f"[bold {DESTAQUE}]{texto}[/]", style=SUAVE)
    console.print()


def escolher_peca(s: Sessao, mensagem: str, filtro: Callable[[dict], bool] | None = None) -> str:
    itens = [i for i in s.ag.registro.listar() if (filtro is None or filtro(i))]
    if not itens:
        raise Aviso("Nenhuma peça disponível para esta ação.")
    opcoes = [
        (
            f"{i['id']}  {i['formato']:<9} {i['titulo'][:58]}",
            i["id"],
            f"{i['pilar']} · {i['frente']} · {i['status']} · v{i['versao_atual']}" + (f" · {i['bloqueios']} bloqueio(s)" if i.get("bloqueios") else ""),
        )
        for i in itens
    ]
    return s.p.escolher(mensagem, opcoes + [("↩  Voltar", "__voltar__")])


def _resultado_registrado(s: Sessao, peca_id: str) -> ResultadoPeca:
    peca, brief, achados, doc = s.ag.registro.carregar_modelos(peca_id)
    return ResultadoPeca(peca_id, doc["versao"], peca, brief, achados, s.ag.registro.dir_peca(peca_id) / f"v{doc['versao']}.md")


def _ou_voltar(valor: str) -> str:
    if valor == "__voltar__":
        raise Voltar()
    return valor


def _validar_data(v: str):
    try:
        date.fromisoformat(v.strip())
        return True
    except ValueError:
        return "Use o formato AAAA-MM-DD."


# ====================================================================== fluxos
def fluxo_criar(s: Sessao) -> None:
    titulo_secao("📝 Criar peça")
    pilar = s.p.escolher("Qual o pilar?", [(DESC_PILAR[p][0], p, DESC_PILAR[p][1]) for p in Pilar])
    formato = s.p.escolher("Qual o formato?", [(DESC_FORMATO[f][0], f, DESC_FORMATO[f][1]) for f in Formato])
    objetivo = s.p.texto("Tema/objetivo da peça (uma frase):", obrigatorio=True)
    publico = s.p.escolher("Público:", [(DESC_PUBLICO[x][0], x, DESC_PUBLICO[x][1]) for x in Publico], padrao=PUBLICO_POR_PILAR[pilar])
    etapa = s.p.escolher("Etapa do funil:", [(NOME_ETAPA[e], e) for e in Etapa], padrao=ETAPA_POR_PILAR[pilar])
    serie = s.p.escolher("Série recorrente:", [("Nenhuma", "-")] + [(x, x) for x in SERIES], padrao="-")

    produto_id, generico = None, False
    if pilar == Pilar.conversao:
        disp = s.ag.ctx.estoque_disponivel
        if not disp:
            console.print("[yellow]Estoque vazio: só é possível criar conteúdo de venda genérico (sem preço nem disponibilidade).[/]")
        opcoes = [
            (f"{a.id} — {a.modelo} {a.armazenamento_gb or '?'}GB", a.id, f"bateria {a.saude_bateria_pct or '?'}% · preço {'aprovado' if a.preco_aprovado_brl else 'pendente'}")
            for a in disp
        ] + [("Venda genérica (sem unidade)", "__generico__", "Sem preço, disponibilidade ou dados de condição")]
        escolha = s.p.escolher("Qual unidade do estoque?", opcoes)
        generico = escolha == "__generico__"
        produto_id = None if generico else escolha

    gerar_img = False
    if produto_id:
        console.print(f"[{SUAVE}]Peça de unidade real: a imagem deve ser foto real do aparelho (imagem gerada fica bloqueada).[/]")
    else:
        gerar_img = s.p.confirmar("Gerar a imagem com Nano Banana logo em seguida?", padrao=False)

    custo = somar(estimar_texto("criar", s.modelo_texto), estimar_imagem(s.modelo_imagem) if gerar_img else 0.0)
    confirmar_custo(s, custo, s.modelo_texto)

    brief = Brief(
        objetivo=objetivo,
        pilar=pilar,
        frente=FRENTE_POR_PILAR[pilar],
        publico=publico,
        etapa=etapa,
        formato=formato,
        produto_id=produto_id,
        serie=None if serie == "-" else serie,
    )
    with console.status(f"Criando peça com {nome_modelo(s.modelo_texto)}... (≈ 30–60 s)", spinner="dots"):
        r = s.ag.criar(brief, generico=generico, modelo=s.modelo_texto)
    mostrar_peca(r)
    if gerar_img:
        _gerar_imagem(s, r.id)
    if s.p.confirmar("Abrir o documento da peça agora?", padrao=False):
        abrir_arquivo(r.caminho_md)


def _gerar_imagem(s: Sessao, peca_id: str, *, proporcao: str | None = None, tamanho: str | None = None, quantidade: int = 1, modelo: str | None = None) -> list[Path]:
    modelo = modelo or s.modelo_imagem
    with console.status(f"Gerando imagem com {nome_modelo(modelo)}... (≈ 15–40 s)", spinner="dots"):
        caminhos, achados = s.ag.imagem_da_peca(peca_id, proporcao=proporcao, quantidade=quantidade, modelo=modelo, tamanho=tamanho)
    for a in achados:
        console.print(f"[{COR[a.nivel]}]{a.nivel.value}: {esc(a.mensagem)}[/]")
    for c in caminhos:
        console.print(f"[green]🖼  Imagem salva:[/] {esc(caminho_curto(c))}")
    console.print(f"[{SUAVE}]Imagem gerada por IA: use para conceitos e campanhas gerais, nunca para representar a unidade vendida.[/]")
    return caminhos


def fluxo_imagem(s: Sessao, peca_id: str | None = None) -> None:
    titulo_secao("🎨 Gerar imagem de uma peça")
    peca_id = peca_id or _ou_voltar(escolher_peca(s, "Para qual peça?", filtro=lambda i: not (i["frente"] == "venda" and i.get("produto_id"))))
    peca, brief, _, _ = s.ag.registro.carregar_modelos(peca_id)
    if b := bloqueio_imagem(brief):
        raise ErroAgente(b.mensagem)
    if not peca.prompt_imagem:
        raise ErroAgente("Esta peça não tem prompt de imagem (provavelmente exige foto real).")
    console.print(Panel(esc(peca.prompt_imagem), title="Prompt da peça", border_style=SUAVE, box=box.ROUNDED))

    padrao = _proporcao_da_peca(peca, brief)
    proporcao = s.p.escolher(
        "Proporção:",
        [("4:5 · feed", "4:5"), ("9:16 · Reels/Stories", "9:16"), ("1:1 · quadrado", "1:1")]
        + ([(f"{padrao} · da direção de arte", padrao)] if padrao not in ("4:5", "9:16", "1:1") else []),
        padrao=padrao,
    )
    tamanho = s.p.escolher(
        "Resolução:",
        [("Padrão (~1K)", "padrao", "Mais barato · bom para validar a ideia"), ("2K", "2K", "Para a versão final (passa de 1080 px) · ~1,5x o custo"), ("4K", "4K", "Máxima · ~2,3x o custo")],
        padrao="padrao",
    )
    tamanho = None if tamanho == "padrao" else tamanho
    modelo = s.p.escolher("Modelo de imagem:", [(nome_modelo(m), m, d) for m, d in MODELOS_IMAGEM], padrao=s.modelo_imagem)
    quantidade = s.p.escolher("Quantas variações?", [(str(n), n) for n in (1, 2, 3, 4)], padrao=1)
    confirmar_custo(s, estimar_imagem(modelo, tamanho, quantidade), modelo)
    caminhos = _gerar_imagem(s, peca_id, proporcao=proporcao, tamanho=tamanho, quantidade=quantidade, modelo=modelo)
    if caminhos and s.p.confirmar("Abrir a imagem agora?", padrao=True):
        abrir_arquivo(caminhos[0])


def fluxo_imagem_livre(s: Sessao) -> None:
    titulo_secao("✨ Imagem livre")
    console.print(f"[{SUAVE}]Dica: descreva a cena em inglês (assunto, composição, luz, fundo). Regras de marca são acrescentadas automaticamente.[/]")
    prompt = s.p.texto("Prompt:", obrigatorio=True)
    proporcao = s.p.escolher("Proporção:", [("4:5 · feed", "4:5"), ("9:16 · Reels/Stories", "9:16"), ("1:1 · quadrado", "1:1")])
    tamanho = s.p.escolher("Resolução:", [("Padrão (~1K)", "padrao"), ("2K", "2K"), ("4K", "4K")], padrao="padrao")
    tamanho = None if tamanho == "padrao" else tamanho
    modelo = s.p.escolher("Modelo de imagem:", [(nome_modelo(m), m, d) for m, d in MODELOS_IMAGEM], padrao=s.modelo_imagem)
    confirmar_custo(s, estimar_imagem(modelo, tamanho), modelo)
    with console.status(f"Gerando imagem com {nome_modelo(modelo)}...", spinner="dots"):
        caminhos, achados = s.ag.imagem_livre(prompt, proporcao=proporcao, modelo=modelo, tamanho=tamanho)
    for a in achados:
        console.print(f"[{COR[a.nivel]}]{a.nivel.value}: {esc(a.mensagem)}[/]")
    for c in caminhos:
        console.print(f"[green]🖼  Imagem salva:[/] {esc(caminho_curto(c))}")
    if caminhos and s.p.confirmar("Abrir a imagem agora?", padrao=True):
        abrir_arquivo(caminhos[0])


def _proxima_segunda() -> date:
    hoje = date.today()
    return hoje + timedelta(days=(7 - hoje.weekday()) % 7 or 7)


def fluxo_planejar(s: Sessao) -> None:
    titulo_secao("📅 Planejar calendário")
    semanas = s.p.escolher("Quantas semanas?", [("1 semana", 1), ("2 semanas", 2), ("4 semanas (mês)", 4)], padrao=4)
    inicio = s.p.texto("Data de início (AAAA-MM-DD):", padrao=_proxima_segunda().isoformat(), validar=_validar_data)
    por_semana = s.p.escolher("Publicações de feed/Reels por semana:", [("3", 3), ("4 (recomendado no briefing)", 4), ("5", 5)], padrao=4)
    foco = s.p.texto("Foco ou observações (opcional — campanha, sazonalidade, prioridade):")
    confirmar_custo(s, estimar_texto("planejar", s.modelo_texto, semanas=semanas), s.modelo_texto)
    with console.status(f"Planejando {semanas} semana(s) com {nome_modelo(s.modelo_texto)}...", spinner="dots"):
        r = s.ag.planejar(semanas=semanas, inicio=date.fromisoformat(inicio), publicacoes_semana=por_semana, foco=foco or None, modelo=s.modelo_texto)
    mostrar_calendario(r)
    if s.p.confirmar("Gerar as peças deste calendário agora?", padrao=False):
        fluxo_lote(s, cal_id=r.id)


def fluxo_lote(s: Sessao, cal_id: str | None = None) -> None:
    titulo_secao("📦 Gerar peças de um calendário")
    if cal_id is None:
        cals = sorted(s.ag.registro.dados["calendarios"].values(), key=lambda c: c["criado_em"], reverse=True)
        if not cals:
            raise Aviso("Nenhum calendário salvo. Use 'Planejar calendário' primeiro.")
        cal_id = _ou_voltar(
            s.p.escolher("Qual calendário?", [(f"{c['id']}  ·  {c['periodo']}", c["id"], f"{c['itens']} itens") for c in cals] + [("↩  Voltar", "__voltar__")])
        )

    _, cal = s.ag.registro.carregar_calendario(cal_id)
    origens = {p.get("origem") for p in s.ag.registro.listar()}
    ja = [n for n in range(1, len(cal.itens) + 1) if f"{cal_id}#{n}" in origens]
    vendas = [n for n, i in enumerate(cal.itens, 1) if i.pilar == Pilar.conversao and n not in ja]
    generico_vendas = False
    if vendas:
        generico_vendas = s.p.confirmar(f"Há {len(vendas)} item(ns) de venda. Gerar como conteúdo genérico (sem unidade)?", padrao=False)
    pendentes = [n for n in range(1, len(cal.itens) + 1) if n not in ja and (generico_vendas or n not in vendas)]
    console.print(f"[{SUAVE}]{len(cal.itens)} itens · {len(ja)} já gerados · {len(pendentes)} a gerar[/]")
    if not pendentes:
        console.print("[green]✓ Todas as peças possíveis deste calendário já foram geradas.[/]")
        return
    quantos = s.p.escolher("Quantas gerar agora?", [(f"Todas ({len(pendentes)})", len(pendentes))] + [(str(n), n) for n in range(1, min(len(pendentes), 5))], padrao=len(pendentes))
    confirmar_custo(s, estimar_texto("criar", s.modelo_texto, vezes=quantos), s.modelo_texto)

    t = Table(box=box.ROUNDED, expand=True, header_style=SUAVE, title=f"Lote {cal_id}")
    for col, kw in (("#", {"width": 3}), ("Tema", {"ratio": 3}), ("Resultado", {"no_wrap": True}), ("Bloq.", {"width": 5})):
        t.add_column(col, overflow="fold", **kw)
    feitos = 0
    with console.status("Gerando peças...", spinner="dots") as st:
        for n, item, res in s.ag.lote(cal_id, generico_vendas=generico_vendas, modelo=s.modelo_texto):
            if isinstance(res, ResultadoPeca):
                feitos += 1
                bloq = sum(1 for a in res.achados if a.nivel == Nivel.bloqueio)
                console.print(f"[green]✓[/] {n}. {esc(item.tema[:80])} → [bold]{res.id}[/]")
                t.add_row(str(n), esc(item.tema), f"[green]{res.id}[/]", f"[red]{bloq}[/]" if bloq else "0")
                if feitos >= quantos:
                    break
                st.update(f"Gerando peças... ({feitos}/{quantos})")
            elif not res.startswith("já gerado"):
                t.add_row(str(n), esc(item.tema), f"[yellow]{esc(res)}[/]", "-")
    console.print(t)


def fluxo_adaptar(s: Sessao, peca_id: str | None = None) -> None:
    titulo_secao("🔀 Adaptar peça")
    peca_id = peca_id or _ou_voltar(escolher_peca(s, "Qual peça adaptar?"))
    atual = Formato(s.ag.registro.entrada(peca_id)["formato"])
    formato = s.p.escolher(f"Adaptar de {DESC_FORMATO[atual][0]} para:", [(DESC_FORMATO[f][0], f, DESC_FORMATO[f][1]) for f in Formato if f != atual])
    obs = s.p.texto("Observações para a adaptação (opcional):")
    confirmar_custo(s, estimar_texto("adaptar", s.modelo_texto), s.modelo_texto)
    with console.status(f"Adaptando para {formato.value}...", spinner="dots"):
        r = s.ag.adaptar(peca_id, formato, observacoes=obs or None, modelo=s.modelo_texto)
    mostrar_peca(r)
    if s.p.confirmar("Abrir o documento da nova peça?", padrao=False):
        abrir_arquivo(r.caminho_md)


def fluxo_revisar(s: Sessao, peca_id: str | None = None) -> None:
    titulo_secao("🔍 Revisar com IA")
    if peca_id:
        alvo = peca_id
    else:
        origem = s.p.escolher(
            "O que revisar?",
            [("Uma peça registrada", "peca"), ("Colar um texto", "texto", "Ex.: legenda escrita à mão ou de outra pessoa"), ("Um arquivo .txt ou .md", "arquivo"), ("↩  Voltar", "__voltar__")],
        )
        _ou_voltar(origem)
        if origem == "peca":
            alvo = _ou_voltar(escolher_peca(s, "Qual peça?"))
        elif origem == "texto":
            alvo = s.p.texto("Cole o texto:", obrigatorio=True, multilinha=True)
        else:
            alvo = s.p.caminho("Caminho do arquivo:")
    contexto = s.p.texto("Contexto extra para o revisor (opcional):")
    confirmar_custo(s, estimar_texto("revisar", s.modelo_texto), s.modelo_texto)
    with console.status("Revisando...", spinner="dots"):
        rev, achados, caminho = s.ag.revisar(alvo, contexto_extra=contexto or None, modelo=s.modelo_texto)
    mostrar_revisao(rev, achados, caminho)
    if s.p.confirmar("Abrir a revisão completa?", padrao=False):
        abrir_arquivo(caminho)


def fluxo_reverificar(s: Sessao, peca_id: str | None = None) -> None:
    titulo_secao("🔄 Reverificar regras")
    peca_id = peca_id or _ou_voltar(escolher_peca(s, "Qual peça?"))
    r = s.ag.reverificar(peca_id)
    mostrar_peca(r)


def fluxo_analisar(s: Sessao) -> None:
    titulo_secao("📊 Analisar resultados")
    console.print(f"[{SUAVE}]CSV com colunas como peca_id, data, alcance, salvamentos, compartilhamentos, conversas_qualificadas... (veja exemplos/resultados_exemplo.csv)[/]")
    caminho = s.p.caminho("Arquivo CSV:")
    confirmar_custo(s, estimar_texto("analisar", s.modelo_texto), s.modelo_texto)
    with console.status("Analisando...", spinner="dots"):
        an, _, saida = s.ag.analisar(Path(caminho), modelo=s.modelo_texto)
    mostrar_analise(an, saida)
    if s.p.confirmar("Abrir a análise completa?", padrao=False):
        abrir_arquivo(saida)


def _painel_peca(s: Sessao, peca_id: str) -> Panel:
    e = s.ag.registro.entrada(peca_id)
    g = Table.grid(padding=(0, 2))
    g.add_column(style=SUAVE, no_wrap=True)
    g.add_column()
    g.add_row("Status", selo_status(e["status"]))
    g.add_row("Formato", f"{e['formato']} · {e['pilar']} · frente {e['frente']} · público {e['publico']}")
    g.add_row("Versão", f"v{e['versao_atual']}" + (f"  [red]{e['bloqueios']} bloqueio(s)[/]" if e.get("bloqueios") else "  [green]sem bloqueios[/]"))
    if e.get("origem"):
        g.add_row("Origem", esc(e["origem"]))
    g.add_row("Imagens", str(len(e.get("imagens", []))))
    if e.get("publicacao"):
        pub = e["publicacao"]
        g.add_row("Publicação", f"{pub['data']} · {esc(pub.get('url_ou_id') or '—')}")
    ultimo = e["historico"][-1]
    g.add_row("Último evento", f"{ultimo['status']} por {esc(str(ultimo['responsavel']))} em {ultimo['em'][:16].replace('T', ' ')}")
    return Panel(g, title=f"[bold]{peca_id}[/]  {esc(e['titulo'][:70])}", border_style=DESTAQUE, box=box.ROUNDED, padding=(1, 2))


def fluxo_acoes_peca(s: Sessao, peca_id: str) -> None:
    while True:
        s.limpar()
        console.print(_painel_peca(s, peca_id))
        e = s.ag.registro.entrada(peca_id)
        st = e["status"]
        venda_real = e["frente"] == "venda" and e.get("produto_id")
        opcoes = [("👁  Ver resumo", "ver"), ("📄  Abrir documento (.md)", "abrir")]
        if e.get("imagens"):
            opcoes.append(("🖼  Abrir pasta de imagens", "imagens"))
        if st in ("ideia", "em_criacao", "revisao"):
            opcoes.append(("✅  Aprovar para publicação", "aprovar", "Exige seu nome e zero bloqueios"))
        if st == "aprovado":
            opcoes.append(("📢  Registrar publicação", "publicar", "Você publica manualmente; aqui só registra"))
        if st == "publicado":
            opcoes.append(("📈  Marcar como analisada", "analisado"))
        opcoes += [
            ("🔄  Reverificar regras (grátis)", "reverificar"),
            ("🔍  Revisar com IA", "revisar"),
            ("🔀  Adaptar para outro formato", "adaptar"),
        ]
        if not venda_real:
            opcoes.append(("🎨  Gerar imagem", "imagem"))
        if st != "arquivado":
            opcoes.append(("🗄  Arquivar", "arquivar"))
        opcoes.append(("↩  Voltar", "voltar"))

        acao = s.p.escolher("O que fazer com esta peça?", opcoes)
        if acao == "voltar":
            return
        try:
            _executar_acao_peca(s, peca_id, acao)
        except Voltar:
            continue
        except Aviso as aviso:
            console.print(f"[yellow]⚠ {esc(str(aviso))}[/]")
        except ERROS as erro:
            console.print(painel_erro(str(erro)))
        s.p.pausar()


def _pedir_responsavel(s: Sessao) -> str:
    nome = s.p.texto("Seu nome (responsável):", padrao=s.responsavel or "", obrigatorio=True)
    s.responsavel = nome
    return nome


def _executar_acao_peca(s: Sessao, peca_id: str, acao: str) -> None:
    reg = s.ag.registro
    if acao == "ver":
        mostrar_peca(_resultado_registrado(s, peca_id))
    elif acao == "abrir":
        abrir_arquivo(reg.dir_peca(peca_id) / f"v{reg.entrada(peca_id)['versao_atual']}.md")
    elif acao == "imagens":
        abrir_arquivo(reg.dir_peca(peca_id) / "imagens")
    elif acao == "aprovar":
        r = _resultado_registrado(s, peca_id)
        pend = len(r.peca.checklist_validacao)
        console.print(f"[yellow]Antes de aprovar, confira os {pend} itens do checklist de validação no documento da peça.[/]")
        nome = _pedir_responsavel(s)
        if not s.p.confirmar("Confirma que revisou o checklist e aprova a publicação?", padrao=False):
            raise Voltar()
        reg.atualizar_status(peca_id, StatusPeca.aprovado, nome)
        console.print(f"[green]✅ {peca_id} aprovada por {esc(nome)}.[/]")
    elif acao == "publicar":
        data = s.p.texto("Data da publicação (AAAA-MM-DD):", padrao=date.today().isoformat(), validar=_validar_data)
        url = s.p.texto("URL ou ID do post/anúncio (opcional):")
        campanha = s.p.texto("Campanha (opcional):")
        criativo = s.p.texto("Criativo/variação usada (opcional — ex.: principal, Variação A):")
        nome = _pedir_responsavel(s)
        reg.registrar_publicacao(peca_id, url=url or None, data=data, campanha=campanha or None, criativo=criativo or None, responsavel=nome)
        console.print(f"[green]📢 Publicação registrada em {data}.[/]")
    elif acao == "analisado":
        reg.atualizar_status(peca_id, StatusPeca.analisado, _pedir_responsavel(s))
        console.print("[green]📈 Marcada como analisada.[/]")
    elif acao == "arquivar":
        if not s.p.confirmar("Arquivar esta peça?", padrao=False):
            raise Voltar()
        reg.atualizar_status(peca_id, StatusPeca.arquivado, s.responsavel or "responsável")
        console.print("[green]🗄 Peça arquivada.[/]")
    elif acao == "reverificar":
        fluxo_reverificar(s, peca_id)
    elif acao == "revisar":
        fluxo_revisar(s, peca_id)
    elif acao == "adaptar":
        fluxo_adaptar(s, peca_id)
    elif acao == "imagem":
        fluxo_imagem(s, peca_id)


def fluxo_pecas(s: Sessao) -> None:
    while True:
        s.limpar()
        titulo_secao("📋 Peças e aprovação")
        filtro = s.extras.get("filtro_status")
        itens = s.ag.registro.listar(status=filtro)
        if not s.ag.registro.listar():
            raise Aviso("Nenhuma peça ainda. Use 'Criar peça' ou 'Planejar calendário'.")
        console.print(tabela_pecas(itens))
        opcoes = [
            (f"{i['id']}  {i['formato']:<9} {i['titulo'][:58]}", i["id"], f"{i['status']} · {i['pilar']} · {i['frente']} · v{i['versao_atual']}")
            for i in itens
        ]
        opcoes += [
            Separador("───"),
            (f"🔎  Filtrar por status (atual: {filtro or 'todos'})", "__filtro__"),
            ("↩  Voltar ao menu", "__voltar__"),
        ]
        escolha = s.p.escolher("Escolha uma peça:", opcoes)
        if escolha == "__voltar__":
            raise Voltar()
        if escolha == "__filtro__":
            novo = s.p.escolher(
                "Mostrar:", [("Todos", "__todos__")] + [(NOME_STATUS[x], x) for x in ORDEM_STATUS], padrao=filtro or "__todos__"
            )
            s.extras["filtro_status"] = None if novo == "__todos__" else novo
            continue
        fluxo_acoes_peca(s, escolha)


def fluxo_modelo(s: Sessao) -> None:
    titulo_secao("🧠 Modelo de texto")
    opcoes = [(nome_modelo(m), m, d) for m, d in MODELOS_TEXTO] + [("Outro (digitar ID do OpenRouter)", "__outro__")]
    escolha = s.p.escolher("Qual modelo usar nesta sessão?", opcoes, padrao=s.modelo_texto)
    if escolha == "__outro__":
        escolha = s.p.texto("ID do modelo (ex.: anthropic/claude-opus-5.5):", obrigatorio=True)
    s.modelo_texto = escolha
    console.print(f"[green]Modelo de texto: {esc(nome_modelo(escolha))}[/] [dim](só nesta sessão; para mudar o padrão, edite MODELO_TEXTO no .env)[/]")


def fluxo_config(s: Sessao) -> None:
    titulo_secao("🧰 Pendências e configuração")
    mostrar_pendencias(s.ag)
    acao = s.p.escolher(
        "Ações:",
        [
            (f"🎨  Modelo de imagem: {nome_modelo(s.modelo_imagem)}", "imagem"),
            ("📝  Abrir dados/negocio.json", "negocio", "Preencha só informações confirmadas; null = pendente"),
            ("📦  Abrir dados/estoque.json", "estoque", "Veja dados/estoque.exemplo.json para o formato"),
            ("📂  Abrir pasta de saída", "saida"),
            ("↩  Voltar", "__voltar__"),
        ],
    )
    _ou_voltar(acao)
    if acao == "imagem":
        s.modelo_imagem = s.p.escolher("Modelo de imagem nesta sessão:", [(nome_modelo(m), m, d) for m, d in MODELOS_IMAGEM], padrao=s.modelo_imagem)
        console.print(f"[green]Modelo de imagem: {esc(nome_modelo(s.modelo_imagem))}[/]")
    elif acao == "negocio":
        abrir_arquivo(s.ag.cfg.dir_dados / "negocio.json")
        console.print(f"[{SUAVE}]Depois de salvar, use 'Reverificar regras' nas peças para atualizar as pendências.[/]")
    elif acao == "estoque":
        abrir_arquivo(s.ag.cfg.dir_dados / "estoque.json")
    elif acao == "saida":
        abrir_arquivo(s.ag.cfg.dir_saida)


FLUXOS: dict[str, Callable[[Sessao], None]] = {
    "planejar": fluxo_planejar,
    "lote": fluxo_lote,
    "criar": fluxo_criar,
    "adaptar": fluxo_adaptar,
    "imagem": fluxo_imagem,
    "imagem_livre": fluxo_imagem_livre,
    "revisar": fluxo_revisar,
    "reverificar": fluxo_reverificar,
    "pecas": fluxo_pecas,
    "analisar": fluxo_analisar,
    "modelo": fluxo_modelo,
    "config": fluxo_config,
}


# ====================================================================== laço principal
def executar_menu(sessao: Sessao | None = None) -> None:
    s = sessao or Sessao.nova()
    while True:
        s.recarregar()
        s.limpar()
        console.print(cabecalho(s))
        try:
            escolha = s.p.escolher("O que você quer fazer?", opcoes_menu(s))
        except Voltar:
            break
        if escolha == "sair":
            break
        try:
            FLUXOS[escolha](s)
        except Voltar:
            continue
        except Aviso as aviso:
            console.print(f"[yellow]⚠ {esc(str(aviso))}[/]")
        except KeyboardInterrupt:
            console.print("[yellow]Operação interrompida.[/]")
        except ERROS as erro:
            console.print(painel_erro(str(erro)))
        s.p.pausar()

    custo = s.ag.cliente.uso_acumulado["custo_usd"]
    console.print(
        Panel(
            f"Até logo! Custo desta sessão ≈ [bold]{em_reais(custo, s.ag.cfg.cotacao_dolar)}[/] [{SUAVE}](US$ {custo:.4f})[/]",
            border_style=DESTAQUE,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )
