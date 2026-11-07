---
id: CTX-SUM-20261107-glossary
type: summary
title: Glossário do domínio
branch: core
tags: [negocio, marketing, software]
status: active
created_at: 2026-11-07
updated_at: 2026-11-07
---

# Glossário

| Termo | Significado |
|---|---|
| **Frente** | Linha comercial de uma peça: `venda` (vender iPhone) ou `captacao` (comprar usado). Derivada do pilar; nunca misturar |
| **Captação** | Compra de iPhones usados de pessoa física para formar estoque |
| **Pilar** | Uma das 5 categorias editoriais: atração, educação, relacionamento (retenção), conversão (venda), captação |
| **Peça** | Unidade de conteúdo gerada (`P-AAAAMMDD-<PILAR>-NNN`), com versões `v1`, `v2`… em `saida/pecas/<ID>/` |
| **Calendário** | Plano de peças (`C-AAAAMMDD-NN`) gerado por `planejar` |
| **Unidade** | Aparelho real do estoque (`U1`, `U2`…) em `dados/estoque.json`, com fotos reais |
| **`[PENDENTE: …]`** | Marcador de dado não fornecido; bloqueia a arte final (exceto rascunho com tarja) |
| **Guardrails / verificações** | Regras determinísticas de `agente/guardrails.py` que rodam sempre; achados com severidade `bloqueio` ou que exigem revisão humana |
| **Bloqueio** | Achado que impede aprovar a peça |
| **Reverificar** | Reaplicar os guardrails a peças existentes sem custo de API |
| **Arte final** | PNG pronto para postar, montado localmente com Pillow (`agente/arte.py`) |
| **Nano Banana** | Apelido dos modelos de imagem Gemini (`google/gemini-3.1-flash-image` = Nano Banana 2) |
| **OpenRouter** | Gateway de API usado para texto e imagem com uma única chave |
| **`contexto/`** | Pasta de contexto de *runtime* do agente de conteúdo (vai ao LLM) |
| **`Context/`** | Esta memória do projeto para agentes de desenvolvimento |
| **Séries** | Formatos recorrentes: "iPhone sem cilada", "Vale o upgrade?", "Seu iPhone vale quanto?", "Mito ou verdade?", "Por dentro da avaliação" |
| **Linha de base** | Primeiras semanas de métricas reais, antes de qualquer meta numérica |
