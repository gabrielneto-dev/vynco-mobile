"""Padrão visual: tokens, estilos de arte e validador de design (sem API)."""

import json

import pytest
from PIL import Image

from agente import design
from agente.arte import ErroArte, montar_arte
from agente.cadastro import adicionar_aparelho, adicionar_fotos
from agente.contexto import carregar_contexto
from agente.imagem import montar_prompt
from agente.schemas import Formato, Frente, Pilar
from agente.validacao_design import FALHA, validar_pasta

from test_arte import criar

REGRAS_DURAS = {"tamanho", "zona", "contraste", "fonte_minima", "miniatura"}


def _sem_falha_dura(rel):
    return [a for a in rel.falhas if a.regra in REGRAS_DURAS]


def test_tokens_contraste_e_estilo_padrao():
    assert round(design.contraste((255, 255, 255), (0, 0, 0))) == 21
    assert design.contraste((255, 255, 255), (37, 99, 235)) >= design.CONTRASTE_CORPO  # destaque provisório
    assert design.estilo_padrao(Formato.stories, Frente.captacao, None) == "nativo"
    assert design.estilo_padrao(Formato.anuncio, Frente.captacao, None) == "nativo"
    assert design.estilo_padrao(Formato.carrossel, Frente.marca, None) == "editorial"
    assert design.estilo_padrao(Formato.imagem, Frente.venda, "U1") == "oferta"
    assert design.estilo_padrao(Formato.imagem, Frente.venda, None) == "editorial"


@pytest.mark.parametrize("formato,estilo", [
    (Formato.carrossel, "editorial"), (Formato.stories, "nativo"), (Formato.imagem, "editorial"),
    (Formato.anuncio, "nativo"), (Formato.stories, "editorial"), (Formato.carrossel, "nativo"), (Formato.reel, "editorial"),
])
def test_cada_estilo_renderiza_e_respeita_regras_duras(agente, formato, estilo):
    from agente.cadastro import definir_campo

    definir_campo(agente.cfg, "nome_loja", "Loja Teste")
    definir_campo(agente.cfg, "cidade_regiao_atendimento", "Jales e região")
    agente.ctx = carregar_contexto(agente.cfg)
    r = criar(agente, formato)
    arte = montar_arte(agente, r.id, estilo=estilo)
    assert arte.estilo == estilo and arte.validacao is not None
    assert (arte.pasta / "validacao.json").exists() and (arte.pasta / "validacao.md").exists()
    assert _sem_falha_dura(arte.validacao) == [], [a.mensagem for a in arte.validacao.falhas]
    meta = json.loads((arte.pasta / "arte.json").read_text(encoding="utf-8"))
    assert meta["estilo"] == estilo and all(p["elementos"] for p in meta["paginas"])


def test_nativo_tem_etiqueta_de_localizacao_e_stories_sem_paginacao(agente):
    from agente.cadastro import definir_campo

    definir_campo(agente.cfg, "cidade_regiao_atendimento", "Jales e região")
    agente.ctx = carregar_contexto(agente.cfg)
    arte = montar_arte(agente, criar(agente, Formato.stories).id)
    meta = json.loads((arte.pasta / "arte.json").read_text(encoding="utf-8"))
    papeis_capa = {e["papel"] for e in meta["paginas"][0]["elementos"]}
    assert meta["estilo"] == "nativo" and "local" in papeis_capa
    assert not any(e["papel"] == "rodape" for p in meta["paginas"] for e in p["elementos"])


def test_oferta_so_com_dados_confirmados(agente, tmp_path):
    ap = adicionar_aparelho(agente.cfg, {"modelo": "iPhone 14", "armazenamento_gb": 128, "cor": "Azul", "condicao": "ok",
                                         "saude_bateria_pct": 91, "preco_aprovado_brl": 2899.0}, [])
    foto = tmp_path / "f.jpg"
    Image.new("RGB", (900, 1200), (90, 90, 90)).save(foto)
    adicionar_fotos(agente.cfg, ap.id, [foto])
    agente.ctx = carregar_contexto(agente.cfg)
    r = criar(agente, Formato.imagem, pilar=Pilar.conversao, frente="venda", produto=ap.id)
    arte = montar_arte(agente, r.id)
    meta = json.loads((arte.pasta / "arte.json").read_text(encoding="utf-8"))
    textos = {e["papel"]: e["texto"] for e in meta["paginas"][0]["elementos"]}
    assert arte.estilo == "oferta" and textos["titulo"] == "iPhone 14"
    assert textos["preco"] == "R$ 2.899" and "Bateria 91%" in [e["texto"] for e in meta["paginas"][0]["elementos"]]
    assert _sem_falha_dura(arte.validacao) == []


def test_oferta_recusada_sem_unidade_real(agente):
    r = criar(agente, Formato.imagem)
    with pytest.raises(ErroArte, match="unidade real"):
        montar_arte(agente, r.id, estilo="oferta")


def test_prompt_nativo_pede_foto_de_celular_e_estudio_pede_estudio():
    nativo = montar_prompt("An iPhone 13 on a desk.", "9:16", paleta={"fundo": "#F4F4F6", "destaque": "#2563EB"}, estilo="nativo")
    estudio = montar_prompt("An iPhone 13 on a desk.", "9:16", paleta={"fundo": "#F4F4F6", "destaque": "#2563EB"})
    assert "hand holds the phone" in nativo and "smartphone camera" in nativo and "#F4F4F6" not in nativo
    assert "100mm lens" in estudio and "top 35%" in estudio and "#F4F4F6" in estudio
    assert "Device accuracy (iPhone 13)" in nativo and "Device accuracy (iPhone 13)" in estudio


# ---------------------------------------------------------------------- validador com artes sintéticas
def _arte_sintetica(tmp_path, elementos, *, fundo_tipo="liso", foto=None, estilo="editorial", formato="imagem"):
    pasta = tmp_path / "arte"
    pasta.mkdir()
    Image.new("RGB", (1080, 1350), (244, 244, 246)).save(pasta / "01.png")
    meta = {"peca": "P-TESTE", "formato": formato, "frente": "marca", "produto_id": None, "estilo": estilo,
            "proporcao": "4:5", "zona": [80, 80, 80, 80], "fundo": {"tipo": fundo_tipo, "arquivo": str(foto) if foto else None},
            "selo_ativo": True, "arquivos": ["01.png"], "paginas": [{"arquivo": "01.png", "elementos": elementos}]}
    (pasta / "arte.json").write_text(json.dumps(meta), encoding="utf-8")
    return pasta


def _el(papel, caixa, tamanho=60, cor=(31, 35, 40), fundo=(244, 244, 246), texto="Título curto"):
    return {"papel": papel, "caixa": list(caixa), "tamanho": tamanho, "cor": list(cor), "fundo": list(fundo), "texto": texto}


def test_validador_aprova_arte_no_padrao(tmp_path):
    rel = validar_pasta(_arte_sintetica(tmp_path, [_el("titulo", (80, 200, 800, 300)), _el("marca", (80, 90, 300, 130), 30, texto="Loja")]))
    assert rel.aprovado and not rel.avisos


@pytest.mark.parametrize("elemento,regra", [
    (_el("titulo", (40, 200, 800, 300)), "zona"),                                     # fora da margem
    (_el("titulo", (80, 200, 800, 300), cor=(200, 200, 200)), "contraste"),            # cinza claro no claro
    (_el("corpo", (80, 400, 800, 440), tamanho=20), "fonte_minima"),
    (_el("titulo", (80, 200, 800, 300), tamanho=40), "miniatura"),
])
def test_validador_reprova_cada_regra(tmp_path, elemento, regra):
    rel = validar_pasta(_arte_sintetica(tmp_path, [elemento, _el("marca", (80, 90, 300, 130), 30, texto="Loja")]))
    assert regra in {a.regra for a in rel.falhas}, rel.achados


def test_validador_avisa_texto_demais_e_hierarquia(tmp_path):
    longo = _el("titulo", (80, 200, 1000, 300), texto="Um título comprido demais com bem mais de sete palavras")
    apoio = _el("apoio", (80, 320, 1000, 360), tamanho=50)
    rel = validar_pasta(_arte_sintetica(tmp_path, [longo, apoio, _el("marca", (80, 90, 300, 130), 30, texto="Loja")]))
    regras = {a.regra for a in rel.avisos}
    assert {"quantidade_texto", "hierarquia"} <= regras and rel.aprovado


def test_validador_exige_selo_em_fundo_ia_e_pega_texto_sobre_o_aparelho(tmp_path):
    foto = tmp_path / "foto.png"
    img = Image.new("RGB", (1080, 1350), (210, 210, 205))
    img.paste((60, 70, 80), (380, 400, 700, 1100))
    img.save(foto)
    rel = validar_pasta(_arte_sintetica(tmp_path, [_el("titulo", (80, 600, 1000, 760)), _el("marca", (80, 90, 300, 130), 30)],
                                        fundo_tipo="ia", foto=foto))
    falhas = {a.regra for a in rel.falhas}
    assert {"marca", "aparelho"} <= falhas


def test_validar_arte_pela_cli(agente, monkeypatch):
    from typer.testing import CliRunner

    from agente import cli

    r = criar(agente, Formato.carrossel)
    montar_arte(agente, r.id)
    monkeypatch.setattr(cli, "_agente", lambda: agente)
    saida = CliRunner().invoke(cli.app, ["validar-arte", r.id])
    assert "Padrão visual" in saida.output and saida.exit_code in (0, 1)
    assert FALHA in ("falha",)


def test_ultimo_slide_e_fechamento_nao_lista():
    from agente.arte_base import estruturar_slide

    assert estruturar_slide("Salve este checklist\nMande sua dúvida no Direct", final=True) == (
        "paragrafo", ["Salve este checklist\nMande sua dúvida no Direct"])
    assert estruturar_slide("Bateria\nFace ID", final=False)[0] == "lista"
