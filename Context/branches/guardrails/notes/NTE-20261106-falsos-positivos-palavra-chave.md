---
id: CTX-NTE-20261106-falsos-positivos-palavra-chave
type: note
title: Falsos positivos das regras por palavra-chave e como foram corrigidos
branch: guardrails
tags: [guardrails, falso-positivo, licao-aprendida, testes]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao, CTX-SRC-20261106-historico-git]
related: [CTX-RSK-20261106-novos-falsos-positivos]
valid_from: 2026-11-06
---

# Lição: palavra-chave precisa de contexto

O português é ambíguo; regras por palavra solta disparam em frases legítimas. Casos reais corrigidos (todos com teste em `tests/test_guardrails.py`):

| Frase legítima | Regra que disparava | Correção |
|---|---|---|
| "pular a **verificação** do iCloud" | contornar bloqueio | verbos ambíguos só disparam quando o objeto é o próprio bloqueio |
| "em **nenhum** momento pedimos senha" | coleta de dados sensíveis | "nenhum", "momento algum" etc. tratados como negação |
| "página **oficial** da Apple" | vínculo com a Apple | só vale para alegação sobre a loja; respeita negação ("não somos autorizada") |
| "tela sem **riscos**" | promessa absoluta | condição física é removida antes da regra |
| "bateria acima de 80%" (critério de compra cadastrado) | dado de unidade sem fonte | critério do `negocio.json` deixou de contar como dado de unidade (`d307c9e`) |

Teste com 8 violações propositais: todas detectadas, **nenhum falso negativo**.

## Procedimento
Novo falso positivo/negativo → teste de regressão primeiro → corrigir a regra → `reverificar` nas peças afetadas (grátis).

## Evitar
Afrouxar uma regra apagando a palavra-chave inteira: isso cria falso negativo. Restringir pelo contexto (objeto, negação, sujeito).
