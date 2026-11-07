---
id: CTX-DEC-20261105-separar-venda-e-captacao
type: decision
title: Venda e captação de usados são frentes separadas
branch: global
tags: [venda, captacao, campanhas, metricas]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1]
related: [CTX-DEC-20261105-cinco-pilares-editoriais]
valid_from: 2026-11-05
---

# Venda × captação

## Contexto
A loja precisa de demanda (compradores) e de oferta (pessoas vendendo o próprio iPhone). Misturar as duas mensagens confunde o público e as métricas.

## Decisão
As frentes compartilham a marca, mas têm criativos, CTAs, formulários de qualificação e métricas **separados**. Campanha A (captação) e B (venda) nunca se misturam.

## Como o código garante
A frente é derivada do pilar (`conversao` → venda; `captacao` → captação) e há alerta de mistura de CTAs nos guardrails.

## Consequências
Métricas e análises comparam peças de mesmo objetivo; o importador de métricas e o `analisar` respeitam a frente.
