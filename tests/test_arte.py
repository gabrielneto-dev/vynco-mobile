import json

import pytest
from PIL import Image

from agente import menu
from agente.arte import ZONAS, ErroArte, montar_arte
from agente.cadastro import adicionar_aparelho
from agente.contexto import carregar_contexto
from agente.schemas import Brief, Formato, Peca, Pilar

from conftest import peca_exemplo
from test_menu import sessao

CENAS = [
    {"ordem": 1, "visual": "capa", "texto_tela": "Checklist do iPhone usado"},
    {"ordem": 2, "visual": "bateria", "texto_tela": "1. Bateria: confira a saúde"},
    {"ordem": 3, "visual": "face id", "texto_tela": "2. Face ID: teste o reconhecimento"},
    {"ordem": 4, "visual": "fim", "texto_tela": "Salve este checklist"},
]


def criar(agente, formato, pilar=Pilar.educacao, frente="marca", produto=None, **peca):
    agente.cliente.respostas[Peca] = Peca.model_validate(peca_exemplo(roteiro=CENAS, cta="Salve este checklist", **peca)).model_dump(mode="json")
    b = Brief(objetivo="x", pilar=pilar, frente=frente, publico="A", etapa="confianca", formato=formato, produto_id=produto)
    return agente.criar(b, generico=True)


def test_carrossel_sem_imagem_gera_slides_em_4x5(agente):
    r = criar(agente, Formato.carrossel)
    arte = montar_arte(agente, r.id)
    # capa + 3 internas; a última já é o CTA ("Salve este checklist"), então não duplica
    assert [a.name for a in arte.arquivos] == ["01.png", "02.png", "03.png", "04.png"]
    assert all(Image.open(a).size == (1080, 1350) for a in arte.arquivos)
    assert arte.fundo == "liso" and not arte.rascunho
    meta = json.loads((arte.pasta / "arte.json").read_text(encoding="utf-8"))
    assert meta["titulo"] == "Gancho 1" and meta["fundo"]["tipo"] == "liso"
    assert agente.registro.entrada(r.id)["artes"][0]["rascunho"] is False


def test_texto_respeita_zona_segura(agente):
    r = criar(agente, Formato.carrossel)
    capa = Image.open(montar_arte(agente, r.id).arquivos[0]).convert("RGB")
    topo, _, _, esq = ZONAS["4:5"]
    fundo = capa.getpixel((5, 5))
    assert all(capa.getpixel((x, y)) == fundo for x in range(0, 1080, 7) for y in range(0, topo - 2, 3))
    assert all(capa.getpixel((x, y)) == fundo for x in range(0, esq - 2, 3) for y in range(0, 1000, 7))


def test_imagem_com_fundo_ia_tem_selo(agente):
    r = criar(agente, Formato.imagem)
    agente.imagem_da_peca(r.id)  # cliente falso devolve uma imagem 1x1
    arte = montar_arte(agente, r.id, gancho=2)
    assert arte.fundo == "ia" and len(arte.arquivos) == 1
    assert Image.open(arte.arquivos[0]).size == (1080, 1350)


def test_stories_e_reel_em_9x16_com_cartelas_transparentes(agente):
    st = montar_arte(agente, criar(agente, Formato.stories).id)
    assert all(Image.open(a).size == (1080, 1920) for a in st.arquivos)
    reel = montar_arte(agente, criar(agente, Formato.reel).id)
    nomes = [a.name for a in reel.arquivos]
    assert nomes[0] == "00-capa.png" and nomes[1:] == ["01-cartela.png", "02-cartela.png", "03-cartela.png", "04-cartela.png"]
    cartela = Image.open(reel.arquivos[1])
    assert cartela.mode == "RGBA" and cartela.getpixel((2, 2))[3] == 0  # fundo transparente


def test_pendente_recusado_e_rascunho_com_tarja(agente):
    r = criar(agente, Formato.imagem, ganchos=["Fale com [PENDENTE: nome da loja]", "b", "c"])
    with pytest.raises(ErroArte, match="PENDENTE: nome da loja"):
        montar_arte(agente, r.id)
    arte = montar_arte(agente, r.id, rascunho=True)
    vermelho = Image.open(arte.arquivos[0]).convert("RGB").getpixel((5, 30))
    assert arte.rascunho and vermelho[0] > 180 and vermelho[1] < 80


def test_venda_exige_foto_real(agente, tmp_path):
    ap = adicionar_aparelho(agente.cfg, {"modelo": "iPhone 14", "armazenamento_gb": 128, "cor": "Azul", "condicao": "ok"}, [])
    agente.ctx = carregar_contexto(agente.cfg)
    r = criar(agente, Formato.imagem, pilar=Pilar.conversao, frente="venda", produto=ap.id)
    with pytest.raises(ErroArte, match="fotos reais"):
        montar_arte(agente, r.id)

    foto = tmp_path / "f.jpg"
    Image.new("RGB", (900, 1200), (90, 90, 90)).save(foto)
    from agente.cadastro import adicionar_fotos

    adicionar_fotos(agente.cfg, ap.id, [foto])
    agente.ctx = carregar_contexto(agente.cfg)
    arte = montar_arte(agente, r.id)
    assert arte.fundo == "foto_real"


def test_marca_com_paleta_e_nome(agente):
    from agente.cadastro import definir_campo

    definir_campo(agente.cfg, "nome_loja", "Loja Teste")
    definir_campo(agente.cfg, "paleta_cores", {"fundo": "#101820", "texto": "#FFFFFF", "destaque": "#FEE715"})
    agente.ctx = carregar_contexto(agente.cfg)
    arte = montar_arte(agente, criar(agente, Formato.carrossel).id)
    assert Image.open(arte.arquivos[1]).convert("RGB").getpixel((5, 5)) == (16, 24, 32)
    assert not any("assinatura" in a or "Paleta provisória" in a for a in arte.avisos)


def test_fluxo_arte_no_menu_com_pendencia_vira_rascunho(agente):
    r = criar(agente, Formato.imagem, ganchos=["Fale com [PENDENTE: nome da loja]", "b", "c"])
    s = sessao(agente, [1, "liso", True, False])  # gancho 1 · fundo liso · aceita rascunho · não abre pasta
    menu.fluxo_arte(s, r.id)
    assert agente.registro.entrada(r.id)["artes"][-1]["rascunho"] is True
    assert s.p.respostas == []


def test_telefone_nao_quebra_e_apoio_redundante_some():
    from agente.arte import _redundante, limpar

    assert "(17)\u00a099782-2073" in limpar("Chame no WhatsApp (17) 99782-2073")
    assert _redundante("Vender seu iPhone? 4 critérios", "Vai vender seu iPhone? Confira 4 critérios antes de chamar.")
    assert not _redundante("1 Envie modelo | 2 Avaliação presencial | 3 Pix", "Vai vender seu iPhone?")


# ---------------------------------------------------------------------- layout (regressões do primeiro uso real)
def test_texto_da_cena_vira_lista_etapas_ou_paragrafo():
    from agente.arte import estruturar, limpar

    assert estruturar(limpar("iPhone 13, 14 ou 15 | bateria acima de 80% | sem bloqueio")) == (
        "lista", ["iPhone 13, 14 ou 15", "Bateria acima de 80%", "Sem bloqueio"])  # 'iPhone' não vira 'IPhone'
    assert estruturar("Conversa > avaliação presencial > Pix") == ("etapas", ["Conversa", "Avaliação presencial", "Pix"])
    assert estruturar(limpar("1. Envie modelo | 2. Avaliação | 3. Pix")) == ("etapas", ["Envie modelo", "Avaliação", "Pix"])
    assert estruturar("1. Bateria: confira a saúde") == ("paragrafo", ["1. Bateria: confira a saúde"])


def test_quebra_equilibrada_sem_palavra_orfa():
    from PIL import ImageDraw

    from agente.arte import _quebrar, fonte

    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f = fonte("bold", 80)
    linhas = _quebrar(d, "iPhone 13, 14 ou 15", f, int(d.textlength("iPhone 13, 14 ou", font=f)) + 5)
    assert len(linhas) == 2 and len(linhas[-1].split()) > 1  # antes: "iPhone 13, 14 ou" / "15"


def test_titulo_da_capa_fica_na_faixa_livre_e_nao_cobre_o_aparelho(agente, tmp_path):
    from agente.arte import Contexto, Paleta, PALETA_PROVISORIA, capa, faixas_livres

    # Foto clara com um "aparelho" escuro no meio, como as imagens geradas.
    foto = tmp_path / "f.png"
    img = Image.new("RGB", (1080, 1920), (205, 205, 200))
    Image.Image.paste(img, (70, 80, 90), (380, 700, 700, 1400))
    img.save(foto)
    faixas = faixas_livres(img.convert("RGBA"), 80, 1000)
    assert any(a <= 300 and b >= 650 for a, b in faixas) and not any(a < 1000 < b for a, b in faixas)

    c = Contexto(Paleta.do_negocio({"paleta_cores": PALETA_PROVISORIA}), {"nome_loja": "Loja"}, agente.cfg,
                 ZONAS["stories"], (1080, 1920), fundo_ia=True, paginacao=False)
    arte = capa(c, "Seu iPhone 13, 14 ou 15 se encaixa nos critérios de compra?", None, None, foto).convert("RGB")
    aparelho = [arte.getpixel((x, y)) for x in range(400, 690, 20) for y in range(720, 1390, 20)]
    assert all(p == (70, 80, 90) for p in aparelho)  # nada desenhado sobre o aparelho
    escuros = sum(1 for x in range(80, 1000, 4) for y in range(260, 690, 4) if sum(arte.getpixel((x, y))) < 200)
    assert escuros > 300  # o título foi escrito acima dele


def test_ultimo_slide_destaca_whatsapp_e_stories_sem_arraste(agente):
    from agente.arte import Contexto, Paleta, PALETA_PROVISORIA, slide_texto

    paleta = Paleta.do_negocio({"paleta_cores": PALETA_PROVISORIA})
    c = Contexto(paleta, {"nome_loja": "Loja", "whatsapp_comercial": "(17) 99782-2073"}, agente.cfg,
                 ZONAS["stories"], (1080, 1920), paginacao=False)
    final = slide_texto(c, 4, 4, "Envie modelo e condição: (17) 99782-2073", final=True).convert("RGB")
    corpo = final.crop((0, 0, 1080, 1900))  # sem o filete da base
    azul = dict((cor, n) for n, cor in corpo.getcolors(maxcolors=1 << 20)).get(paleta.destaque, 0)
    assert azul > 30_000  # botão na cor de destaque com o número
