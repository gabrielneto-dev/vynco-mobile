"""Testes do menu interativo com respostas roteirizadas (sem terminal, sem API)."""

import pytest
from rich.console import Console

from agente import menu
from agente.menu import Perguntas, Separador, Sessao, Voltar, cabecalho, estimar_imagem, estimar_texto, executar_menu
from agente.schemas import Etapa, Formato, Pilar, Publico


class Roteiro(Perguntas):
    """Responde na ordem dada. Em escolhas, confere se a resposta é uma opção válida."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.perguntas_feitas = []

    def _proxima(self, mensagem):
        self.perguntas_feitas.append(mensagem)
        if not self.respostas:
            raise AssertionError(f"Sem resposta roteirizada para: {mensagem}")
        r = self.respostas.pop(0)
        if r is Voltar:
            raise Voltar()
        return r

    def escolher(self, mensagem, opcoes, padrao=None):
        valores = [o[1] for o in opcoes if not isinstance(o, Separador)]
        r = self._proxima(mensagem)
        assert r in valores, f"{r!r} não está entre as opções de '{mensagem}': {valores}"
        return r

    def texto(self, mensagem, padrao="", obrigatorio=False, validar=None, multilinha=False):
        r = self._proxima(mensagem)
        if r is None:
            r = padrao
        if validar:
            assert validar(r) is True, f"Validação falhou para {r!r}"
        return r

    def caminho(self, mensagem, padrao=""):
        return self._proxima(mensagem)

    def confirmar(self, mensagem, padrao=True):
        return self._proxima(mensagem)

    def pausar(self):
        pass


def sessao(agente, respostas):
    return Sessao(ag=agente, p=Roteiro(respostas), modelo_texto="anthropic/claude-haiku-5.5", modelo_imagem="google/gemini-3.1-flash-image", limpar_tela=False)


@pytest.fixture(autouse=True)
def nao_abrir_arquivos(monkeypatch):
    abertos = []
    monkeypatch.setattr(menu, "abrir_arquivo", lambda p: abertos.append(p))
    return abertos


def test_cabecalho_mostra_estado(agente):
    s = sessao(agente, [])
    c = Console(record=True, width=120)
    c.print(cabecalho(s))
    texto = c.export_text()
    for trecho in ("Agente de Conteúdo", "Haiku 5.5", "Nano Banana 2", "chave configurada", "informações pendentes", "vazio", "nenhuma ainda"):
        assert trecho in texto, trecho


def test_estimativas_de_custo():
    # Valores medidos nos testes reais após as otimizações (Sonnet ≈ US$ 0,06–0,08; Haiku ≈ US$ 0,003).
    assert 0.04 < estimar_texto("criar", "anthropic/claude-sonnet-5.5") < 0.09
    assert estimar_texto("criar", "anthropic/claude-haiku-5.5") < 0.005
    assert estimar_texto("criar", "modelo/desconhecido") is None
    assert 0.06 < estimar_imagem("google/gemini-3.1-flash-image") < 0.08
    assert estimar_imagem("google/gemini-3.1-flash-image", "2K", 2) > 0.19


def test_criar_pelo_menu(agente):
    s = sessao(agente, [Pilar.educacao, Formato.carrossel, "Checklist de bateria", Publico.A, Etapa.confianca, "iPhone sem cilada", False, True, True])
    menu.fluxo_criar(s)
    itens = agente.registro.listar()
    assert len(itens) == 1 and itens[0]["formato"] == "carrossel"
    assert agente.registro.carregar(itens[0]["id"])["brief"]["serie"] == "iPhone sem cilada"


def test_criar_venda_com_estoque_vazio_vira_generico(agente):
    s = sessao(agente, [Pilar.conversao, Formato.imagem, "Venda genérica", Publico.A, Etapa.intencao, "-", "__generico__", False, True, False])
    menu.fluxo_criar(s)
    assert agente.registro.listar()[0]["frente"] == "venda"


def test_recusar_custo_volta_sem_criar(agente):
    s = sessao(agente, [Pilar.atracao, Formato.reel, "Tema", Publico.A, Etapa.descoberta, "-", False, False])
    with pytest.raises(Voltar):
        menu.fluxo_criar(s)
    assert agente.registro.listar() == []


def test_aprovar_e_publicar_pelo_submenu(agente):
    r = agente.criar(menu.Brief(objetivo="x", pilar=Pilar.atracao, frente="marca", publico="A", etapa="descoberta", formato="reel"))
    s = sessao(agente, ["aprovar", "Gabriel", True, "publicar", "2026-11-10", "https://instagram.com/p/x", "", "principal", None, "voltar"])
    menu.fluxo_acoes_peca(s, r.id)
    e = agente.registro.entrada(r.id)
    assert e["status"] == "publicado" and e["publicacao"]["criativo"] == "principal"
    assert [h["responsavel"] for h in e["historico"]][-2:] == ["Gabriel", "Gabriel"]


def test_aprovacao_bloqueada_mostra_erro_e_continua(agente, capsys):
    from conftest import peca_exemplo
    from agente.schemas import Peca

    agente.cliente.respostas[Peca] = Peca.model_validate(peca_exemplo(legenda="Compra 100% segura!")).model_dump(mode="json")
    r = agente.criar(menu.Brief(objetivo="x", pilar=Pilar.atracao, frente="marca", publico="A", etapa="descoberta", formato="reel"))
    s = sessao(agente, ["aprovar", "Gabriel", True, "voltar"])
    menu.fluxo_acoes_peca(s, r.id)
    assert agente.registro.entrada(r.id)["status"] == "revisao"
    assert "bloqueios" in capsys.readouterr().out


def test_menu_principal_navega_e_sai(agente):
    # Peças sem nenhuma peça (aviso, não quebra) → planejar 1 semana → não gerar lote → criar via lote → peças → abrir uma → voltar → sair
    s = sessao(agente, ["pecas", "planejar", 1, "2026-11-09", 4, "", True, False, "lote", "C-20261106-01", False, 1, True,
                        "pecas", "__voltar__", "sair"])
    executar_menu(s)
    assert agente.registro.dados["calendarios"] and len(agente.registro.listar()) == 1
    assert s.p.respostas == []


def test_ctrl_c_no_menu_principal_sai(agente):
    s = sessao(agente, [Voltar])
    executar_menu(s)


def test_lote_pelo_menu_respeita_quantidade(agente):
    cal = agente.planejar(semanas=1)
    s = sessao(agente, [False, 2, True])  # não gerar vendas genéricas · 2 peças · confirma custo
    menu.fluxo_lote(s, cal_id=cal.id)
    assert len(agente.registro.listar()) == 2


def test_em_reais():
    from agente.visual import em_reais
    assert em_reais(0.0035, 5.5) == "R$ 0,02"
    assert em_reais(1234.5, 5.5) == "R$ 6.789,75"
