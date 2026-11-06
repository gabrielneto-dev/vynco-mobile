import pytest

from agente import menu
from agente.metricas import ErroMetricas, codigo_post, importar, salvar
from agente.modos import agregar, ler_resultados_csv
from agente.schemas import Brief, Formato, Pilar, StatusPeca

from test_menu import sessao


def publicar(agente, formato, pilar, data, url=None):
    r = agente.criar(Brief(objetivo="x", pilar=pilar, frente={"captacao": "captacao"}.get(pilar.value, "marca"), publico="A", etapa="descoberta", formato=formato))
    agente.registro.atualizar_status(r.id, StatusPeca.aprovado, "Gabriel")
    agente.registro.registrar_publicacao(r.id, url=url, data=data, campanha=None, criativo=None, responsavel="Gabriel")
    return r.id


@pytest.fixture
def publicadas(agente):
    reel = publicar(agente, Formato.reel, Pilar.atracao, "2026-11-10", "https://www.instagram.com/reel/ABC123xyz/?igsh=x")
    carrossel = publicar(agente, Formato.carrossel, Pilar.educacao, "2026-11-11")
    anuncio = publicar(agente, Formato.anuncio, Pilar.captacao, "2026-11-12")
    return reel, carrossel, anuncio


def test_codigo_post():
    assert codigo_post("https://www.instagram.com/reel/ABC123xyz/?igsh=x") == "ABC123xyz"
    assert codigo_post("https://instagram.com/minhaloja/p/QWE_9/") == "QWE_9"
    assert codigo_post("17890012345") == "17890012345"


def test_exportacao_organica_em_portugues(agente, publicadas, tmp_path):
    reel, carrossel, _ = publicadas
    csv_pt = tmp_path / "insights.csv"
    csv_pt.write_text(
        "Identificação da publicação;Link permanente;Horário de publicação;Tipo de publicação;Descrição;Alcance;Curtidas;Comentários;Compartilhamentos;Salvamentos;Seguimentos\n"
        "111;https://www.instagram.com/reel/ABC123xyz/;10/11/2026 18:30;Reel do IG;3 sinais;4.200;310;22;140;95;12\n"
        "222;https://www.instagram.com/p/OUTRO1/;11/11/2026 12:00;Carrossel do IG;Checklist;2.100;180;14;75;260;5\n"
        "333;https://www.instagram.com/p/SEMPECA/;15/11/2026 09:00;Imagem do IG;Post antigo;900;40;1;2;3;0\n",
        encoding="utf-8",
    )
    imp = importar(agente, csv_pt)
    assert imp.tipo == "organico"
    por_peca = {l["peca_id"]: l for l in imp.ligadas}
    assert por_peca[reel]["ligacao"] == "link do post" and por_peca[reel]["alcance"] == 4200
    assert por_peca[carrossel]["ligacao"] == "data + formato" and por_peca[carrossel]["salvamentos"] == 260
    assert len(imp.nao_ligadas) == 1 and "SEMPECA" in imp.nao_ligadas[0]["referencia"]

    linhas, _ = ler_resultados_csv(salvar(agente, imp))
    ag = agregar(linhas)
    assert ag["por_pilar"]["educacao"]["salvamentos"]["soma"] == 260
    assert ag["por_formato"]["reel"]["compartilhamentos"]["soma"] == 140


def test_exportacao_de_anuncios_em_ingles_consolida_dias(agente, publicadas, tmp_path):
    _, _, anuncio = publicadas
    csv_en = tmp_path / "ads.csv"
    csv_en.write_text(
        "Reporting starts,Ad name,Campaign name,Reach,Impressions,Link clicks,Messaging conversations started,Amount spent (BRL)\n"
        f"2026-11-12,{anuncio} | variação A,Captação,3000,4100,40,14,75.50\n"
        f"2026-11-13,{anuncio} | variação A,Captação,3800,5200,52,17,74.50\n",
        encoding="utf-8",
    )
    imp = importar(agente, csv_en)
    assert imp.tipo == "anuncios" and len(imp.ligadas) == 1
    l = imp.ligadas[0]
    assert l["peca_id"] == anuncio and l["conversas"] == 31 and l["investimento_brl"] == 150.0 and l["ligacao"] == "ID no anuncio"


def test_arquivo_sem_metricas_e_recusado(agente, tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("nome,cidade\na,b\n", encoding="utf-8")
    with pytest.raises(ErroMetricas, match="Nenhuma coluna de métrica"):
        importar(agente, p)


def test_fluxo_metricas_no_menu(agente, publicadas, tmp_path):
    reel, carrossel, _ = publicadas
    p = tmp_path / "insights.csv"
    p.write_text(
        "Permalink,Publish time,Post type,Reach,Saves,Shares\n"
        "https://www.instagram.com/reel/ABC123xyz/,2026-11-10T18:30:00,IG reel,4200,95,140\n",
        encoding="utf-8",
    )
    # arquivo · informar WhatsApp: sim · qualificadas 3 · negócios 1 · não analisar agora · marcar como analisada: sim
    s = sessao(agente, [str(p), True, "3", "1", False, True])
    menu.fluxo_metricas(s)
    assert agente.registro.entrada(reel)["status"] == "analisado"
    assert agente.registro.entrada(carrossel)["status"] == "publicado"
    csvs = list((agente.registro.dir / "metricas").glob("M-*.csv"))
    linhas, _ = ler_resultados_csv(csvs[0])
    assert linhas[0]["conversas_qualificadas"] == 3 and linhas[0]["negocios"] == 1
