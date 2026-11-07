---
id: CTX-CP-20261107-1129-bootstrap-contexto
type: checkpoint
title: Instalação da memória de projeto Context/
branch: global
tags: [bootstrap]
status: active
created_at: 2026-11-07
updated_at: 2026-11-07
related: [CTX-SRC-20261106-historico-git]
---

# Checkpoint: bootstrap do contexto

## Objetivo
Instalar uma memória persistente para agentes de desenvolvimento, sem depender de conversas anteriores.

## O que mudou
- Criados `AGENTS.md` (regras do projeto + bloco `CONTEXT-ENGINEERING`) e `CLAUDE.md` (`@AGENTS.md`). Não existiam antes.
- Criada `Context/` com 4 branches (`negocio`, `marketing`, `software`, `guardrails`), registros globais, fontes, ideias futuras e `_meta/catalogo.py`.
- Nenhum código, dado ou arquivo de `contexto/` foi alterado.

## Descobertas
- Já existia uma pasta `contexto/` (contexto de runtime do agente de conteúdo). Nome parecido com `Context/`, papel diferente — regra explícita no `AGENTS.md`.
- O briefing está desatualizado em dados operacionais (nome da loja, avaliação presencial); `dados/negocio.json` prevalece.

## Estado atual
Ver `STATE.md`. Projeto no ponto do commit `d307c9e` (dados da Vynco Mobile e correções do primeiro uso real).

## Não verificado
`pytest` não rodou nesta sessão (ambiente Linux sem as dependências instaladas).

## Próximos passos
Os de `STATE.md` (preencher pendências do negócio, primeiras publicações, métricas reais).

## Registros criados
Todos os registros em `Context/` (ver `_meta/catalog.jsonl`).
