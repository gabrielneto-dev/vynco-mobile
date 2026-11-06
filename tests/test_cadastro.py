import json

import pytest
from PIL import Image

from agente import menu
from agente.cadastro import (
    ErroCadastro,
    adicionar_aparelho,
    definir_campo,
    importar_logo,
    ler_estoque,
    ler_negocio,
    marcar_vendido,
    novo_id_aparelho,
    resumo_negocio,
)
from agente.contexto import carregar_contexto
from agente.schemas import Brief, Formato, Pilar

from test_menu import Roteiro, sessao


@pytest.fixture
def foto(tmp_path):
    p = tmp_path / "foto_origem.jpg"
    Image.new("RGB", (800, 1000), (40, 40, 40)).save(p)
    return p


def test_definir_campos_preserva_instrucoes_e_vazio_vira_pendente(agente):
    cfg = agente.cfg
    definir_campo(cfg, "nome_loja", "  Loja Teste  ")
    definir_campo(cfg, "modelos_captacao_foco", "iPhone 13; iPhone 14 ;")
    definir_campo(cfg, "garantia_oferecida", "")
    d = ler_negocio(cfg)
    assert d["_instrucoes"] and d["nome_loja"] == "Loja Teste"
    assert d["modelos_captacao_foco"] == ["iPhone 13", "iPhone 14"]
    assert d["garantia_oferecida"] is None
    preenchidos, total, essenciais = resumo_negocio(cfg)
    assert "Nome da loja" not in essenciais and "WhatsApp comercial" in essenciais and preenchidos < total


def test_paleta_valida_e_invalida(agente):
    assert definir_campo(agente.cfg, "paleta_cores", {"fundo": "#ffffff", "texto": "#111111", "destaque": "#2f6bff"})["fundo"] == "#FFFFFF"
    with pytest.raises(ErroCadastro):
        definir_campo(agente.cfg, "paleta_cores", {"fundo": "branco", "texto": "#111111", "destaque": "#2f6bff"})


def test_importar_logo(agente, tmp_path):
    origem = tmp_path / "meu_logo.png"
    Image.new("RGBA", (200, 80), (255, 0, 0, 255)).save(origem)
    rel = importar_logo(agente.cfg, origem)
    assert rel == "marca/logo.png" and (agente.cfg.dir_dados / rel).exists()
    assert ler_negocio(agente.cfg)["logotipo"] == rel


def test_id_de_aparelho():
    assert novo_id_aparelho("iPhone 14 Pro", 128, "Azul-sierra", []) == "IP14PRO-128-AZULSIERRA-01"
    assert novo_id_aparelho("iPhone 13", 256, "Verde", ["IP13-256-VERDE-01"]) == "IP13-256-VERDE-02"


def test_adicionar_aparelho_copia_fotos_e_entra_no_contexto(agente, foto):
    ap = adicionar_aparelho(agente.cfg, {"modelo": "iPhone 14", "armazenamento_gb": 128, "cor": "Azul", "condicao": "Sem riscos", "saude_bateria_pct": 88}, [foto], verificado_por="Gabriel")
    assert ap.id == "IP14-128-AZUL-01" and ap.fotos == ["fotos/IP14-128-AZUL-01/01.jpg"]
    assert (agente.cfg.dir_dados / ap.fotos[0]).exists()
    ctx = carregar_contexto(agente.cfg)
    assert [a.id for a in ctx.estoque_disponivel] == [ap.id]


def test_vendido_sai_das_ofertas_e_lista_pecas(agente, foto):
    ap = adicionar_aparelho(agente.cfg, {"modelo": "iPhone 14", "armazenamento_gb": 128, "cor": "Azul", "condicao": "ok"}, [foto])
    agente.ctx = carregar_contexto(agente.cfg)
    r = agente.criar(Brief(objetivo="oferta", pilar=Pilar.conversao, frente="venda", publico="A", etapa="intencao", formato=Formato.imagem, produto_id=ap.id))
    marcar_vendido(agente.cfg, ap.id)
    assert ler_estoque(agente.cfg)[0]["disponivel"] is False
    assert [p["id"] for p in agente.pecas_do_produto(ap.id)] == [r.id]
    # Reverificar uma peça de unidade vendida informa o problema sem derrubar as demais.
    res = dict(agente.reverificar_todas())
    assert "não está mais disponível" in res[r.id]


def test_fluxo_negocio_pelo_menu(agente):
    s = sessao(agente, ["nome_loja", "Loja Teste", "whatsapp_comercial", "(19) 99999-9999", "__fim__"])
    menu.fluxo_negocio(s)
    d = ler_negocio(agente.cfg)
    assert d["nome_loja"] == "Loja Teste" and d["whatsapp_comercial"] == "(19) 99999-9999"
    assert "nome_loja" in s.ag.ctx.negocio_confirmado  # contexto recarregado para as próximas peças


def test_fluxo_estoque_cadastra_e_vende(agente, foto):
    s = sessao(
        agente,
        [
            "novo", "iPhone 13", 128, "Meia-noite", "Tela perfeita; marcas leves na lateral", "87", "Nenhuma", "Pessoa física com NF", "", "3.299,90",
            True, str(foto), False, "Gabriel", True,       # foto, responsável, confirma
            "vendido", "IP13-128-MEIANOITE-01", True,      # sem peças: não pergunta sobre arquivar
            "__voltar__",
        ],
    )
    menu.fluxo_estoque(s)
    item = ler_estoque(agente.cfg)[0]
    assert item["preco_aprovado_brl"] == 3299.90 and item["saude_bateria_pct"] == 87 and item["garantia"] is None
    assert item["disponivel"] is False and item["verificado_por"] == "Gabriel"
    assert s.p.respostas == []
