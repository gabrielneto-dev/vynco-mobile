import os
import time

from agente import menu
from agente.backup import configurar_destino, definir_variavel_env, fazer_backup, tempo_relativo, ultimo_backup
from agente.schemas import Brief, Formato, Pilar

from test_menu import sessao


def test_backup_incremental(agente, tmp_path):
    agente.criar(Brief(objetivo="x", pilar=Pilar.atracao, frente="marca", publico="A", etapa="descoberta", formato=Formato.reel))
    destino = tmp_path / "nuvem"
    r1 = fazer_backup(agente.cfg, destino)
    assert r1.copiados == r1.conferidos > 0
    assert (destino / "dados" / "negocio.json").exists() and (destino / "saida" / "registro.json").exists()
    assert not (destino / ".env").exists()

    r2 = fazer_backup(agente.cfg, destino)
    assert r2.copiados == 0 and r2.conferidos == r1.conferidos

    time.sleep(1.1)
    (agente.cfg.dir_dados / "negocio.json").write_text('{"nome_loja": "Mudou"}', encoding="utf-8")
    assert fazer_backup(agente.cfg, destino).copiados == 1
    assert ultimo_backup(destino) is not None and tempo_relativo(ultimo_backup(destino)) == "agora há pouco"


def test_backup_nunca_apaga_no_destino(agente, tmp_path):
    destino = tmp_path / "nuvem"
    fazer_backup(agente.cfg, destino)
    (agente.cfg.dir_dados / "estoque.exemplo.json").unlink()
    fazer_backup(agente.cfg, destino)
    assert (destino / "dados" / "estoque.exemplo.json").exists()


def test_definir_variavel_env_preserva_outras_linhas(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("OPENROUTER_API_KEY=sk-123\nMODELO_TEXTO=x\n", encoding="utf-8")
    configurar_destino(tmp_path / "bk", arquivo_env=env)
    definir_variavel_env("BACKUP_DIR", str(tmp_path / "bk2"), env)
    linhas = env.read_text(encoding="utf-8").splitlines()
    assert linhas == ["OPENROUTER_API_KEY=sk-123", "MODELO_TEXTO=x", f"BACKUP_DIR={tmp_path / 'bk2'}"]
    assert os.environ["BACKUP_DIR"] == str(tmp_path / "bk2")


def test_menu_faz_backup_ao_sair_quando_configurado(agente, tmp_path, monkeypatch):
    destino = tmp_path / "nuvem"
    monkeypatch.setenv("BACKUP_DIR", str(destino))
    menu.executar_menu(sessao(agente, ["sair"]))
    assert (destino / "dados" / "negocio.json").exists()


def test_menu_sem_backup_configurado_nao_copia(agente, tmp_path):
    menu.executar_menu(sessao(agente, ["sair"]))  # BACKUP_DIR removido pelo conftest
    assert not any(tmp_path.glob("**/ultimo_backup.txt"))
