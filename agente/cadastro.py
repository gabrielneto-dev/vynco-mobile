"""Cadastro dos dados do negócio (dados/negocio.json) e do estoque (dados/estoque.json).

Só grava o que o responsável informa. Campo vazio = pendente (null), nunca um valor suposto.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agente.config import RAIZ, Config
from agente.schemas import Aparelho


@dataclass(frozen=True)
class Campo:
    chave: str
    rotulo: str
    ajuda: str
    tipo: str = "texto"  # texto | lista | paleta | logo
    essencial: bool = False


CAMPOS_NEGOCIO: list[Campo] = [
    Campo("nome_loja", "Nome da loja", "Como a loja assina as peças.", essencial=True),
    Campo("cidade_regiao_atendimento", "Cidade / região de atendimento", "Ex.: Campinas e região (até 30 km).", essencial=True),
    Campo("whatsapp_comercial", "WhatsApp comercial", "Número que aparece nos CTAs. Ex.: (19) 99999-9999.", essencial=True),
    Campo("instagram", "Instagram", "Ex.: @minhaloja"),
    Campo("facebook", "Facebook", "Nome ou link da página."),
    Campo("retirada_entrega_logistica", "Retirada / entrega", "Ex.: retirada na loja; entrega na cidade combinada pelo WhatsApp."),
    Campo("garantia_oferecida", "Garantia oferecida", "Exatamente o que a loja oferece. Ex.: 90 dias para defeitos de funcionamento."),
    Campo("parcelamento", "Parcelamento", "Ex.: até 10x no cartão (com juros da maquininha)."),
    Campo("formas_pagamento_venda", "Formas de pagamento (venda)", "Ex.: Pix, cartão, dinheiro."),
    Campo("troca_aceita", "Aceita troca?", "Ex.: aceitamos iPhone usado como parte do pagamento, mediante avaliação."),
    Campo("politica_devolucao", "Política de devolução", "Ex.: 7 dias para compras online (CDC)."),
    Campo("prazo_resposta_atendimento", "Prazo de resposta", "Só o que a loja consegue cumprir. Ex.: em até 2 horas no horário comercial."),
    Campo("criterios_compra_usados", "Critérios para comprar usados", "Ex.: bateria acima de 80%, sem bloqueios, sem peças trocadas.", essencial=True),
    Campo("modelos_captacao_foco", "Modelos que a loja compra", "Separe por ponto e vírgula. Ex.: iPhone 13; iPhone 14; iPhone 15.", tipo="lista"),
    Campo("forma_pagamento_compra_usados", "Como paga quem vende o usado", "Ex.: Pix na hora, após a avaliação presencial."),
    Campo("paleta_cores", "Paleta de cores", "3 cores em hexadecimal: fundo, texto e destaque.", tipo="paleta"),
    Campo("logotipo", "Logotipo", "Arquivo PNG (de preferência com fundo transparente).", tipo="logo"),
    Campo("diferenciais_comprovados", "Diferenciais comprovados", "Só o que dá para provar. Separe por ponto e vírgula.", tipo="lista"),
    Campo("observacoes", "Observações", "Qualquer outra informação útil para o agente."),
]

PALETA_PROVISORIA = {"fundo": "#F4F4F6", "texto": "#1F2328", "destaque": "#2563EB"}  # azul com contraste AA (5,2:1) para texto branco
MODELOS_IPHONE = [
    "iPhone 11", "iPhone 11 Pro", "iPhone 11 Pro Max", "iPhone SE (2ª geração)", "iPhone SE (3ª geração)",
    "iPhone 12", "iPhone 12 mini", "iPhone 12 Pro", "iPhone 12 Pro Max",
    "iPhone 13", "iPhone 13 mini", "iPhone 13 Pro", "iPhone 13 Pro Max",
    "iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max",
    "iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max",
    "iPhone 16", "iPhone 16 Plus", "iPhone 16 Pro", "iPhone 16 Pro Max", "iPhone 16e",
    "iPhone 17", "iPhone 17 Pro", "iPhone 17 Pro Max", "iPhone Air",
]
ARMAZENAMENTOS = [64, 128, 256, 512, 1024]
_RE_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class ErroCadastro(ValueError):
    pass


# ---------------------------------------------------------------------- utilidades
def _gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(caminho)


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "", sem_acento.upper())


def validar_hex(valor: str) -> bool:
    return bool(_RE_HEX.match(valor.strip()))


def resolver_caminho(cfg: Config, p: str | Path) -> Path:
    """Caminhos gravados podem ser relativos à pasta de dados ou à raiz do projeto."""
    p = Path(p)
    if p.is_absolute():
        return p
    for base in (cfg.dir_dados, RAIZ, cfg.dir_dados.parent):
        if (base / p).exists():
            return base / p
    return cfg.dir_dados / p


# ---------------------------------------------------------------------- negócio
def ler_negocio(cfg: Config) -> dict:
    p = cfg.dir_dados / "negocio.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def salvar_negocio(cfg: Config, dados: dict) -> None:
    _gravar_json(cfg.dir_dados / "negocio.json", dados)


def converter_valor(campo: Campo, entrada) -> object:
    """Texto digitado → valor gravado. Vazio vira None (pendente)."""
    if campo.tipo == "lista":
        if isinstance(entrada, list):
            itens = entrada
        else:
            itens = [x.strip() for x in re.split(r"[;\n]", entrada or "")]
        itens = [x for x in itens if x]
        return itens or ([] if campo.chave == "diferenciais_comprovados" else None)
    if campo.tipo == "paleta":
        if not entrada:
            return None
        if not all(validar_hex(entrada.get(k, "")) for k in ("fundo", "texto", "destaque")):
            raise ErroCadastro("Paleta precisa de 3 cores no formato #RRGGBB.")
        return {k: entrada[k].upper() for k in ("fundo", "texto", "destaque")}
    texto = (entrada or "").strip()
    return texto or None


def definir_campo(cfg: Config, chave: str, entrada) -> object:
    campo = next(c for c in CAMPOS_NEGOCIO if c.chave == chave)
    dados = ler_negocio(cfg)
    dados[chave] = converter_valor(campo, entrada)
    salvar_negocio(cfg, dados)
    return dados[chave]


def importar_logo(cfg: Config, origem: Path) -> str:
    origem = Path(origem)
    if not origem.is_file():
        raise ErroCadastro(f"Arquivo não encontrado: {origem}")
    if origem.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ErroCadastro("Use um arquivo PNG, JPG ou WEBP.")
    destino = cfg.dir_dados / "marca" / f"logo{origem.suffix.lower()}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, destino)
    rel = f"marca/{destino.name}"
    dados = ler_negocio(cfg)
    dados["logotipo"] = rel
    salvar_negocio(cfg, dados)
    return rel


def resumo_negocio(cfg: Config) -> tuple[int, int, list[str]]:
    """(preenchidos, total, essenciais pendentes)."""
    dados = ler_negocio(cfg)
    preenchidos = sum(1 for c in CAMPOS_NEGOCIO if dados.get(c.chave) not in (None, "", []))
    essenciais = [c.rotulo for c in CAMPOS_NEGOCIO if c.essencial and dados.get(c.chave) in (None, "", [])]
    return preenchidos, len(CAMPOS_NEGOCIO), essenciais


# ---------------------------------------------------------------------- estoque
def ler_estoque(cfg: Config) -> list[dict]:
    p = cfg.dir_dados / "estoque.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def salvar_estoque(cfg: Config, itens: list[dict]) -> None:
    for item in itens:
        Aparelho.model_validate(item)  # nunca grava algo que o resto do sistema não consiga ler
    _gravar_json(cfg.dir_dados / "estoque.json", itens)


def novo_id_aparelho(modelo: str, armazenamento_gb: int | None, cor: str | None, existentes: list[str]) -> str:
    """Ex.: iPhone 14 Pro, 128 GB, Azul → IP14PRO-128-AZUL-01."""
    base = _slug(modelo).replace("IPHONE", "IP") or "IPHONE"
    partes = [base, str(armazenamento_gb or "X"), _slug(cor or "")[:10] or "SEMCOR"]
    prefixo = "-".join(partes)
    n = 1
    while f"{prefixo}-{n:02d}" in existentes:
        n += 1
    return f"{prefixo}-{n:02d}"


def copiar_fotos(cfg: Config, aparelho_id: str, fotos: list[Path], ja_existentes: int = 0) -> list[str]:
    pasta = cfg.dir_dados / "fotos" / aparelho_id
    pasta.mkdir(parents=True, exist_ok=True)
    gravadas = []
    for i, origem in enumerate(fotos, ja_existentes + 1):
        origem = Path(origem)
        if not origem.is_file():
            raise ErroCadastro(f"Foto não encontrada: {origem}")
        destino = pasta / f"{i:02d}{origem.suffix.lower()}"
        shutil.copy2(origem, destino)
        gravadas.append(f"fotos/{aparelho_id}/{destino.name}")
    return gravadas


def adicionar_aparelho(cfg: Config, dados: dict, fotos: list[Path] | None = None, verificado_por: str | None = None) -> Aparelho:
    itens = ler_estoque(cfg)
    aparelho_id = novo_id_aparelho(dados["modelo"], dados.get("armazenamento_gb"), dados.get("cor"), [i["id"] for i in itens])
    registro = {
        "id": aparelho_id,
        **{k: v for k, v in dados.items() if k != "id"},
        "disponivel": True,
        "fotos": copiar_fotos(cfg, aparelho_id, fotos or []),
        "verificado_por": verificado_por,
        "verificado_em": date.today().isoformat(),
    }
    aparelho = Aparelho.model_validate(registro)
    itens.append(registro)
    salvar_estoque(cfg, itens)
    return aparelho


def atualizar_aparelho(cfg: Config, aparelho_id: str, **campos) -> dict:
    itens = ler_estoque(cfg)
    item = next((i for i in itens if i["id"] == aparelho_id), None)
    if item is None:
        raise ErroCadastro(f"Aparelho {aparelho_id} não encontrado.")
    item.update(campos)
    salvar_estoque(cfg, itens)
    return item


def adicionar_fotos(cfg: Config, aparelho_id: str, fotos: list[Path]) -> list[str]:
    item = next((i for i in ler_estoque(cfg) if i["id"] == aparelho_id), None)
    if item is None:
        raise ErroCadastro(f"Aparelho {aparelho_id} não encontrado.")
    novas = copiar_fotos(cfg, aparelho_id, fotos, ja_existentes=len(item.get("fotos", [])))
    atualizar_aparelho(cfg, aparelho_id, fotos=item.get("fotos", []) + novas)
    return novas


def marcar_vendido(cfg: Config, aparelho_id: str) -> dict:
    return atualizar_aparelho(cfg, aparelho_id, disponivel=False, vendido_em=date.today().isoformat())
