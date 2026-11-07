---
id: CTX-DEC-20261106-openrouter-chave-unica
type: decision
title: OpenRouter como gateway único para texto e imagem
branch: software
tags: [llm, imagem, arquitetura]
status: active
confidence: high
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-readme]
valid_from: 2026-11-06
---

# OpenRouter com uma chave

## Decisão
Texto e imagem passam pelo OpenRouter (`agente/llm.py`, `agente/imagem.py`), com uma só variável `OPENROUTER_API_KEY` no `.env`. Qualquer modelo com structured outputs serve para texto.

## Motivo
Um único cadastro/crédito para o dono; trocar de modelo é mudar uma variável.

## Consequências
Saída estruturada validada com Pydantic e nova tentativa automática; se o provedor recusar `response_format` (HTTP 400), o schema vai no texto do pedido.
