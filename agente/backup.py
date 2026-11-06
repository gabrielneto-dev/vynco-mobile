"""Backup incremental de saida/ e dados/ para uma pasta sincronizada (OneDrive, Google Drive...).

- Copia só o que é novo ou mudou; nunca apaga nada no destino.
- O .env (com a chave da API) NÃO entra no backup.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agente.config import RAIZ, Config

NOME_PASTA = "AgenteConteudo-backup"
MARCADOR = "ultimo_backup.txt"
IGNORAR_SUFIXOS = {".tmp"}


@dataclass
class ResultadoBackup:
    destino: Path
    copiados: int
    conferidos: int
    quando: datetime


def destino_configurado() -> Path | None:
    v = os.getenv("BACKUP_DIR", "").strip()
    return Path(v) if v else None


def sugerir_destino() -> Path | None:
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        base = os.getenv(var)
        if base and Path(base).is_dir():
            return Path(base) / NOME_PASTA
    for candidato in (Path.home() / "Google Drive", Path.home() / "My Drive", Path("G:/Meu Drive"), Path("G:/My Drive")):
        if candidato.is_dir():
            return candidato / NOME_PASTA
    return None


def definir_variavel_env(chave: str, valor: str, arquivo: Path | None = None) -> None:
    """Grava/atualiza CHAVE=valor no .env, sem mexer nas outras linhas."""
    arquivo = arquivo or (RAIZ / ".env")
    linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
    nova = f"{chave}={valor}"
    for i, l in enumerate(linhas):
        if l.strip().startswith(f"{chave}="):
            linhas[i] = nova
            break
    else:
        linhas.append(nova)
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    os.environ[chave] = valor


def configurar_destino(caminho: Path, arquivo_env: Path | None = None) -> Path:
    caminho = Path(caminho)
    caminho.mkdir(parents=True, exist_ok=True)
    definir_variavel_env("BACKUP_DIR", str(caminho), arquivo_env)
    return caminho


def _espelhar(origem: Path, destino: Path) -> tuple[int, int]:
    copiados = conferidos = 0
    if not origem.exists():
        return 0, 0
    for arq in origem.rglob("*"):
        if not arq.is_file() or arq.suffix in IGNORAR_SUFIXOS:
            continue
        conferidos += 1
        alvo = destino / arq.relative_to(origem)
        st = arq.stat()
        if alvo.exists():
            sd = alvo.stat()
            if sd.st_size == st.st_size and sd.st_mtime >= st.st_mtime - 1:
                continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arq, alvo)
        copiados += 1
    return copiados, conferidos


def fazer_backup(cfg: Config, destino: Path | None = None) -> ResultadoBackup:
    destino = Path(destino or destino_configurado() or "")
    if not str(destino) or str(destino) == ".":
        raise ValueError("Pasta de backup não configurada.")
    destino.mkdir(parents=True, exist_ok=True)
    c1, v1 = _espelhar(cfg.dir_saida, destino / "saida")
    c2, v2 = _espelhar(cfg.dir_dados, destino / "dados")
    agora = datetime.now()
    (destino / MARCADOR).write_text(agora.isoformat(timespec="seconds"), encoding="utf-8")
    return ResultadoBackup(destino, c1 + c2, v1 + v2, agora)


def ultimo_backup(destino: Path | None = None) -> datetime | None:
    destino = destino or destino_configurado()
    if not destino:
        return None
    m = Path(destino) / MARCADOR
    try:
        return datetime.fromisoformat(m.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def tempo_relativo(quando: datetime | None) -> str:
    if not quando:
        return "nunca"
    s = (datetime.now() - quando).total_seconds()
    if s < 90:
        return "agora há pouco"
    if s < 3600:
        return f"há {int(s // 60)} min"
    if s < 86400:
        return f"há {int(s // 3600)} h"
    return f"há {int(s // 86400)} dia(s)"
