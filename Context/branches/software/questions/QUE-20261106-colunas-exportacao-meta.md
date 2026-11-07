---
id: CTX-QUE-20261106-colunas-exportacao-meta
type: question
title: Quais são os nomes reais das colunas na exportação de métricas da Meta?
branch: software
tags: [metricas, plataforma-meta]
status: open
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: [CTX-DEC-20261105-sem-metas-sem-linha-de-base, CTX-QUE-20261106-contas-redes-sociais]
---

# Colunas da exportação da Meta?

## Por que importa
`agente/metricas.py` foi testado só com exportações **sintéticas** (PT e EN). Os nomes de coluna variam por idioma e versão; se não baterem, a importação não liga métricas às peças.

## Como resolver
Quando houver a primeira publicação, exportar os insights reais, rodar `importar-metricas <arquivo>` e ajustar os mapeamentos. Adicionar o cabeçalho real (sem dados pessoais) como fixture de teste.
