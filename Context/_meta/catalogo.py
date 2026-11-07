"""Reconstrói Context/_meta/catalog.jsonl a partir dos registros e valida a memória.

Uso:
    python Context/_meta/catalogo.py           # reconstrói o catálogo e valida
    python Context/_meta/catalogo.py --check   # só valida; código de saída 1 se houver erro

Só biblioteca padrão. Os registros Markdown são canônicos; o catálogo é derivado.
Frontmatter aceito: `chave: valor`, listas inline `[a, b]` ou em bloco (`- item`).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "_meta" / "catalog.jsonl"
IGNORAR = {"README.md", "MAP.md", "STATE.md"}
IGNORAR_PASTAS = {"_meta"}
NOMES_FIXOS = {"core"}  # core/overview.md etc. têm nome fixo; o ID não precisa bater com o arquivo
TAXONOMIA = RAIZ / "_meta" / "taxonomy.yaml"
OBRIGATORIOS = ("id", "type", "title", "branch", "tags", "status", "created_at", "updated_at")
CAMPOS_RELACAO = ("related", "depends_on", "source_ids")
CAMPOS_ID_UNICO = ("supersedes", "superseded_by", "resolved_by")
PREFIXOS = {
    "fact": "FCT", "assumption": "ASM", "question": "QUE", "research": "RES", "decision": "DEC",
    "plan": "PLN", "risk": "RSK", "experiment": "EXP", "note": "NTE", "source": "SRC",
    "summary": "SUM", "checkpoint": "CP",
}
# Padrões de valores de segredo (não nomes de variáveis).
SEGREDOS = [
    re.compile(r"sk-(or-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|password|senha|secret)\s*[=:]\s*['\"]?[A-Za-z0-9_\-/+]{12,}"),
]


def _valor(bruto: str):
    v = bruto.strip()
    if v in ("", "null", "~"):
        return None
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return v.strip("'\"")


def ler_frontmatter(texto: str) -> dict | None:
    if not texto.startswith("---\n"):
        return None
    fim = texto.find("\n---", 4)
    if fim == -1:
        return None
    dados: dict = {}
    chave_lista: str | None = None
    for linha in texto[4:fim].splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if linha.lstrip().startswith("- ") and chave_lista:
            dados[chave_lista] = [*dados[chave_lista], linha.lstrip()[2:].strip().strip("'\"")]
            continue
        chave, _, resto = linha.partition(":")
        chave = chave.strip()
        valor = _valor(resto.split(" #", 1)[0])
        if valor is None and resto.strip() == "":
            dados[chave] = []
            chave_lista = chave
        else:
            dados[chave] = valor
            chave_lista = None
    return dados


def coletar() -> tuple[list[dict], list[str]]:
    registros, erros = [], []
    for caminho in sorted(RAIZ.rglob("*.md")):
        rel = caminho.relative_to(RAIZ)
        if rel.parts[0] in IGNORAR_PASTAS or (len(rel.parts) == 1 and rel.name in IGNORAR):
            continue
        texto = caminho.read_text(encoding="utf-8")
        for padrao in SEGREDOS:
            if padrao.search(texto):
                erros.append(f"{rel}: possível segredo persistido ({padrao.pattern[:30]}…)")
        if rel.name == "_index.md":
            continue
        fm = ler_frontmatter(texto)
        if fm is None:
            erros.append(f"{rel}: sem frontmatter YAML")
            continue
        registros.append({**fm, "path": rel.as_posix()})
    return registros, erros


def validar(registros: list[dict]) -> list[str]:
    erros: list[str] = []
    ids: dict[str, str] = {}
    for r in registros:
        faltando = [c for c in OBRIGATORIOS if c not in r or r[c] in (None, "")]
        if faltando:
            erros.append(f"{r['path']}: campos obrigatórios ausentes: {', '.join(faltando)}")
        rid = r.get("id") or ""
        if rid in ids:
            erros.append(f"{r['path']}: ID duplicado {rid} (também em {ids[rid]})")
        ids[rid] = r["path"]
        prefixo = PREFIXOS.get(r.get("type", ""))
        if prefixo is None:
            erros.append(f"{r['path']}: tipo desconhecido {r.get('type')!r}")
        elif not rid.startswith(f"CTX-{prefixo}-"):
            erros.append(f"{r['path']}: ID {rid} não combina com o tipo {r.get('type')}")
        elif r["path"].split("/")[0] not in NOMES_FIXOS and Path(r["path"]).stem != rid.removeprefix("CTX-"):
            erros.append(f"{r['path']}: nome do arquivo difere do ID {rid}")
    for r in registros:
        alvos = [x for c in CAMPOS_RELACAO for x in (r.get(c) or [])]
        alvos += [r[c] for c in CAMPOS_ID_UNICO if r.get(c)]
        for alvo in alvos:
            if alvo not in ids:
                erros.append(f"{r['path']}: referência a ID inexistente {alvo}")
        if r.get("status") == "superseded" and not r.get("superseded_by"):
            erros.append(f"{r['path']}: status superseded sem superseded_by")
    return erros


def ler_taxonomia() -> tuple[set[str], dict[str, str]]:
    """Tags permitidas (canônicas + nomes de branch) e mapa sinônimo -> canônica."""
    permitidas: set[str] = set()
    sinonimos: dict[str, str] = {}
    secao = None
    for linha in TAXONOMIA.read_text(encoding="utf-8").splitlines():
        if linha and not linha.startswith((" ", "#")):
            secao = linha.split(":", 1)[0].strip()
            continue
        if secao in ("canonical_tags", "branches") and linha.startswith("  ") and ":" in linha:
            chave, _, resto = linha.strip().partition(":")
            permitidas.add(chave)
            if secao == "canonical_tags":
                for s in _valor(resto) or []:
                    sinonimos[s] = chave
    return permitidas, sinonimos


def validar_tags(registros: list[dict]) -> list[str]:
    permitidas, sinonimos = ler_taxonomia()
    erros = []
    for r in registros:
        for tag in r.get("tags") or []:
            if tag in sinonimos:
                erros.append(f"{r['path']}: tag {tag!r} é sinônimo; use {sinonimos[tag]!r}")
            elif tag not in permitidas:
                erros.append(f"{r['path']}: tag {tag!r} fora de _meta/taxonomy.yaml (adicione ou use uma canônica)")
    return erros


def linha_catalogo(r: dict) -> str:
    campos = ("id", "type", "title", "branch", "tags", "status", "updated_at", "path")
    return json.dumps({c: r.get(c) for c in campos}, ensure_ascii=False)


def main(argv: list[str]) -> int:
    so_validar = "--check" in argv
    registros, erros = coletar()
    erros += validar(registros)
    erros += validar_tags(registros)
    if not so_validar:
        CATALOGO.write_text("".join(linha_catalogo(r) + "\n" for r in registros), encoding="utf-8")
        print(f"Catálogo reconstruído: {len(registros)} registros → {CATALOGO.relative_to(RAIZ.parent)}")
    for e in erros:
        print(f"ERRO: {e}")
    print("OK: nenhuma inconsistência." if not erros else f"{len(erros)} problema(s).")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
