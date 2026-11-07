---
id: CTX-RSK-20261106-saldo-de-credito-api
type: risk
title: Saldo pré-pago pequeno no OpenRouter
branch: global
tags: [custo, llm]
status: active
confidence: medium
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: [CTX-FCT-20261106-custos-medidos]
valid_from: 2026-11-06
revisit_at: 2026-12-01
---

# Risco: saldo de crédito

- **Risco:** o crédito acabar no meio de um lote ou durante testes de desenvolvimento.
- **Causa:** saldo de ~US$ 3,70 em 06/11/2026 (total gasto no projeto até então ~US$ 1,30); testes reais com Sonnet consomem rápido.
- **Impacto:** peças/lote incompletos (o `lote` retoma de onde parou, sem cobrar de novo o que já foi gerado).
- **Mitigação:** Haiku como padrão; confirmar com o dono antes de rodar comandos pagos; preferir `reverificar`/`pytest` (gratuitos) para validar mudanças.
- **Sinal:** erro 402/saldo no OpenRouter. Saldo atual: [desconhecido — conferir no painel do OpenRouter].
