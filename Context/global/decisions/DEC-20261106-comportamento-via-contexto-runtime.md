---
id: CTX-DEC-20261106-comportamento-via-contexto-runtime
type: decision
title: O comportamento do agente de conteúdo muda em contexto/, não no código
branch: global
tags: [contexto-runtime, arquitetura]
status: active
confidence: high
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-readme]
related: [CTX-DEC-20261106-haiku-padrao-sonnet-final]
valid_from: 2026-11-06
---

# Comportamento via `contexto/`

## Decisão
Marca, públicos, pilares, copy, padrões criativos e regras de qualidade vivem em `contexto/*.md`, carregados por `agente/contexto.py` em **toda** chamada (ordem fixa + qualquer `.md` extra da pasta). Para mudar o que o agente escreve, edite esses arquivos.

## Motivo
O dono consegue ajustar o agente sem programar; o código fica para o que é determinístico (guardrails, dados, arte, fluxo).

## Consequências
- Cada `.md` em `contexto/` aumenta o custo de toda chamada; mantenha-os enxutos (o corte de custo de `29f3a22` incluiu prompt enxuto).
- Regras que **precisam** ser garantidas não ficam só no texto do contexto: também viram verificação em `agente/guardrails.py`.
- `Context/` (esta memória) nunca deve ser colocada em `contexto/`.
