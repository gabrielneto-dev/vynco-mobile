---
id: CTX-RES-20261106-haiku-vs-sonnet
type: research
title: Comparação de qualidade Haiku 5.5 × Sonnet 5.5 nas peças
branch: software
tags: [llm, custo]
status: active
confidence: medium
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: [CTX-DEC-20261106-haiku-padrao-sonnet-final]
valid_from: 2026-11-06
---

# Haiku × Sonnet

## Pergunta
Qual modelo usar para cada tarefa, considerando custo e qualidade?

## Escopo e evidência
Testes reais de 06/11/2026: carrossel com Haiku, anúncio e lote com Sonnet, revisões e análise com Sonnet (amostra pequena; avaliação qualitativa do dono + agente).

## Achados
- Haiku: peças corretas e seguras, porém mais genéricas.
- Sonnet: justificativas melhores, checklists mais ricos, revisões mais finas; ~25× o custo por peça.
- Ambos respeitaram as regras de veracidade; nenhum falso negativo dos guardrails.

## Limitações
Amostra pequena, sem métrica de desempenho real (nada publicado). Haiku tem o problema de acentuação com saída nativa (`CTX-NTE-20261106-haiku-perde-acentuacao`).
