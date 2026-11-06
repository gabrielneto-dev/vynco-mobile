"""Importa métricas exportadas da Meta (Business Suite / Instagram / Gerenciador de Anúncios).

Reconhece as colunas por sinônimos em PT/EN, liga cada linha a uma peça registrada e gera um CSV
normalizado no formato que o modo "analisar" entende. Nada é estimado: coluna ausente fica vazia.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from agente.modos import _numero

# Coluna canônica → nomes possíveis na exportação (comparados sem acento, minúsculas, só letras/números).
SINONIMOS: dict[str, list[str]] = {
    "peca_id": ["peca_id", "id da peca"],
    "post_id": ["post id", "identificacao da publicacao", "id da publicacao", "id do post", "media id", "id da midia", "identificacao do post"],
    "url": ["permalink", "link permanente", "link da publicacao", "url"],
    "data": ["publish time", "horario de publicacao", "data de publicacao", "hora de publicacao", "date", "data", "dia", "day",
             "inicio dos relatorios", "reporting starts"],
    "tipo": ["post type", "tipo de publicacao", "tipo de post", "tipo"],
    "descricao": ["description", "descricao", "legenda", "caption", "titulo", "title"],
    "anuncio": ["ad name", "nome do anuncio"],
    "campanha": ["campaign name", "nome da campanha"],
    "alcance": ["reach", "alcance", "contas alcancadas", "accounts reached"],
    "impressoes": ["impressions", "impressoes"],
    "visualizacoes": ["views", "visualizacoes", "plays", "reproducoes"],
    "curtidas": ["likes", "curtidas", "reacoes", "reactions"],
    "comentarios": ["comments", "comentarios"],
    "compartilhamentos": ["shares", "compartilhamentos"],
    "salvamentos": ["saves", "salvamentos", "itens salvos"],
    "visitas_perfil": ["profile visits", "visitas ao perfil"],
    "seguidores": ["follows", "seguimentos", "novos seguidores", "seguidores ganhos"],
    "cliques": ["link clicks", "cliques no link", "cliques todos", "clicks all"],
    "conversas": ["messaging conversations started", "conversas por mensagem iniciadas", "conversas iniciadas"],
    "investimento_brl": ["amount spent brl", "valor usado brl", "valor gasto brl", "amount spent", "valor usado", "valor gasto"],
    "conversas_qualificadas": ["conversas_qualificadas", "conversas qualificadas"],
    "negocios": ["negocios", "negocios fechados"],
}
NUMERICAS = [
    "alcance", "impressoes", "visualizacoes", "curtidas", "comentarios", "compartilhamentos", "salvamentos",
    "visitas_perfil", "seguidores", "cliques", "conversas", "conversas_qualificadas", "negocios", "investimento_brl",
]
COLUNAS_SAIDA = ["peca_id", "data", "pilar", "frente", "formato", "origem", "ligacao", "referencia"] + NUMERICAS
TIPO_PARA_FORMATO = {
    "reel": "reel", "reels": "reel", "ig reel": "reel", "video": "reel",
    "carousel": "carrossel", "carrossel": "carrossel", "ig carousel": "carrossel", "album": "carrossel",
    "image": "imagem", "imagem": "imagem", "foto": "imagem", "photo": "imagem", "ig image": "imagem",
    "story": "stories", "stories": "stories", "ig story": "stories",
}
_RE_ID_PECA = re.compile(r"P-\d{8}-[A-Z]{3}-\d{3}")
_RE_CODIGO_IG = re.compile(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


class ErroMetricas(ValueError):
    pass


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9_]+", " ", t).strip()


_MAPA = {_norm(s): canon for canon, nomes in SINONIMOS.items() for s in nomes}


def codigo_post(valor: str | None) -> str | None:
    """Código estável de um post: código do Instagram na URL, ou o próprio ID."""
    if not valor:
        return None
    valor = str(valor).strip()
    m = _RE_CODIGO_IG.search(valor)
    if m:
        return m.group(1)
    return valor.rstrip("/").split("/")[-1] or None


def _data(valor) -> str | None:
    if not valor:
        return None
    v = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(v[: len(datetime.now().strftime(fmt))], fmt).date().isoformat()
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    return m.group(1) if m else None


# ---------------------------------------------------------------------- leitura
def ler_tabela(caminho: Path) -> list[dict]:
    caminho = Path(caminho)
    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # opcional
        except ImportError as e:
            raise ErroMetricas("Para ler .xlsx instale o openpyxl (pip install openpyxl) ou exporte/salve como CSV.") from e
        ws = openpyxl.load_workbook(caminho, read_only=True, data_only=True).active
        linhas = [list(r) for r in ws.iter_rows(values_only=True)]
        cab = [str(c or "").strip() for c in linhas[0]]
        return [{cab[i]: ("" if v is None else str(v)) for i, v in enumerate(l) if i < len(cab)} for l in linhas[1:] if any(v not in (None, "") for v in l)]

    texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
    linhas = texto.splitlines()
    # Algumas exportações têm linhas de título antes do cabeçalho: usa a primeira linha com 3+ colunas reconhecidas.
    inicio = 0
    for i, l in enumerate(linhas[:10]):
        partes = re.split(r"[,;\t]", l)
        if sum(1 for p in partes if _norm(p.strip('"')) in _MAPA) >= 3:
            inicio = i
            break
    try:
        dialeto = csv.Sniffer().sniff(linhas[inicio], delimiters=",;\t")
    except (csv.Error, IndexError):
        dialeto = csv.excel
    return [dict(r) for r in csv.DictReader(linhas[inicio:], dialect=dialeto)]


@dataclass
class Importacao:
    tipo: str  # organico | anuncios
    linhas: list[dict]
    reconhecidas: dict[str, str]
    ignoradas: list[str]
    nao_ligadas: list[dict] = field(default_factory=list)

    @property
    def ligadas(self) -> list[dict]:
        return [l for l in self.linhas if l.get("peca_id")]


def normalizar(bruto: list[dict]) -> tuple[list[dict], dict[str, str], list[str]]:
    if not bruto:
        raise ErroMetricas("Arquivo sem linhas de dados.")
    reconhecidas: dict[str, str] = {}
    ignoradas: list[str] = []
    for col in bruto[0].keys():
        if col is None:
            continue
        canon = _MAPA.get(_norm(col))
        if canon and canon not in reconhecidas.values():
            reconhecidas[col] = canon
        else:
            ignoradas.append(col)
    if not any(c in reconhecidas.values() for c in NUMERICAS):
        raise ErroMetricas("Nenhuma coluna de métrica reconhecida (alcance, curtidas, salvamentos...). Confira se é a exportação certa.")
    linhas = []
    for r in bruto:
        ln: dict = {}
        for col, canon in reconhecidas.items():
            v = r.get(col)
            if canon in NUMERICAS:
                n = _numero(str(v)) if v not in (None, "") else None
                ln[canon] = n
            elif canon == "data":
                ln[canon] = _data(v)
            else:
                ln[canon] = (str(v).strip() if v is not None else "") or None
        if any(ln.get(c) is not None for c in NUMERICAS):
            linhas.append(ln)
    return linhas, reconhecidas, ignoradas


# ---------------------------------------------------------------------- ligação às peças
def ligar(linhas: list[dict], registro) -> None:
    pecas = registro.dados["pecas"]
    por_codigo = {}
    por_data = defaultdict(list)
    for pid, e in pecas.items():
        pub = e.get("publicacao") or {}
        if pub.get("url_ou_id") and (c := codigo_post(pub["url_ou_id"])):
            por_codigo[c] = pid
        if pub.get("data"):
            por_data[pub["data"]].append(pid)

    for ln in linhas:
        if ln.get("peca_id") and ln["peca_id"] in pecas:
            ln["ligacao"] = "planilha"
            continue
        ln["peca_id"] = None
        for chave in ("url", "post_id"):
            c = codigo_post(ln.get(chave))
            if c and c in por_codigo:
                ln["peca_id"], ln["ligacao"] = por_codigo[c], "link do post"
                break
        if ln["peca_id"]:
            continue
        for chave in ("anuncio", "campanha", "descricao"):
            m = _RE_ID_PECA.search(ln.get(chave) or "")
            if m and m.group(0) in pecas:
                ln["peca_id"], ln["ligacao"] = m.group(0), f"ID no {chave}"
                break
        if ln["peca_id"] or not ln.get("data"):
            continue
        candidatos = por_data.get(ln["data"], [])
        formato = TIPO_PARA_FORMATO.get(_norm(ln.get("tipo") or ""))
        if formato:
            candidatos = [p for p in candidatos if pecas[p]["formato"] == formato]
        if len(candidatos) == 1:
            ln["peca_id"], ln["ligacao"] = candidatos[0], "data + formato"


def consolidar(linhas: list[dict], registro, origem: str) -> list[dict]:
    """Uma linha por peça ligada (soma as métricas, ex.: anúncio com uma linha por dia); não ligadas ficam como vieram."""
    por_peca: dict[str, dict] = {}
    saida: list[dict] = []
    for ln in linhas:
        pid = ln.get("peca_id")
        ref = ln.get("anuncio") or ln.get("url") or ln.get("post_id") or (ln.get("descricao") or "")[:60]
        if not pid:
            saida.append({**{c: ln.get(c) for c in COLUNAS_SAIDA}, "origem": origem, "ligacao": "não ligada", "referencia": ref})
            continue
        e = registro.dados["pecas"][pid]
        alvo = por_peca.setdefault(
            pid,
            {"peca_id": pid, "data": (e.get("publicacao") or {}).get("data") or ln.get("data"), "pilar": e["pilar"], "frente": e["frente"],
             "formato": e["formato"], "origem": origem, "ligacao": ln.get("ligacao"), "referencia": ref, **{c: None for c in NUMERICAS}},
        )
        for c in NUMERICAS:
            if ln.get(c) is not None:
                alvo[c] = (alvo[c] or 0) + ln[c]
    return list(por_peca.values()) + saida


def importar(ag, caminho: Path) -> Importacao:
    bruto = ler_tabela(Path(caminho))
    linhas, reconhecidas, ignoradas = normalizar(bruto)
    origem = "anuncios" if {"anuncio", "investimento_brl"} & set(reconhecidas.values()) else "organico"
    ligar(linhas, ag.registro)
    final = consolidar(linhas, ag.registro, origem)
    return Importacao(origem, final, reconhecidas, ignoradas, [l for l in final if not l.get("peca_id")])


def salvar(ag, imp: Importacao) -> Path:
    pasta = ag.registro.dir / "metricas"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"M-{datetime.now():%Y%m%d-%H%M%S}.csv"
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_SAIDA)
        w.writeheader()
        for l in imp.linhas:
            w.writerow({c: ("" if l.get(c) is None else (f"{l[c]:g}" if isinstance(l[c], float) else l[c])) for c in COLUNAS_SAIDA})
    return destino
