---
id: CTX-DEC-20261105-sem-metas-sem-linha-de-base
type: decision
title: Nenhuma meta numérica antes de existir linha de base
branch: marketing
tags: [metricas]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1]
related: [CTX-QUE-20261106-colunas-exportacao-meta]
valid_from: 2026-11-05
---

# Sem metas sem linha de base

## Decisão
As primeiras semanas de dados reais formam a linha de base; só depois se definem metas e cortes. Nenhum formato é declarado vencedor só por curtidas; comparar peças de mesmo objetivo e janela equivalente. Medir qualidade das conversas, não só cliques.

## Como o código garante
`analisar` usa agregados calculados pelo código e declara quando a base é insuficiente (teste real: n=1 por grupo → "base insuficiente").
