---
id: CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica
type: decision
title: Aprovação humana obrigatória e nenhuma publicação automática
branch: global
tags: [aprovacao-humana, publicacao, guardrails]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1, CTX-SRC-20261106-readme]
related: [CTX-DEC-20261105-separar-venda-e-captacao]
valid_from: 2026-11-05
---

# Aprovação humana e publicação manual

## Contexto
Loja em início de operação; um erro de preço, estoque ou promessa vai a público e custa reputação. Briefing §13 e §20.

## Decisão
- Preços, promoções, claims comerciais, publicações e anúncios exigem aprovação humana.
- A primeira versão publica **manualmente**. O agente **não tem** integração de publicação; `publicado` só registra o que o dono fez à mão (data, URL, responsável).
- **Não autorizado:** publicação automática, configuração de campanhas, execução de anúncios, movimentação financeira.

## Como o código garante
- `status aprovado` exige `--responsavel` e zero bloqueios; `publicado` só depois de `aprovado`.
- Fluxo de status: ideia → em criação → revisão → aprovado → publicado → analisado → reutilizável/arquivado.

## Consequências
Qualquer automação futura de publicação precisa de nova decisão explícita do dono e controles de aprovação (ver `future/`).
