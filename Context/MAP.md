# Context Map

Roteador: **pergunta → branch → `_index.md` → registro**. Comece aqui e por `STATE.md`; não leia a pasta inteira.
Manual da memória: `README.md`. Busca rápida: `rg -i "<termo>" Context/` ou filtre `_meta/catalog.jsonl`.

## Projeto
- O que é / componentes → `core/overview.md`
- Objetivos e não objetivos → `core/goals.md`
- Restrições (éticas, custo, Windows, plataforma) → `core/constraints.md`
- Termos (frente, pilar, peça, `[PENDENTE]`, `contexto/` × `Context/`) → `core/glossary.md`
- Onde estamos → `STATE.md` · último checkpoint → `checkpoints/` (mais recente pelo nome)

## Branches

### negocio — `branches/negocio/`
Status: active · Tags: `dados-negocio`, `estoque`, `captacao`, `venda`, `pendencia`
- Dados confirmados da loja, região, pagamento → `dados/negocio.json` (verdade) + `CTX-FCT-20261106-dados-confirmados-vynco`
- Estoque / ofertas possíveis → `dados/estoque.json` + `CTX-FCT-20261106-estoque-vazio`
- O que o dono ainda precisa decidir → `type: question` + `status: open` nesta branch

### marketing — `branches/marketing/`
Status: active · Tags: `pilares`, `publicos`, `marca`, `campanhas`, `metricas`
- Estratégia operacional que vai ao LLM → `contexto/*.md` (runtime)
- Pilares, metas, hipóteses de conteúdo e públicos → `_index.md`

### software — `branches/software/`
Status: active · Tags: `llm`, `custo`, `arte`, `metricas`, `menu`, `backup`, `testes`
- Mapa dos módulos de `agente/` e como rodar → `_index.md`
- Escolha de modelo e custo → `CTX-DEC-20261106-haiku-padrao-sonnet-final`, `CTX-FCT-20261106-custos-medidos`
- Erros conhecidos que não devem se repetir → tag `licao-aprendida`

### guardrails — `branches/guardrails/`
Status: active · Tags: `guardrails`, `falso-positivo`, `aprovacao-humana`, `imagem`
- O que bloqueia vs. o que pede revisão humana → `_index.md` + tabela "Garantias embutidas" do `README.md`
- Falsos positivos já resolvidos → `CTX-NTE-20261106-falsos-positivos-palavra-chave`

## Transversal
- Decisões que valem para tudo → `global/decisions/` (aprovação humana, venda × captação, comportamento via `contexto/`)
- Riscos globais → `global/risks/`
- Ideias não aprovadas → `future/`
- Proveniência (briefing, relatório, README, git) → `sources/`
