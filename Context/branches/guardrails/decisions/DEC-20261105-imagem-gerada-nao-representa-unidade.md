---
id: CTX-DEC-20261105-imagem-gerada-nao-representa-unidade
type: decision
title: Imagem gerada por IA nunca representa a unidade à venda
branch: guardrails
tags: [imagem, guardrails, venda]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1, CTX-SRC-20261106-readme]
valid_from: 2026-11-05
---

# Imagem gerada × foto real

## Decisão
Peça de unidade do estoque usa **somente fotos reais** da unidade. Imagem gerada só para conceitos, educação, captação e campanhas gerais, sem representar falsamente um produto à venda. Avarias nunca são simuladas nem escondidas.

## Como o código garante
Peça com produto do estoque não recebe prompt de imagem e o comando `imagem` é recusado. Fundo gerado por IA recebe o selo "Imagem ilustrativa" na arte final.
