---
id: CTX-NTE-20261106-haiku-perde-acentuacao
type: note
title: Haiku 5.5 devolve português sem acento com response_format nativo
branch: software
tags: [llm, acentuacao, licao-aprendida]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-historico-git]
related: [CTX-DEC-20261106-haiku-padrao-sonnet-final]
valid_from: 2026-11-06
revisit_at: 2027-02-01
---

# Lição: Haiku sem acentuação

## Problema
No primeiro uso real (06/11/2026), peças geradas pelo Haiku 5.5 com `response_format` (JSON Schema nativo) vieram em português **sem acentos**.

## Solução validada (commit `d307c9e`, `agente/llm.py`)
- Modelos em `MODELOS_SEM_SAIDA_NATIVA` (`anthropic/claude-haiku`) recebem o schema **no texto do pedido**, sem `response_format` (+~5 mil tokens de entrada, centavos).
- Qualquer modelo que devolva texto longo com < 3 acentos por mil letras (`parece_sem_acento`) é refeito sem `response_format`.
- Guardrail `sem_acentuacao` marca revisão humana se ainda escapar.

## Evitar
Não "otimizar" voltando o Haiku ao `response_format` nativo sem testar de novo a acentuação com a API real. Vale reavaliar quando houver nova versão do modelo.
