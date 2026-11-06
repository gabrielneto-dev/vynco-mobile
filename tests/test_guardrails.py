from agente.guardrails import Nivel, verificar_prompt_imagem, verificar_texto
from agente.schemas import Aparelho, Frente


def regras(texto, **kw):
    return {a.regra: a.nivel for a in verificar_texto(texto, **kw)}


def test_texto_limpo_sem_achados():
    assert regras("Veja o que conferir antes de comprar um iPhone usado.") == {}


def test_promessa_absoluta_bloqueia():
    assert regras("Compra 100% segura e sem riscos!")["promessa_absoluta"] == Nivel.bloqueio


def test_tela_sem_riscos_e_condicao_fisica_nao_promessa():
    # Falso positivo encontrado no teste real do fluxo de venda (dado vindo do estoque).
    assert "promessa_absoluta" not in regras("Tela sem riscos; leve marca de uso na lateral.")
    assert "promessa_absoluta" not in regras("Traseira e câmeras sem nenhum arranhão.")
    assert regras("Compre sem riscos com a gente")["promessa_absoluta"] == Nivel.bloqueio


def test_vinculo_apple_bloqueia():
    assert regras("Somos revenda autorizada Apple")["vinculo_apple"] == Nivel.bloqueio
    assert regras("Loja certificada pela Apple")["vinculo_apple"] == Nivel.bloqueio
    assert regras("Somos parceiro oficial da Apple")["vinculo_apple"] == Nivel.bloqueio
    # Falsos positivos encontrados no teste real (lote) e permitidos pelo BRAND.md:
    assert "vinculo_apple" not in regras("Confira a compatibilidade na página oficial da Apple.")
    assert "vinculo_apple" not in regras("Não somos assistência autorizada Apple.")


def test_urgencia_exige_revisao_mas_nao_perca_dinheiro_e_ok():
    assert regras("Última unidade, corre!")["urgencia_escassez"] == Nivel.revisao_humana
    assert "urgencia_escassez" not in regras("Não perca dinheiro comprando sem conferir a bateria.")


def test_imei_bloqueia():
    assert regras("IMEI: 356789012345678")["imei_exposto"] == Nivel.bloqueio


def test_pedir_senha_bloqueia_mas_negar_e_permitido():
    assert regras("Envie a senha do seu Apple ID para avaliarmos")["coleta_dados_indevida"] == Nivel.bloqueio
    assert "coleta_dados_indevida" not in regras("Envie fotos do aparelho. Nunca pedimos sua senha do Apple ID.")
    # Falso positivo encontrado no teste real com o Sonnet:
    assert "coleta_dados_indevida" not in regras("Em nenhum momento pedimos senha de Apple ID ou código de verificação.")
    assert "coleta_dados_indevida" not in regras("Envie modelo, armazenamento e condição.")


def test_contornar_icloud_bloqueia():
    assert regras("Ensinamos a burlar o bloqueio de ativação")["contornar_bloqueio"] == Nivel.bloqueio
    assert regras("Dá pra pular o bloqueio do iCloud")["contornar_bloqueio"] == Nivel.bloqueio
    # Falso positivo encontrado no primeiro teste real:
    assert "contornar_bloqueio" not in regras("O erro mais caro ao comprar iPhone usado é pular a verificação do iCloud.")


def test_preco_sem_estoque_bloqueia_e_com_preco_aprovado_pede_revisao():
    assert regras("iPhone 14 por R$ 3.299")["preco_sem_aprovacao"] == Nivel.bloqueio
    produto = Aparelho(id="U1", modelo="iPhone 14", preco_aprovado_brl=3299, disponivel=True)
    r = regras("iPhone 14 por R$ 3.299", produto=produto)
    assert "preco_sem_aprovacao" not in r and r["preco"] == Nivel.revisao_humana


def test_bateria_divergente_do_estoque_bloqueia():
    produto = Aparelho(id="U1", modelo="iPhone 14", saude_bateria_pct=88, disponivel=True)
    assert regras("Saúde da bateria: 92%", produto=produto)["bateria_divergente"] == Nivel.bloqueio
    assert "bateria_divergente" not in regras("Saúde da bateria: 88%", produto=produto)


def test_garantia_sem_definicao_pede_revisao():
    assert regras("Com garantia de 90 dias")["garantia"] == Nivel.revisao_humana
    assert regras("Com garantia de 90 dias", negocio={"garantia_oferecida": "90 dias"})["garantia"] == Nivel.aviso


def test_pendente_e_prova_social():
    r = regras("Fale com [PENDENTE: nome da loja]. Mais de 500 clientes satisfeitos.")
    assert r["campo_pendente"] == Nivel.revisao_humana
    assert r["prova_social"] == Nivel.revisao_humana


def test_mistura_de_frentes():
    assert "mistura_frentes" in regras("Disponível! Ou venda seu iPhone pra gente.", frente=Frente.venda)
    assert "mistura_frentes" in regras("Solicite avaliação. Compre o seu também!", frente=Frente.captacao)


def test_prompt_imagem_negativas_nao_disparam():
    assert verificar_prompt_imagem("iPhone on a desk, no visible damage, no cracked screens, no Apple logo") == []
    assert verificar_prompt_imagem("iPhone with a cracked screen")[0].regra == "avaria_simulada"
