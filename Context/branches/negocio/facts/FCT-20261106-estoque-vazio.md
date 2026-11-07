---
id: CTX-FCT-20261106-estoque-vazio
type: fact
title: Estoque sem nenhuma unidade cadastrada
branch: negocio
tags: [estoque, venda]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
related: [CTX-DEC-20261105-separar-venda-e-captacao]
valid_from: 2026-11-06
revisit_at: 2026-11-20
---

# Estoque vazio

`dados/estoque.json` está `[]` (verificado em 07/11/2026). Consequências no comportamento do agente:

- `planejar` troca os slots de venda por captação/relacionamento.
- `lote` pula os itens de venda; `criar --pilar conversao` exige `--produto` (ou `--generico`, sem preço nem disponibilidade).
- Nenhuma oferta concreta pode ser publicada.

Quando o dono cadastrar unidades (menu → 📱 Estoque, com fotos reais e `preco_aprovado_brl`), atualize ou marque este registro como `superseded`.
