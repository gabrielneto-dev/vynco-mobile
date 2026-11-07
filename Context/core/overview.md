---
id: CTX-SUM-20261107-overview
type: summary
title: Visão geral do projeto
branch: core
tags: [negocio, arquitetura]
status: active
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1, CTX-SRC-20261106-readme]
---

# Visão geral

## O que é

Um **agente de conteúdo de marketing** para a **Vynco Mobile**, loja de iPhones em início de operação em Jales (SP) e região, sem loja física.
É uma aplicação **Python de linha de comando** (menu interativo + comandos) que planeja, cria, adapta, revisa e analisa peças para Instagram, Facebook e Meta Ads.
Texto e imagem passam pelo **OpenRouter** (Claude Haiku/Sonnet para texto; Gemini "Nano Banana" para imagem).

## Para quem

O dono da loja (operador único, sem equipe técnica), que usa o menu no Windows (`agente.bat`), aprova e publica as peças **manualmente**.

## Escopo

- Duas frentes comerciais que nunca se misturam numa peça: **venda** de iPhones e **captação** (compra de usados de pessoa física).
- Cinco pilares editoriais, quatro públicos-hipótese, formatos Reel/carrossel/imagem/Stories/anúncio.
- Fora do escopo atual: publicação automática, configuração de campanhas, movimentação financeira (não autorizados).

## Componentes

| Parte | Onde | Papel |
|---|---|---|
| Contexto de runtime | `contexto/*.md` | Regras de marca, públicos, pilares, copy, criativo e qualidade enviadas ao LLM em toda chamada |
| Dados confirmados | `dados/negocio.json`, `dados/estoque.json` | Única fonte de fatos comerciais; `null` vira `[PENDENTE]` |
| Código | `agente/` | Modos, guardrails determinísticos, arte (Pillow), métricas, backup, menu |
| Saídas | `saida/` (fora do git) | Peças JSON+Markdown, imagens, artes, calendários, revisões, análises |
| Testes | `tests/` | pytest com cliente falso, sem custo |

Mapa detalhado do código: `branches/software/_index.md`.
