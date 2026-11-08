"""Modelos de dados: entradas (brief), saídas estruturadas do LLM e dados do negócio."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- enums
class Pilar(str, Enum):
    atracao = "atracao"
    educacao = "educacao"
    relacionamento = "relacionamento"
    conversao = "conversao"
    captacao = "captacao"


class Frente(str, Enum):
    venda = "venda"
    captacao = "captacao"
    marca = "marca"


class Formato(str, Enum):
    reel = "reel"
    carrossel = "carrossel"
    imagem = "imagem"
    stories = "stories"
    anuncio = "anuncio"


class Publico(str, Enum):
    A = "A"  # comprador econômico
    B = "B"  # quer trocar de modelo
    C = "C"  # vendedor de usado
    D = "D"  # seguidor em formação


class Etapa(str, Enum):
    descoberta = "descoberta"
    interesse = "interesse"
    confianca = "confianca"
    intencao = "intencao"
    conversao = "conversao"
    fidelizacao = "fidelizacao"


class StatusFonte(str, Enum):
    fato_confirmado = "fato_confirmado"
    hipotese_criativa = "hipotese_criativa"
    informacao_pendente = "informacao_pendente"


class StatusPeca(str, Enum):
    ideia = "ideia"
    em_criacao = "em_criacao"
    revisao = "revisao"
    aprovado = "aprovado"
    publicado = "publicado"
    analisado = "analisado"
    reutilizavel = "reutilizavel"
    arquivado = "arquivado"


PESO_PILAR = {
    Pilar.atracao: 0.30,
    Pilar.educacao: 0.25,
    Pilar.relacionamento: 0.15,
    Pilar.conversao: 0.20,
    Pilar.captacao: 0.10,
}

FRENTE_POR_PILAR = {
    Pilar.atracao: Frente.marca,
    Pilar.educacao: Frente.marca,
    Pilar.relacionamento: Frente.marca,
    Pilar.conversao: Frente.venda,
    Pilar.captacao: Frente.captacao,
}

ETAPA_POR_PILAR = {
    Pilar.atracao: Etapa.descoberta,
    Pilar.educacao: Etapa.confianca,
    Pilar.relacionamento: Etapa.interesse,
    Pilar.conversao: Etapa.intencao,
    Pilar.captacao: Etapa.intencao,
}

PUBLICO_POR_PILAR = {
    Pilar.atracao: Publico.A,
    Pilar.educacao: Publico.A,
    Pilar.relacionamento: Publico.D,
    Pilar.conversao: Publico.A,
    Pilar.captacao: Publico.C,
}

PROPORCAO_POR_FORMATO = {
    Formato.reel: "9:16",
    Formato.stories: "9:16",
    Formato.carrossel: "4:5",
    Formato.imagem: "4:5",
    Formato.anuncio: "4:5",
}


# --------------------------------------------------------------------------- dados do negócio
class Aparelho(BaseModel):
    """Unidade real do estoque. Campos None = não verificados (viram [PENDENTE])."""

    model_config = ConfigDict(extra="allow")

    id: str
    modelo: str
    armazenamento_gb: int | None = None
    cor: str | None = None
    condicao: str | None = None
    saude_bateria_pct: int | None = None
    pecas_trocadas: str | None = None
    procedencia: str | None = None
    garantia: str | None = None
    preco_aprovado_brl: float | None = None
    disponivel: bool = False
    fotos: list[str] = Field(default_factory=list)
    verificado_por: str | None = None
    verificado_em: str | None = None


# --------------------------------------------------------------------------- entrada
class Brief(BaseModel):
    objetivo: str
    pilar: Pilar
    frente: Frente
    publico: Publico
    etapa: Etapa
    formato: Formato
    canais: list[str] = Field(default_factory=lambda: ["instagram", "facebook"])
    produto_id: str | None = None
    regiao: str | None = None
    oferta: str | None = None
    cta: str | None = None
    restricoes: str | None = None
    referencias: str | None = None
    serie: str | None = None
    origem: str | None = None  # ex.: id do calendário ou da peça adaptada


# --------------------------------------------------------------------------- saídas do LLM
class Afirmacao(BaseModel):
    texto: str = Field(description="Afirmação feita na peça (fato, número, característica, promessa).")
    status: StatusFonte
    fonte: str | None = Field(
        default=None,
        description="Origem do fato (negocio.json, estoque:<id>, especificação pública). Obrigatória se fato_confirmado.",
    )


class Cena(BaseModel):
    ordem: int
    visual: str = Field(description="O que aparece na tela/slide.")
    texto_tela: str | None = Field(default=None, description="Texto sobreposto (curto).")
    narracao: str | None = Field(default=None, description="Fala/locução, quando houver.")
    duracao_s: float | None = Field(default=None, description="Duração em segundos (Reels/Stories).")


class DirecaoArte(BaseModel):
    proporcao: str = Field(description="Ex.: 9:16, 4:5, 1:1.")
    dimensoes_px: str = Field(description="Ex.: 1080x1920.")
    elementos_visuais: list[str]
    hierarquia: str = Field(description="Ordem de leitura: título → informação → CTA.")
    paleta: str
    tipografia: str
    zonas_seguras: str
    fonte_imagens: str = Field(description="'foto real: <qual>' ou 'imagem gerada: <conceito>'.")


class Variacao(BaseModel):
    nome: str
    eixo: str = Field(description="O ÚNICO eixo que muda: angulo, gancho, imagem ou formato.")
    hipotese: str = Field(description="O que esta variação testa.")
    gancho: str
    texto: str = Field(description="Copy completa da variação.")


class ItemValidacao(BaseModel):
    campo: str
    motivo: str
    status: StatusFonte


class Metrica(BaseModel):
    principal: str
    apoio: list[str]
    criterio_avaliacao: str = Field(description="Como julgar o resultado sem metas inventadas (comparar com linha de base).")


class Peca(BaseModel):
    """Saída padrão por peça (seção 12 do briefing)."""

    titulo_interno: str
    objetivo: str
    objecao_ou_interesse: str = Field(description="Objeção ou interesse do público tratado pela peça.")
    ideia_central: str
    justificativa_estrategica: str
    ganchos: list[str] = Field(min_length=3, max_length=3, description="Exatamente 3 opções de gancho/título com ângulos distintos, cada uma com no máximo 7 palavras (vira o título da arte).")
    copy_principal: str
    legenda: str
    cta: str
    roteiro: list[Cena] = Field(description="Cenas do Reel/Stories ou slides do carrossel; 1 item para imagem estática.")
    direcao_arte: DirecaoArte
    prompt_imagem: str | None = Field(
        default=None,
        description="Prompt em inglês para Nano Banana. null se a peça exige foto real.",
    )
    variacoes: list[Variacao] = Field(min_length=2, max_length=2, description="Exatamente 2 variações para teste.")
    afirmacoes: list[Afirmacao]
    checklist_validacao: list[ItemValidacao] = Field(description="Campos que exigem validação humana antes da publicação.")
    metrica: Metrica


class ItemCalendario(BaseModel):
    data: str = Field(description="AAAA-MM-DD")
    slot: int
    pilar: Pilar
    frente: Frente
    formato: Formato
    publico: Publico
    etapa: Etapa
    serie: str | None = None
    tema: str
    gancho_sugerido: str
    cta: str
    justificativa: str
    depende_de: list[str] = Field(default_factory=list, description="Ex.: 'unidade em estoque', 'gravação real', 'preço aprovado'.")


class Calendario(BaseModel):
    periodo: str
    premissas: list[str] = Field(description="Premissas explícitas usadas no planejamento (não fatos inventados).")
    itens: list[ItemCalendario]
    stories_sugeridos: list[str] = Field(description="Ideias de Stories para dias operacionais com conteúdo real.")
    observacao_estoque: str
    pendencias: list[str] = Field(description="Informações que faltam para executar o plano.")


class Problema(BaseModel):
    categoria: str = Field(description="clareza | veracidade | marca | objetivo | conformidade | privacidade | funil | formato")
    severidade: str = Field(description="alta | media | baixa")
    trecho: str
    explicacao: str
    sugestao: str


class Revisao(BaseModel):
    veredito: str = Field(description="pronto_para_aprovacao_humana | ajustes_necessarios | bloqueado")
    resumo: str
    problemas: list[Problema]
    pontos_fortes: list[str]
    campos_para_validar: list[str]
    versao_revisada: str | None = Field(default=None, description="Texto revisado completo, se houver ajustes.")


class Comparacao(BaseModel):
    grupo: str = Field(description="Grupo comparado (mesmo objetivo/pilar/frente).")
    observacao: str
    evidencia: str = Field(description="Números da tabela que sustentam a observação.")


class HipoteseAvaliada(BaseModel):
    hipotese: str
    status: str = Field(description="confirmada | refutada | inconclusiva | em_teste")
    evidencia: str


class Recomendacao(BaseModel):
    acao: str
    motivo: str
    prioridade: str = Field(description="alta | media | baixa")


class Analise(BaseModel):
    resumo: str
    base_suficiente: bool = Field(description="Há dados suficientes para conclusões? (amostra, janela, comparabilidade)")
    comparacoes: list[Comparacao]
    aprendizados: list[str]
    hipoteses: list[HipoteseAvaliada]
    recomendacoes: list[Recomendacao]
    limitacoes: list[str]
