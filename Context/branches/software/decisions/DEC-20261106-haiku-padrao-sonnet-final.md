---
id: CTX-DEC-20261106-haiku-padrao-sonnet-final
type: decision
title: Haiku como modelo padrão; Sonnet para peças finais e revisão
branch: software
tags: [llm, custo]
status: active
confidence: high
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao, CTX-SRC-20261106-historico-git]
depends_on: [CTX-RES-20261106-haiku-vs-sonnet]
related: [CTX-FCT-20261106-custos-medidos, CTX-DEC-20261106-openrouter-chave-unica]
valid_from: 2026-11-06
---

# Modelo padrão

## Decisão
- `MODELO_TEXTO` padrão: `anthropic/claude-haiku-5.5` (rascunhos, exploração, lote).
- `anthropic/claude-sonnet-5.5` para a peça final e para a revisão (troca no menu).
- `ESFORCO_RACIOCINIO=low` por padrão (raciocínio é cobrado como saída; corta ~40% do Sonnet).
- Imagem: `google/gemini-3.1-flash-image` (Nano Banana 2); `google/gemini-3-pro-image` quando precisar de mais qualidade.

## Motivo
Saldo pequeno e operador único; diferença de qualidade não justifica o custo em rascunhos.

## Consequências
O menu sempre mostra o custo estimado em reais antes de cada chamada paga. Junto com o corte: JSON Schema enviado uma vez só e respostas com limite de tamanho (`MAX_TOKENS`).
