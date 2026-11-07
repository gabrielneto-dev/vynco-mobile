---
id: CTX-RSK-20261106-novos-falsos-positivos
type: risk
title: Novos falsos positivos/negativos nas verificações por palavra-chave
branch: guardrails
tags: [guardrails, falso-positivo]
status: active
confidence: high
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: [CTX-NTE-20261106-falsos-positivos-palavra-chave]
---

# Risco: regras por palavra-chave

- **Impacto:** falso positivo bloqueia peças boas e irrita o operador; falso negativo deixa passar algo proibido (mais grave).
- **Probabilidade:** alta — já foram 5 casos em dois dias de uso.
- **Mitigação:** fluxo corrigir → teste → `reverificar`; revisão humana continua obrigatória antes de publicar.
