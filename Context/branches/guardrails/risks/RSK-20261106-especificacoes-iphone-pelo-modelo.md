---
id: CTX-RSK-20261106-especificacoes-iphone-pelo-modelo
type: risk
title: Especificações de iPhone citadas pelo modelo podem estar erradas
branch: guardrails
tags: [llm, guardrails, aprovacao-humana]
status: active
confidence: medium
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
---

# Risco: especificações técnicas

- **Causa:** o LLM cita especificações de modelos de memória; não há base de especificações verificada no projeto.
- **Mitigação atual:** `QUALITY_RULES.md` manda marcar especificações citadas como fato para conferência humana; o checklist da peça pede isso.
- **Mitigação possível (não decidida):** tabela de especificações verificadas em `dados/`.
