"""Verificações determinísticas (sem LLM) das regras de QUALITY_RULES.md.

O LLM é instruído a seguir as regras, mas estas checagens rodam sempre, sobre o texto final,
para que nenhuma violação dependa de o modelo "lembrar". Níveis:
  - bloqueio: a peça não pode ser aprovada até corrigir.
  - revisao_humana: precisa de validação explícita do responsável.
  - aviso: ponto de atenção.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum

from agente.schemas import Aparelho, FRENTE_POR_PILAR, Brief, Frente, Peca, StatusFonte


class Nivel(str, Enum):
    bloqueio = "bloqueio"
    revisao_humana = "revisao_humana"
    aviso = "aviso"


@dataclass
class Achado:
    nivel: Nivel
    regra: str
    mensagem: str
    trecho: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["nivel"] = self.nivel.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Achado":
        return cls(nivel=Nivel(d["nivel"]), regra=d["regra"], mensagem=d["mensagem"], trecho=d.get("trecho", ""))


# (regex, nível, regra, mensagem) — aplicadas sobre o texto em minúsculas.
_REGRAS_FIXAS: list[tuple[str, Nivel, str, str]] = [
    (
        r"menor pre[çc]o|mais barat[oa]s? d[oa]s? (brasil|cidade|regi[aã]o|mercado)|melhor pre[çc]o d[aoe]|pre[çc]o imbat[ií]vel",
        Nivel.revisao_humana,
        "claim_preco_comparativo",
        "Claim comparativo de preço exige prova documentada.",
    ),
    (
        r"100\s*%\s*(segur|garantid|sem risco|confi[aá]v|original|aprovad)|sem (nenhum )?risco|risco zero|garantia total|zero dor de cabe[çc]a",
        Nivel.bloqueio,
        "promessa_absoluta",
        "Promessa absoluta é proibida.",
    ),
    (
        r"[uú]ltimas? unidades?|s[oó] hoje|corra\b|corre que|acaba (hoje|amanh[aã])|estoque limitado"
        r"|n[aã]o perca (essa|esta|a) (oportunidade|chance|oferta)|[uú]ltima chance",
        Nivel.revisao_humana,
        "urgencia_escassez",
        "Urgência/escassez só com confirmação real e aprovada.",
    ),
    (
        r"\b\d{15}\b|imei\s*[:#]?\s*\d{6,}",
        Nivel.bloqueio,
        "imei_exposto",
        "Não expor IMEI completo em publicações.",
    ),
    (
        r"depoimento|avalia[çc][aã]o (de|do|dos) clientes?|clientes? (satisfeit|aprova|diz|disse|elogi|recomend)|\+?\d+\s*(mil\s+)?clientes|nota\s+\d|\d(\.\d)?\s*estrelas",
        Nivel.revisao_humana,
        "prova_social",
        "Prova social só se for verdadeira, documentada e autorizada.",
    ),
    (
        r"\[pendente[^\]]*\]",
        Nivel.revisao_humana,
        "campo_pendente",
        "Há campos [PENDENTE] que precisam ser preenchidos antes de publicar.",
    ),
]

# Regras avaliadas frase a frase, ignorando frases negativas ("nunca pedimos sua senha" é desejável).
_REGRAS_POR_FRASE: list[tuple[str, Nivel, str, str]] = [
    (
        # Verbos inequívocos: qualquer menção próxima. Verbos ambíguos ("pular a verificação do iCloud" é um
        # bom conselho): só quando o objeto direto é o próprio bloqueio/conta.
        r"\b(burlar|contornar|bypass)\w*\s.{0,30}(icloud|bloqueio|activation lock|conta apple|apple id)"
        r"|\b(pul|quebr|fur|tir)ar\s+(o\s+|a\s+)?(bloqueio|trava|icloud|activation lock|conta (apple|do icloud))",
        Nivel.bloqueio,
        "contornar_bloqueio",
        "Instruções para contornar bloqueio de ativação são proibidas.",
    ),
    (
        r"(envi[ae]|mand[ae]|inform[ae]|pass[ae]|digit[ae]|compartilh[ae]|pedimos|precisamos)\w*\s.{0,40}"
        r"(senha|c[oó]digo de (verifica|autentica|seguran)|token|dados banc[aá]rios|\bcpf\b|\brg\b)",
        Nivel.bloqueio,
        "coleta_dados_indevida",
        "Não solicitar senha, códigos de autenticação ou dados pessoais desnecessários.",
    ),
    (
        r"\b(desbloque|remov|tir)\w*\s.{0,25}(icloud|bloqueio de ativa[çc][aã]o|conta apple|apple id)",
        Nivel.revisao_humana,
        "mencao_desbloqueio",
        "Confirme que o texto orienta o PRÓPRIO dono a sair da conta, sem ensinar desbloqueio.",
    ),
    (
        # Só alegações sobre a própria loja. "Página oficial da Apple" (referência) e
        # "Não somos assistência autorizada Apple" (frase negativa) são permitidas.
        r"(autorizad[ao]|certificad[ao]|credenciad[ao]|homologad[ao])s?\s+(pela\s+|da\s+)?apple"
        r"|\b(somos|loja|revenda|revendedor[a]?|assist[eê]ncia|parceir[oa]|distribuidor[a]?)\s+(\w+\s+){0,2}"
        r"(oficial|autorizad\w*|certificad\w*|credenciad\w*)\s+(pela\s+|da\s+)?apple"
        r"|apple\s+(authorized|premium reseller|premium partner)|revend(a|edor)\w* oficial",
        Nivel.bloqueio,
        "vinculo_apple",
        "Vínculo/certificação oficial da Apple não pode ser alegado sem documentação.",
    ),
]
# "Tela sem riscos" = sem arranhões (condição física), não promessa de "sem risco". Removido antes das regras fixas.
_RE_RISCO_FISICO = re.compile(
    r"\b(tela|telas|vidro|traseira|tampa|lentes?|laterais|lateral|carca[çc]a|c[aâ]meras?|corpo|bordas?|moldura|display)"
    r"\s+(\w+\s+){0,3}?sem (nenhum |qualquer )?(riscos?|arranh\w*)"
)
_RE_NEGACAO = re.compile(r"\b(nunca|jamais|n[aã]o|nem|sem|nenhum[a]?|momento algum|de forma alguma|de jeito nenhum)\b")
_RE_FRASES = re.compile(r"[^.!?\n]+")

_RE_PRECO = re.compile(r"r\$\s*\d[\d.,]*")
_RE_BATERIA = re.compile(r"(bateria|sa[uú]de)\D{0,25}(\d{2,3})\s*%")
_RE_GARANTIA = re.compile(r"garantia")
_RE_PARCELA = re.compile(r"parcel|sem juros|\b\d{1,2}\s?x\s?(de|sem)\b")
_RE_PRAZO = re.compile(r"(respondemos|resposta|pagamento|pagamos|pix)\s.{0,15}(na hora|imediat|no mesmo dia|em at[eé]|em \d+\s*(min|h))")
_RE_CTA_CAPTACAO = re.compile(r"vend[ae] (o )?seu iphone|compramos (o )?seu|compramos iphones?|avaliamos (o )?seu|solicit\w* (uma )?avalia[çc][aã]o")
_RE_CTA_VENDA = re.compile(r"\bcompre\b|garanta o seu|consultar disponibilidade|reserve (o |j[aá] )?seu|leve o seu")
_RE_AVARIA_PROMPT = re.compile(r"\b(crack|scratch|damage|broken|dent|trinc|arranh|avaria|quebrad|riscad|amassad)")
_RE_LOGO_PROMPT = re.compile(r"apple logo|logo da apple|logotipo da apple|(?<!no )apple branding")


def _trecho(texto: str, m: re.Match, margem: int = 30) -> str:
    ini, fim = max(0, m.start() - margem), min(len(texto), m.end() + margem)
    return texto[ini:fim].replace("\n", " ").strip()


def verificar_texto(
    texto: str,
    *,
    frente: Frente | None = None,
    negocio: dict | None = None,
    produto: Aparelho | None = None,
) -> list[Achado]:
    negocio = negocio or {}
    t = texto.lower()
    achados: list[Achado] = []

    t_regras = _RE_RISCO_FISICO.sub(" ", t)
    for padrao, nivel, regra, msg in _REGRAS_FIXAS:
        m = re.search(padrao, t_regras)
        if m:
            achados.append(Achado(nivel, regra, msg, _trecho(t_regras, m)))

    for frase in _RE_FRASES.findall(t):
        negativa = bool(_RE_NEGACAO.search(frase))
        for padrao, nivel, regra, msg in _REGRAS_POR_FRASE:
            if negativa and nivel == Nivel.bloqueio:
                continue
            if m := re.search(padrao, frase):
                achados.append(Achado(nivel, regra, msg, _trecho(frase, m)))

    # Preço: só com unidade de estoque com preço aprovado; e sempre com aprovação humana.
    m = _RE_PRECO.search(t)
    if m:
        if not produto or produto.preco_aprovado_brl is None:
            achados.append(Achado(Nivel.bloqueio, "preco_sem_aprovacao", "Preço citado sem preço aprovado no estoque.", _trecho(t, m)))
        else:
            achados.append(Achado(Nivel.revisao_humana, "preco", "Preço exige aprovação humana antes de publicar.", _trecho(t, m)))

    # Saúde de bateria: precisa bater com o estoque.
    for m in _RE_BATERIA.finditer(t):
        valor = int(m.group(2))
        if not produto or produto.saude_bateria_pct is None:
            achados.append(Achado(Nivel.revisao_humana, "bateria_sem_fonte", "Percentual de bateria sem unidade verificada; confirme se é exemplo genérico.", _trecho(t, m)))
        elif valor != produto.saude_bateria_pct:
            achados.append(Achado(Nivel.bloqueio, "bateria_divergente", f"Bateria citada ({valor}%) difere do estoque ({produto.saude_bateria_pct}%).", _trecho(t, m)))

    m = _RE_GARANTIA.search(t)
    if m:
        tem_garantia = bool(negocio.get("garantia_oferecida")) or bool(produto and produto.garantia)
        nivel = Nivel.aviso if tem_garantia else Nivel.revisao_humana
        msg = "Confirme que a garantia citada é exatamente a oferecida." if tem_garantia else "Garantia citada, mas não definida pelo negócio."
        achados.append(Achado(nivel, "garantia", msg, _trecho(t, m)))

    m = _RE_PARCELA.search(t)
    if m and not negocio.get("parcelamento"):
        achados.append(Achado(Nivel.revisao_humana, "parcelamento", "Parcelamento citado, mas não definido pelo negócio.", _trecho(t, m)))

    m = _RE_PRAZO.search(t)
    if m:
        chave = "forma_pagamento_compra_usados" if "pag" in m.group(1) or "pix" in m.group(1) else "prazo_resposta_atendimento"
        if not negocio.get(chave):
            achados.append(Achado(Nivel.revisao_humana, "prazo_pagamento", f"Prazo/forma citada sem definição em negocio.json ({chave}).", _trecho(t, m)))

    # Mistura de frentes.
    if frente == Frente.venda and (m := _RE_CTA_CAPTACAO.search(t)):
        achados.append(Achado(Nivel.aviso, "mistura_frentes", "Peça de venda com linguagem de captação.", _trecho(t, m)))
    if frente == Frente.captacao and (m := _RE_CTA_VENDA.search(t)):
        achados.append(Achado(Nivel.aviso, "mistura_frentes", "Peça de captação com linguagem de venda.", _trecho(t, m)))

    return achados


def texto_publicavel(peca: Peca) -> str:
    """Somente o que vai ao ar (não inclui checklist/afirmações, que falam *sobre* as regras)."""
    partes = [*peca.ganchos, peca.copy_principal, peca.legenda, peca.cta]
    for c in peca.roteiro:
        partes += [c.texto_tela or "", c.narracao or ""]
    for v in peca.variacoes:
        partes += [v.gancho, v.texto]
    return "\n".join(p for p in partes if p)


def verificar_peca(peca: Peca, brief: Brief, *, negocio: dict | None = None, produto: Aparelho | None = None) -> list[Achado]:
    achados = verificar_texto(texto_publicavel(peca), frente=brief.frente, negocio=negocio, produto=produto)

    if FRENTE_POR_PILAR[brief.pilar] != brief.frente:
        achados.append(Achado(Nivel.aviso, "frente_pilar", f"Pilar {brief.pilar.value} normalmente pertence à frente {FRENTE_POR_PILAR[brief.pilar].value}."))

    for a in peca.afirmacoes:
        if a.status == StatusFonte.fato_confirmado and not a.fonte:
            achados.append(Achado(Nivel.revisao_humana, "fato_sem_fonte", "Afirmação marcada como fato sem fonte.", a.texto))
        elif a.status == StatusFonte.informacao_pendente:
            achados.append(Achado(Nivel.revisao_humana, "informacao_pendente", "Informação pendente.", a.texto))

    if brief.frente == Frente.venda and brief.produto_id:
        achados.append(Achado(Nivel.revisao_humana, "unidade_estoque", "Peça de unidade real: confirme disponibilidade, dados e fotos reais antes de publicar."))
    if brief.formato.value == "anuncio":
        achados.append(Achado(Nivel.revisao_humana, "anuncio", "Anúncios exigem aprovação explícita e revisão das políticas vigentes da Meta."))

    if peca.prompt_imagem:
        achados += verificar_prompt_imagem(peca.prompt_imagem, brief=brief)

    return _deduplicar(achados)


def verificar_prompt_imagem(prompt: str, *, brief: Brief | None = None) -> list[Achado]:
    achados: list[Achado] = []
    p = prompt.lower()
    # Remove trechos negativos ("no visible damage") antes de procurar avarias.
    p_sem_negativas = re.sub(r"\b(no|without|sem|nenhum[a]?)\s+[\w\s'-]{0,40}?(crack\w*|scratch\w*|damage\w*|broken|dent\w*|trinc\w*|arranh\w*|avaria\w*|quebrad\w*|riscad\w*|amassad\w*)", " ", p)
    if m := _RE_AVARIA_PROMPT.search(p_sem_negativas):
        achados.append(Achado(Nivel.revisao_humana, "avaria_simulada", "Prompt menciona avaria: não simular avarias inexistentes.", _trecho(p, m)))
    if m := _RE_LOGO_PROMPT.search(re.sub(r"\bno apple logo\w*", " ", p)):
        achados.append(Achado(Nivel.aviso, "logo_apple", "Evite logotipo da Apple como elemento de marca.", _trecho(p, m)))
    return achados


def bloqueio_imagem(brief: Brief) -> Achado | None:
    """Imagem gerada não pode representar unidade real à venda."""
    if brief.frente == Frente.venda and brief.produto_id:
        return Achado(
            Nivel.bloqueio,
            "imagem_unidade_real",
            "Peça de unidade do estoque: use somente fotos reais do aparelho (CREATIVE_STANDARDS.md).",
        )
    return None


def tem_bloqueio(achados: list[Achado]) -> bool:
    return any(a.nivel == Nivel.bloqueio for a in achados)


def _deduplicar(achados: list[Achado]) -> list[Achado]:
    vistos, saida = set(), []
    for a in achados:
        chave = (a.regra, a.trecho)
        if chave not in vistos:
            vistos.add(chave)
            saida.append(a)
    ordem = {Nivel.bloqueio: 0, Nivel.revisao_humana: 1, Nivel.aviso: 2}
    return sorted(saida, key=lambda a: ordem[a.nivel])
