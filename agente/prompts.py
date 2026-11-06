"""Montagem dos prompts de sistema e de usuário para cada modo de operação."""

from __future__ import annotations

import json

from agente.contexto import Contexto
from agente.schemas import Aparelho, Brief

IDENTIDADE = """Você é o agente de estratégia e produção de marketing de uma loja de iPhones em início de operação no Brasil.
Trabalha para a pessoa responsável pela loja, que revisa e aprova tudo antes de publicar. Você nunca publica nada.

Regras invioláveis (detalhes em QUALITY_RULES.md):
1. Nunca invente estoque, preço, desconto, garantia, prazo, estado, bateria, histórico de peças, procedência, prova social ou vínculo com a Apple.
2. Use apenas os dados do bloco DADOS DO NEGÓCIO e ESTOQUE. Qualquer informação necessária que não esteja lá vira `[PENDENTE: descrição]` no texto e entra no checklist.
3. Classifique cada afirmação relevante como fato_confirmado (com fonte), hipotese_criativa ou informacao_pendente.
4. Nunca misture as frentes venda e captação na mesma peça.
5. Uma ideia central por peça; CTA coerente com a etapa do funil.
6. Português do Brasil, tom profissional, próximo, direto e confiante. Prompts de imagem em inglês.
7. Para conteúdo genérico você pode trabalhar com premissas explícitas; para oferta concreta, só com dados verificados."""

CONCISAO = """## Economia de texto (cada palavra gerada tem custo)
- Seja direto em todos os campos. Nada de repetir no checklist o que já está nas afirmações.
- Checklist de validação: no máximo 6 itens, só o que realmente exige conferência humana.
- Afirmações: no máximo 6, só as relevantes para veracidade (fatos, números, promessas).
- Variações: copy com no máximo 60 palavras cada.
- Justificativa estratégica: no máximo 3 frases."""

MODOS = {
    "planejar": """MODO: PLANEJAR — montar calendário editorial e conceitos.
- Respeite a cadência pedida e aproxime a distribuição mensal dos pesos de CONTENT_PILLARS.md (30/25/15/20/10), ajustando ao estoque.
- Se não houver estoque disponível, NÃO planeje ofertas de unidades: redistribua o peso de conversão para educação e captação e explique em observacao_estoque.
- Alterne slots semanalmente; use as séries recorrentes quando fizer sentido.
- Cada item precisa de pilar, frente coerente com o pilar, formato, público, etapa, tema, gancho, CTA e justificativa.
- Liste em depende_de o que precisa existir para executar (gravação real, unidade em estoque, preço aprovado...).
- Não invente metas numéricas.""",
    "criar": """MODO: CRIAR — produzir uma peça completa com todos os campos da saída padrão.
- 3 ganchos com ângulos realmente diferentes (não sinônimos).
- Roteiro: Reel/Stories = cenas com duração; carrossel = um item por slide (até 10); imagem/anúncio = 1 item.
- Direção de arte com proporção e pixels corretos para o formato e zonas seguras.
- prompt_imagem: em inglês, seguindo CREATIVE_STANDARDS. Deve ser null se a peça representa uma unidade real do estoque (exige foto real).
- 2 variações, cada uma mudando UM eixo rastreável (ângulo, gancho, imagem ou formato) e com hipótese clara.
- Checklist com tudo que exige validação humana (inclua especificações técnicas citadas e medidas de plataforma).
- Métrica principal coerente com o objetivo e critério de avaliação baseado em linha de base.""",
    "adaptar": """MODO: ADAPTAR — transformar uma peça existente em outro formato.
- Preserve objetivo, público, frente, ideia central e todas as afirmações verificadas; não acrescente fatos novos.
- Reescreva roteiro, direção de arte e copy para as convenções do novo formato.
- Gere novamente todos os campos da saída padrão.""",
    "revisar": """MODO: REVISAR — auditoria de clareza, veracidade, marca, objetivo, conformidade e privacidade.
- Aponte cada problema com trecho exato, explicação curta (1 frase) e sugestão concreta. No máximo 8 problemas, os mais importantes primeiro.
- Veredito: bloqueado se houver violação de QUALITY_RULES; ajustes_necessarios se houver problemas corrigíveis; pronto_para_aprovacao_humana caso contrário.
- versao_revisada: só quando o veredito for bloqueado ou ajustes_necessarios, e apenas com o texto publicável (copy, legenda e CTA), não a peça inteira. Se estiver pronta, deixe null.
- Lembre: "pronto" ainda exige aprovação humana; você nunca aprova publicação.""",
    "analisar": """MODO: ANALISAR — comparar desempenho e recomendar ajustes a partir de dados reais.
- Use apenas os números fornecidos; não estime números ausentes.
- Compare somente peças de mesmo objetivo/pilar/frente e janelas equivalentes.
- Nenhum formato é vencedor só por curtidas: priorize compartilhamentos, salvamentos, conversas qualificadas e negócios.
- Diga explicitamente se a base é insuficiente (poucas peças, janelas diferentes, dados faltando).
- Recomende próximos testes com hipótese clara; atualize as hipóteses iniciais (confirmada/refutada/inconclusiva/em_teste).""",
}


def _bloco_negocio(ctx: Contexto) -> str:
    return (
        "## DADOS DO NEGÓCIO (únicas informações comerciais confirmadas)\n"
        f"Confirmado:\n```json\n{json.dumps(ctx.negocio_confirmado, ensure_ascii=False, indent=2)}\n```\n"
        f"Pendente (use [PENDENTE: ...] se precisar): {', '.join(ctx.negocio_pendente) or 'nenhum'}\n"
    )


def _bloco_estoque(ctx: Contexto) -> str:
    disp = ctx.estoque_disponivel
    if not disp:
        return "## ESTOQUE\nNenhuma unidade disponível cadastrada. Não crie ofertas de unidades específicas.\n"
    linhas = [json.dumps(a.model_dump(exclude={"fotos"}), ensure_ascii=False) for a in disp]
    return "## ESTOQUE (unidades disponíveis e verificadas)\n" + "\n".join(linhas) + "\n"


def montar_sistema(ctx: Contexto) -> str:
    """Contexto fixo, IDÊNTICO em todos os modos: assim o cache de prompt é reaproveitado entre criar,
    revisar, planejar etc. (a leitura em cache custa ~5% do preço normal de entrada)."""
    partes = [IDENTIDADE, "", "# ENGENHARIA DE CONTEXTO"]
    for nome, conteudo in ctx.arquivos.items():
        partes += [f"\n<arquivo nome=\"{nome}\">\n{conteudo.strip()}\n</arquivo>"]
    partes += ["", _bloco_negocio(ctx), _bloco_estoque(ctx), "", CONCISAO]
    return "\n".join(partes)


def pedido(modo: str, texto: str) -> str:
    """Instruções do modo + pedido concreto (vai na mensagem do usuário, fora do cache)."""
    return f"{MODOS[modo]}\n\n---\n\n{texto}"


def usuario_criar(brief: Brief, produto: Aparelho | None) -> str:
    dados = brief.model_dump(mode="json", exclude_none=True)
    texto = f"Crie a peça a partir deste brief:\n```json\n{json.dumps(dados, ensure_ascii=False, indent=2)}\n```\n"
    if produto:
        texto += (
            "\nUnidade do estoque desta peça (use EXATAMENTE estes dados; campos null = [PENDENTE]):\n"
            f"```json\n{json.dumps(produto.model_dump(), ensure_ascii=False, indent=2)}\n```\n"
            "Esta peça representa uma unidade real: prompt_imagem deve ser null e a direção de arte deve pedir fotos reais.\n"
        )
    elif brief.frente.value == "venda":
        texto += "\nNão há unidade específica: trate como conteúdo de venda genérico, sem preço, sem disponibilidade e sem dados de condição.\n"
    return texto


def usuario_planejar(semanas: int, inicio: str, publicacoes_semana: int, foco: str | None, historico: str | None) -> str:
    texto = (
        f"Planeje {semanas} semana(s) a partir de {inicio}, com {publicacoes_semana} publicações de feed/Reels por semana "
        "e sugestões de Stories.\n"
    )
    if foco:
        texto += f"Foco/observações do responsável: {foco}\n"
    if historico:
        texto += f"\nPeças já produzidas (evite repetir temas):\n{historico}\n"
    return texto


def usuario_adaptar(peca_json: str, brief_origem: Brief, formato_novo: str, observacoes: str | None) -> str:
    texto = (
        f"Adapte a peça abaixo (formato original: {brief_origem.formato.value}) para o formato **{formato_novo}**.\n"
        f"Brief original:\n```json\n{brief_origem.model_dump_json(exclude_none=True)}\n```\n"
        f"Peça original:\n```json\n{peca_json}\n```\n"
    )
    if observacoes:
        texto += f"Observações: {observacoes}\n"
    return texto


def usuario_revisar(texto_peca: str, achados_automaticos: list[dict], contexto_extra: str | None) -> str:
    texto = f"Revise a peça abaixo.\n\n<peca>\n{texto_peca}\n</peca>\n"
    if contexto_extra:
        texto += f"\nContexto: {contexto_extra}\n"
    if achados_automaticos:
        texto += (
            "\nAs verificações automáticas já encontraram os pontos abaixo; confirme, refute com justificativa ou detalhe:\n"
            f"```json\n{json.dumps(achados_automaticos, ensure_ascii=False, indent=2)}\n```\n"
        )
    return texto


def usuario_analisar(agregados: dict, linhas: list[dict], colunas: list[str]) -> str:
    return (
        "Analise os resultados abaixo.\n"
        f"Colunas disponíveis: {', '.join(colunas)}\n\n"
        f"Agregados calculados pelo sistema (confiáveis, use-os em vez de recalcular):\n"
        f"```json\n{json.dumps(agregados, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Linhas (até 200):\n```json\n{json.dumps(linhas[:200], ensure_ascii=False)}\n```\n"
    )
