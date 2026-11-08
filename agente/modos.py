"""Os cinco modos de operação do agente (planejar, criar, adaptar, revisar, analisar) + imagens."""

from __future__ import annotations

import csv
import re
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agente import prompts, render
from agente.armazenamento import Registro
from agente.cadastro import PALETA_PROVISORIA
from agente.design import estilo_padrao
from agente.config import Config, carregar_config
from agente.contexto import Contexto, carregar_contexto
from agente.guardrails import (
    Achado,
    Nivel,
    bloqueio_imagem,
    verificar_peca,
    verificar_prompt_imagem,
    verificar_texto,
)
from agente.imagem import PROPORCOES_VALIDAS, gerar_imagens
from agente.llm import ClienteOpenRouter
from agente.schemas import (
    FRENTE_POR_PILAR,
    PROPORCAO_POR_FORMATO,
    Analise,
    Aparelho,
    Brief,
    Calendario,
    Formato,
    Frente,
    Peca,
    Pilar,
    Revisao,
)


class ErroAgente(RuntimeError):
    pass


@dataclass
class ResultadoPeca:
    id: str
    versao: int
    peca: Peca
    brief: Brief
    achados: list[Achado]
    caminho_md: Path


@dataclass
class ResultadoCalendario:
    id: str
    calendario: Calendario
    distribuicao: dict
    avisos: list[str]
    caminho: Path


class Agente:
    def __init__(self, cfg: Config, cliente: ClienteOpenRouter, ctx: Contexto, registro: Registro):
        self.cfg, self.cliente, self.ctx, self.registro = cfg, cliente, ctx, registro

    @classmethod
    def padrao(cls) -> "Agente":
        cfg = carregar_config()
        return cls(cfg, ClienteOpenRouter(cfg), carregar_contexto(cfg), Registro(cfg.dir_saida))

    # ================================================================== validação de entrada
    def validar_brief(self, brief: Brief, *, generico: bool = False) -> Aparelho | None:
        """Regras do briefing que impedem criar a peça (seção 12: pedir informação crítica)."""
        if brief.produto_id:
            produto = self.ctx.produto(brief.produto_id)
            if not produto:
                raise ErroAgente(f"Produto {brief.produto_id} não existe em dados/estoque.json.")
            if not produto.disponivel:
                raise ErroAgente(f"Produto {brief.produto_id} está indisponível: não anunciar aparelhos indisponíveis.")
            if brief.frente != Frente.venda:
                raise ErroAgente("Produto do estoque só pode ser usado em peças da frente 'venda'.")
            return produto
        if brief.pilar == Pilar.conversao and not generico:
            raise ErroAgente(
                "Oferta de venda exige uma unidade real (--produto ID do estoque). "
                "Para conteúdo de venda genérico, sem unidade, preço ou disponibilidade, use --generico."
            )
        return None

    # ================================================================== CRIAR
    def criar(self, brief: Brief, *, generico: bool = False, modelo: str | None = None) -> ResultadoPeca:
        produto = self.validar_brief(brief, generico=generico)
        sistema = prompts.montar_sistema(self.ctx)
        peca = self.cliente.gerar_estruturado(sistema, prompts.pedido("criar", prompts.usuario_criar(brief, produto)), Peca, modelo=modelo)
        return self._finalizar_peca(peca, brief, produto, modelo)

    def _finalizar_peca(self, peca: Peca, brief: Brief, produto: Aparelho | None, modelo: str | None, peca_id: str | None = None) -> ResultadoPeca:
        if bloqueio_imagem(brief):
            peca.prompt_imagem = None  # unidade real: só foto real, independentemente do que o modelo devolveu
        achados = verificar_peca(peca, brief, negocio=self.ctx.negocio, produto=produto)
        peca_id = peca_id or self.registro.novo_id(brief.pilar)
        versao = self.registro.proxima_versao(peca_id)
        nome_modelo = modelo or self.cfg.modelo_texto
        md = render.peca_md(peca_id, versao, peca, brief, achados, nome_modelo)
        self.registro.salvar_peca(peca_id, peca, brief, achados, modelo=nome_modelo, markdown=md)
        return ResultadoPeca(peca_id, versao, peca, brief, achados, self.registro.dir_peca(peca_id) / f"v{versao}.md")

    def reverificar(self, peca_id: str) -> ResultadoPeca:
        """Roda de novo as verificações (sem LLM) e grava nova versão — útil após mudar regras, negocio.json ou estoque."""
        peca, brief, _, doc = self.registro.carregar_modelos(peca_id)
        produto = self.ctx.produto(brief.produto_id) if brief.produto_id else None
        if brief.produto_id and (not produto or not produto.disponivel):
            raise ErroAgente(f"Produto {brief.produto_id} não está mais disponível no estoque.")
        return self._finalizar_peca(peca, brief, produto, doc.get("modelo"), peca_id=peca_id)

    def reverificar_todas(self, status: tuple[str, ...] = ("revisao",)) -> list[tuple[str, ResultadoPeca | str]]:
        """Reverifica (sem custo) todas as peças nos status indicados. Erros não interrompem as demais."""
        self.ctx = carregar_contexto(self.cfg)  # pega negocio.json/estoque.json recém-editados
        resultados: list[tuple[str, ResultadoPeca | str]] = []
        for item in self.registro.listar():
            if item["status"] not in status:
                continue
            try:
                resultados.append((item["id"], self.reverificar(item["id"])))
            except ErroAgente as e:
                resultados.append((item["id"], str(e)))
        return resultados

    def pecas_do_produto(self, produto_id: str) -> list[dict]:
        return [p for p in self.registro.listar() if p.get("produto_id") == produto_id]

    # ================================================================== ADAPTAR
    def adaptar(self, peca_id: str, formato: Formato, *, observacoes: str | None = None, modelo: str | None = None) -> ResultadoPeca:
        peca_orig, brief_orig, _, _ = self.registro.carregar_modelos(peca_id)
        if formato == brief_orig.formato:
            raise ErroAgente("O formato de destino é igual ao original.")
        brief = brief_orig.model_copy(update={"formato": formato, "origem": peca_id})
        produto = self.validar_brief(brief, generico=True)
        sistema = prompts.montar_sistema(self.ctx)
        usuario = prompts.usuario_adaptar(peca_orig.model_dump_json(), brief_orig, formato.value, observacoes)
        peca = self.cliente.gerar_estruturado(sistema, prompts.pedido("adaptar", usuario), Peca, modelo=modelo)
        return self._finalizar_peca(peca, brief, produto, modelo)

    # ================================================================== PLANEJAR
    def planejar(
        self,
        *,
        semanas: int = 4,
        inicio: date | None = None,
        publicacoes_semana: int = 4,
        foco: str | None = None,
        modelo: str | None = None,
    ) -> ResultadoCalendario:
        inicio = inicio or date.today()
        historico = "\n".join(f"- {p['titulo']} ({p['pilar']}/{p['formato']})" for p in self.registro.listar()[:40]) or None
        sistema = prompts.montar_sistema(self.ctx)
        usuario = prompts.usuario_planejar(semanas, inicio.isoformat(), publicacoes_semana, foco, historico)
        cal = self.cliente.gerar_estruturado(sistema, prompts.pedido("planejar", usuario), Calendario, modelo=modelo)

        avisos = self.avisos_calendario(cal, esperado=semanas * publicacoes_semana)
        distribuicao = render.distribuicao_pilares(cal)
        cal_id = self.registro.novo_id_calendario()
        md = render.calendario_md(cal_id, cal, distribuicao, avisos)
        caminho = self.registro.salvar_calendario(cal_id, cal, md, distribuicao)
        return ResultadoCalendario(cal_id, cal, distribuicao, avisos, caminho)

    def avisos_calendario(self, cal: Calendario, esperado: int) -> list[str]:
        avisos = []
        if len(cal.itens) != esperado:
            avisos.append(f"Calendário tem {len(cal.itens)} itens; esperado {esperado}.")
        for n, i in enumerate(cal.itens, 1):
            if FRENTE_POR_PILAR[i.pilar] != i.frente:
                avisos.append(f"Item {n}: pilar {i.pilar.value} com frente {i.frente.value} (esperado {FRENTE_POR_PILAR[i.pilar].value}).")
            try:
                date.fromisoformat(i.data)
            except ValueError:
                avisos.append(f"Item {n}: data inválida '{i.data}'.")
        if not self.ctx.estoque_disponivel:
            vendas = [n for n, i in enumerate(cal.itens, 1) if i.pilar == Pilar.conversao]
            if vendas:
                avisos.append(f"Estoque vazio, mas há itens de conversão ({vendas}); só produza-os como conteúdo genérico ou após cadastrar unidades.")
        return avisos

    def lote(self, cal_ref: str, *, limite: int | None = None, generico_vendas: bool = False, refazer: bool = False, modelo: str | None = None):
        """Gera peças para os itens de um calendário. Rende (n, item, ResultadoPeca | str de pulo/erro).

        Itens que já viraram peça (origem "C-...#n") são pulados, então um lote interrompido pode ser retomado.
        """
        cal_id, cal = self.registro.carregar_calendario(cal_ref)
        ja_gerados = {p["origem"]: p["id"] for p in self.registro.listar() if p.get("origem")}
        for n, item in enumerate(cal.itens[:limite] if limite else cal.itens, 1):
            if not refazer and f"{cal_id}#{n}" in ja_gerados:
                yield n, item, f"já gerado: {ja_gerados[f'{cal_id}#{n}']}"
                continue
            brief = Brief(
                objetivo=f"{item.tema} — {item.justificativa}",
                pilar=item.pilar,
                frente=item.frente,
                publico=item.publico,
                etapa=item.etapa,
                formato=item.formato,
                cta=item.cta,
                serie=item.serie,
                referencias=f"Gancho sugerido: {item.gancho_sugerido}. Data prevista: {item.data}.",
                origem=f"{cal_id}#{n}",
            )
            if item.pilar == Pilar.conversao and not generico_vendas:
                yield n, item, "pulado: item de venda exige unidade do estoque (use `criar --produto` ou --generico-vendas)"
                continue
            try:
                yield n, item, self.criar(brief, generico=True, modelo=modelo)
            except Exception as e:  # um item com erro não interrompe o lote
                yield n, item, f"erro: {e}"

    # ================================================================== REVISAR
    def revisar(self, alvo: str, *, contexto_extra: str | None = None, modelo: str | None = None, responsavel: str = "agente"):
        """alvo = ID de peça registrada, caminho de arquivo de texto ou o próprio texto."""
        peca_id = alvo if alvo in self.registro.dados["pecas"] else None
        if peca_id:
            peca, brief, _, doc = self.registro.carregar_modelos(peca_id)
            produto = self.ctx.produto(brief.produto_id) if brief.produto_id else None
            achados = verificar_peca(peca, brief, negocio=self.ctx.negocio, produto=produto)
            texto = (self.registro.dir_peca(peca_id) / f"v{doc['versao']}.md").read_text(encoding="utf-8")
            rotulo = f"{peca_id} v{doc['versao']}"
        else:
            p = _como_arquivo(alvo)
            texto = p.read_text(encoding="utf-8") if p else alvo
            achados = verificar_texto(texto, negocio=self.ctx.negocio)
            rotulo = p.name if p else "texto avulso"

        sistema = prompts.montar_sistema(self.ctx)
        usuario = prompts.usuario_revisar(texto, [a.to_dict() for a in achados], contexto_extra)
        rev = self.cliente.gerar_estruturado(sistema, prompts.pedido("revisar", usuario), Revisao, modelo=modelo)
        if any(a.nivel == Nivel.bloqueio for a in achados) and rev.veredito != "bloqueado":
            rev.veredito = "bloqueado"  # regra determinística prevalece sobre o modelo
        caminho = self.registro.salvar_revisao(rotulo, {**rev.model_dump(mode="json"), "achados": [a.to_dict() for a in achados]}, render.revisao_md(rotulo, rev, achados))
        return rev, achados, caminho

    # ================================================================== ANALISAR
    def analisar(self, csv_path: Path, *, modelo: str | None = None):
        linhas, colunas = ler_resultados_csv(csv_path)
        if not linhas:
            raise ErroAgente("CSV sem linhas.")
        # Completa pilar/frente/formato a partir do registro quando a planilha só tem o ID.
        for ln in linhas:
            pid = ln.get("peca_id")
            if pid and pid in self.registro.dados["pecas"]:
                ent = self.registro.dados["pecas"][pid]
                for campo in ("pilar", "frente", "formato"):
                    if not ln.get(campo):
                        ln[campo] = ent[campo]
        agregados = agregar(linhas)
        sistema = prompts.montar_sistema(self.ctx)
        an = self.cliente.gerar_estruturado(sistema, prompts.pedido("analisar", prompts.usuario_analisar(agregados, linhas, colunas)), Analise, modelo=modelo)
        pasta = self.registro.dir / "analises"
        pasta.mkdir(parents=True, exist_ok=True)
        nome = f"A-{date.today():%Y%m%d}-{len(list(pasta.glob('*.md'))) + 1:02d}"
        (pasta / f"{nome}.json").write_text(json.dumps({"analise": an.model_dump(mode="json"), "agregados": agregados}, ensure_ascii=False, indent=2), encoding="utf-8")
        caminho = pasta / f"{nome}.md"
        caminho.write_text(render.analise_md(an, agregados), encoding="utf-8")
        return an, agregados, caminho

    # ================================================================== IMAGENS
    def imagem_da_peca(
        self,
        peca_id: str,
        *,
        proporcao: str | None = None,
        quantidade: int = 1,
        modelo: str | None = None,
        tamanho: str | None = None,
        referencias: list[Path] | None = None,
        estilo: str = "auto",
    ) -> tuple[list[Path], list[Achado]]:
        peca, brief, _, _ = self.registro.carregar_modelos(peca_id)
        if b := bloqueio_imagem(brief):
            raise ErroAgente(b.mensagem)
        if not peca.prompt_imagem:
            raise ErroAgente("A peça não tem prompt de imagem (provavelmente exige foto real).")
        proporcao = proporcao or _proporcao_da_peca(peca, brief)
        achados = verificar_prompt_imagem(peca.prompt_imagem, brief=brief)
        caminhos = []
        modelo = modelo or self.cfg.modelo_imagem
        paleta = self.ctx.negocio.get("paleta_cores") or PALETA_PROVISORIA  # fundo da foto casa com a arte
        if estilo in ("auto", "", None):  # mesmo estilo que a arte vai usar (design.estilo_padrao)
            estilo = estilo_padrao(brief.formato, brief.frente, brief.produto_id)
        for _ in range(quantidade):
            for img in gerar_imagens(self.cliente, peca.prompt_imagem, proporcao=proporcao, modelo=modelo, tamanho=tamanho, referencias=referencias, paleta=paleta, estilo=estilo):
                caminhos.append(self.registro.salvar_imagem(peca_id, img.dados, img.extensao, img.prompt_final, modelo, proporcao))
        return caminhos, achados

    def imagem_livre(self, prompt: str, *, proporcao: str = "4:5", quantidade: int = 1, modelo: str | None = None, tamanho: str | None = None, referencias: list[Path] | None = None):
        achados = verificar_prompt_imagem(prompt)
        modelo = modelo or self.cfg.modelo_imagem
        caminhos = []
        for _ in range(quantidade):
            # Prompt livre: mantém o enquadramento que a pessoa descreveu (sem a composição da arte).
            for img in gerar_imagens(self.cliente, prompt, proporcao=proporcao, modelo=modelo, tamanho=tamanho, referencias=referencias, composicao=False):
                caminhos.append(self.registro.salvar_imagem(None, img.dados, img.extensao, img.prompt_final, modelo, proporcao))
        return caminhos, achados


# ====================================================================== utilidades
def _como_arquivo(alvo: str) -> Path | None:
    if len(alvo) > 250 or "\n" in alvo:
        return None
    try:
        p = Path(alvo)
        return p if p.is_file() else None
    except (OSError, ValueError):
        return None


def _proporcao_da_peca(peca: Peca, brief: Brief) -> str:
    p = peca.direcao_arte.proporcao.strip().replace(" ", "")
    return p if p in PROPORCOES_VALIDAS else PROPORCAO_POR_FORMATO[brief.formato]


_RE_MILHAR_PONTO = re.compile(r"^-?[1-9]\d{0,2}(\.\d{3})+$")    # 4.200 / 1.234.567
_RE_MILHAR_VIRGULA = re.compile(r"^-?[1-9]\d{0,2}(,\d{3})+$")   # 4,200 (exportação em inglês)


def _numero(v: str):
    """Número em formato brasileiro ou americano: 4.200 · 1.234,56 · 75,50 · 1,234.56 · 75.50 · R$ 10 · 12%."""
    v = (v or "").strip().replace("R$", "").replace("US$", "").replace("%", "").replace(" ", "").replace(" ", "")
    if not v:
        return None
    if "," in v and "." in v:
        # O separador que aparece por último é o decimal.
        v = v.replace(".", "").replace(",", ".") if v.rfind(",") > v.rfind(".") else v.replace(",", "")
    elif "," in v:
        v = v.replace(",", "") if _RE_MILHAR_VIRGULA.match(v) else v.replace(",", ".")
    elif "." in v and _RE_MILHAR_PONTO.match(v):
        v = v.replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def ler_resultados_csv(caminho: Path) -> tuple[list[dict], list[str]]:
    texto = Path(caminho).read_text(encoding="utf-8-sig")
    try:
        dialeto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;\t")
    except (csv.Error, IndexError):
        dialeto = csv.excel
    leitor = csv.DictReader(texto.splitlines(), dialect=dialeto)
    linhas = []
    for bruta in leitor:
        ln: dict = {}
        for k, v in bruta.items():
            if k is None:
                continue
            k = k.strip().lower()
            n = _numero(v) if v is not None else None
            ln[k] = n if n is not None and k not in {"peca_id", "data"} else (v or "").strip()
        linhas.append(ln)
    return linhas, list(leitor.fieldnames or [])


def agregar(linhas: list[dict]) -> dict:
    """Somas e médias por pilar, frente e formato (o LLM não faz contas)."""
    numericas = sorted({k for ln in linhas for k, v in ln.items() if isinstance(v, float)})
    saida: dict = {"total_linhas": len(linhas), "metricas": numericas}
    for dim in ("pilar", "frente", "formato"):
        grupos: dict = defaultdict(list)
        for ln in linhas:
            grupos[str(ln.get(dim) or "sem_" + dim)].append(ln)
        saida[f"por_{dim}"] = {
            g: {
                "pecas": len(lns),
                **{
                    m: {"soma": round(sum(vals), 2), "media": round(sum(vals) / len(vals), 2), "n": len(vals)}
                    for m in numericas
                    if (vals := [ln[m] for ln in lns if isinstance(ln.get(m), float)])
                },
            }
            for g, lns in grupos.items()
        }
    return saida
