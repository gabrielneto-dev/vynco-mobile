import json

import pytest

from agente.armazenamento import ErroRegistro
from agente.llm import _sanitizar_schema, extrair_json
from agente.modos import ErroAgente, agregar, ler_resultados_csv
from agente.prompts import montar_sistema
from agente.config import RAIZ
from agente.schemas import Brief, Formato, Frente, Peca, Pilar, Publico, Etapa, StatusPeca

from conftest import com_estoque, peca_exemplo


def brief(**kw):
    base = dict(objetivo="3 sinais de alerta", pilar=Pilar.atracao, frente=Frente.marca, publico=Publico.A, etapa=Etapa.descoberta, formato=Formato.reel)
    base.update(kw)
    return Brief(**base)


def test_sistema_inclui_contexto_e_pendencias(agente):
    s = montar_sistema(agente.ctx)
    for nome in ("BRAND.md", "QUALITY_RULES.md", "CREATIVE_STANDARDS.md"):
        assert nome in s
    assert "nome_loja" in s  # pendente listado
    assert "Nenhuma unidade disponível" in s
    assert "MODO:" not in s  # instruções de modo ficam fora do sistema (cache compartilhado)


def test_sistema_igual_em_todos_os_modos_e_modo_vai_no_pedido(agente):
    agente.criar(brief())
    agente.revisar("Texto qualquer para revisar.")
    (s1, u1), (s2, u2) = agente.cliente.chamadas[-2:]
    assert s1 == s2
    assert u1.startswith("MODO: CRIAR") and u2.startswith("MODO: REVISAR")


def test_criar_salva_versao_e_markdown(agente):
    r = agente.criar(brief())
    assert r.id.startswith("P-") and r.id.endswith("-ATR-001") and r.versao == 1
    assert r.caminho_md.exists()
    md = r.caminho_md.read_text(encoding="utf-8")
    for secao in ("## 1. Objetivo", "## 4. Ganchos", "## 8. Prompt de imagem", "## 10. Checklist", "## 11. Métrica"):
        assert secao in md
    assert agente.registro.entrada(r.id)["status"] == "revisao"


def test_venda_sem_produto_exige_flag(agente):
    with pytest.raises(ErroAgente, match="--produto"):
        agente.criar(brief(pilar=Pilar.conversao, frente=Frente.venda))
    assert agente.criar(brief(pilar=Pilar.conversao, frente=Frente.venda), generico=True).id


def test_produto_inexistente_ou_indisponivel(agente):
    with pytest.raises(ErroAgente, match="não existe"):
        agente.criar(brief(pilar=Pilar.conversao, frente=Frente.venda, produto_id="X"))
    com_estoque(agente, disponivel=False)
    with pytest.raises(ErroAgente, match="indisponível"):
        agente.criar(brief(pilar=Pilar.conversao, frente=Frente.venda, produto_id="U1"))


def test_unidade_real_remove_prompt_e_bloqueia_imagem(agente):
    com_estoque(agente)
    r = agente.criar(brief(pilar=Pilar.conversao, frente=Frente.venda, produto_id="U1", formato=Formato.imagem))
    assert r.peca.prompt_imagem is None
    with pytest.raises(ErroAgente, match="fotos reais"):
        agente.imagem_da_peca(r.id)


def test_aprovacao_bloqueada_com_bloqueios_e_fluxo_ate_publicado(agente):
    ruim = Peca.model_validate(peca_exemplo(legenda="Compra 100% segura!"))
    agente.cliente.respostas[Peca] = ruim.model_dump(mode="json")
    r = agente.criar(brief())
    with pytest.raises(ErroRegistro, match="bloqueios"):
        agente.registro.atualizar_status(r.id, StatusPeca.aprovado, "Gabriel")

    agente.cliente.respostas.pop(Peca)
    ok = agente.criar(brief())
    with pytest.raises(ErroRegistro, match="responsável"):
        agente.registro.atualizar_status(ok.id, StatusPeca.aprovado, "agente")
    with pytest.raises(ErroRegistro):
        agente.registro.atualizar_status(ok.id, StatusPeca.publicado, "Gabriel")
    agente.registro.atualizar_status(ok.id, StatusPeca.aprovado, "Gabriel")
    agente.registro.registrar_publicacao(ok.id, url="https://instagram.com/p/x", data="2026-11-10", campanha=None, criativo="V1", responsavel="Gabriel")
    assert agente.registro.entrada(ok.id)["status"] == "publicado"


def test_reverificar_grava_nova_versao_sem_llm(agente):
    r = agente.criar(brief())
    chamadas = len(agente.cliente.chamadas)
    r2 = agente.reverificar(r.id)
    assert r2.id == r.id and r2.versao == 2 and len(agente.cliente.chamadas) == chamadas
    assert (agente.registro.dir_peca(r.id) / "v2.md").exists()


def test_imagem_salva_arquivo_e_metadados(agente):
    r = agente.criar(brief())
    caminhos, _ = agente.imagem_da_peca(r.id, quantidade=2)
    assert len(caminhos) == 2 and all(c.exists() and c.suffix == ".png" for c in caminhos)
    assert caminhos[0].with_suffix(".json").exists()
    assert len(agente.registro.entrada(r.id)["imagens"]) == 2


def test_adaptar_cria_nova_peca_com_origem(agente):
    r = agente.criar(brief())
    a = agente.adaptar(r.id, Formato.carrossel)
    assert a.id != r.id and a.brief.formato == Formato.carrossel and a.brief.origem == r.id


def test_planejar_e_lote(agente):
    cal = agente.planejar(semanas=1, publicacoes_semana=4)
    assert cal.caminho.exists() and cal.caminho.with_suffix(".md").exists()
    assert any("Estoque vazio" in a for a in cal.avisos)
    resultados = list(agente.lote(cal.id))
    assert len(resultados) == 4
    assert isinstance(resultados[3][2], str) and resultados[3][2].startswith("pulado")
    # Retomada: itens já gerados não são cobrados de novo (bug real ao interromper um lote).
    chamadas = len(agente.cliente.chamadas)
    retomada = list(agente.lote(cal.id))
    assert all(isinstance(r, str) for _, _, r in retomada[:3]) and retomada[0][2].startswith("já gerado")
    assert len(agente.cliente.chamadas) == chamadas
    assert len(list(agente.lote(cal.id, refazer=True, limite=1))) == 1


def test_csv_e_agregados():
    linhas, colunas = ler_resultados_csv(RAIZ / "exemplos" / "resultados_exemplo.csv")
    assert len(linhas) == 4 and "salvamentos" in colunas
    assert linhas[2]["investimento_brl"] == 150.0
    ag = agregar(linhas)
    assert ag["por_pilar"]["educacao"]["salvamentos"]["soma"] == 260


def test_extrair_json_e_sanitizar():
    assert extrair_json('Aqui está:\n```json\n{"a": 1}\n```') == '{"a": 1}'
    s = _sanitizar_schema(Peca.model_json_schema())
    texto = str(s)
    assert "minItems" not in texto and "'additionalProperties': False" in texto


def test_schema_vai_so_no_response_format_e_raciocinio_baixo(agente, monkeypatch):
    """Economia: o JSON Schema não é repetido no texto do pedido quando o response_format é aceito."""
    from agente.llm import ClienteOpenRouter
    from conftest import peca_exemplo
    import json as _json

    enviados = []
    real = ClienteOpenRouter(agente.cfg)
    def post(payload):
        enviados.append(payload)
        return {"choices": [{"message": {"content": _json.dumps(peca_exemplo())}}], "usage": {}}
    monkeypatch.setattr(real, "post", post)
    real.gerar_estruturado("sistema", "pedido", Peca, modelo="anthropic/claude-sonnet-5.5")
    p = enviados[0]
    assert "response_format" in p and "JSON Schema" not in p["messages"][1]["content"]
    assert p["reasoning"] == {"effort": agente.cfg.esforco_raciocinio}

    # Provedor recusa response_format → repete com schema no texto.
    from agente.llm import ErroLLM
    chamadas = {"n": 0}
    def post_recusa(payload):
        chamadas["n"] += 1
        if "response_format" in payload:
            raise ErroLLM("OpenRouter 400: response_format not supported", status=400)
        enviados.append(payload)
        return {"choices": [{"message": {"content": _json.dumps(peca_exemplo())}}], "usage": {}}
    monkeypatch.setattr(real, "post", post_recusa)
    real.gerar_estruturado("sistema", "pedido", Peca, modelo="outro/modelo")
    assert "JSON Schema" in enviados[-1]["messages"][1]["content"] and chamadas["n"] == 2


def test_numeros_em_formato_brasileiro_e_americano():
    from agente.modos import _numero

    casos = {"4.200": 4200, "1.234.567": 1234567, "1.234,56": 1234.56, "75,50": 75.5, "150,00": 150, "1,234.56": 1234.56,
             "4,200": 4200, "75.50": 75.5, "0.123": 0.123, "R$ 10": 10, "12%": 12, "": None, "abc": None}
    for texto, esperado in casos.items():
        assert _numero(texto) == esperado, texto


def test_haiku_recebe_schema_no_texto_e_resposta_sem_acento_e_refeita(agente, monkeypatch):
    """Haiku 5.5 perde acentos com response_format: vai com schema no texto; outros modelos refazem se vier sem acento."""
    import json as _json
    from agente.llm import ClienteOpenRouter
    from conftest import peca_exemplo

    real = ClienteOpenRouter(agente.cfg)
    enviados = []
    def post(payload):
        enviados.append(payload)
        return {"choices": [{"message": {"content": _json.dumps(peca_exemplo())}}], "usage": {}}
    monkeypatch.setattr(real, "post", post)
    real.gerar_estruturado("s", "p", Peca, modelo="anthropic/claude-haiku-5.5")
    assert "response_format" not in enviados[-1] and "JSON Schema" in enviados[-1]["messages"][1]["content"]

    sem_acento = peca_exemplo(copy_principal="Confira os criterios da avaliacao presencial e o pagamento " * 30)
    respostas = [sem_acento, peca_exemplo(copy_principal="Confira os critérios da avaliação presencial " * 30)]
    def post2(payload):
        enviados.append(payload)
        return {"choices": [{"message": {"content": _json.dumps(respostas.pop(0))}}], "usage": {}}
    monkeypatch.setattr(real, "post", post2)
    p = real.gerar_estruturado("s", "p", Peca, modelo="anthropic/claude-sonnet-5.5")
    assert "critérios" in p.copy_principal
    assert "response_format" in enviados[-2] and "response_format" not in enviados[-1]


def test_prompt_de_imagem_garante_modelo_enquadramento_e_paleta(agente):
    from agente.imagem import montar_prompt, precisao_aparelho

    base = precisao_aparelho("An iPhone 15 lying face down on a gray sweep.")
    assert "exactly two rear camera lenses" in base and "NOT a Pro" in base
    assert "three rear camera lenses" in precisao_aparelho("An iPhone 15 Pro Max on a desk")
    assert precisao_aparelho("A smartphone on a desk") == ""

    final = montar_prompt("An iPhone 13 on a desk.", "9:16", paleta={"fundo": "#F4F4F6", "texto": "#111111", "destaque": "#2F6BFF"})
    assert "Composition" in final and "top 35%" in final and "#F4F4F6" in final and final.endswith("Aspect ratio: 9:16.")
    assert "Composition" not in montar_prompt("Free prompt", "1:1", composicao=False)


def test_metadados_da_imagem_guardam_o_prompt_enviado(agente):
    r = agente.criar(brief())
    caminho = agente.imagem_da_peca(r.id)[0][0]
    meta = json.loads(caminho.with_suffix(".json").read_text(encoding="utf-8"))
    assert "Device accuracy (iPhone 14)" in meta["prompt"] and "Composition" in meta["prompt"]
