---
id: CTX-NTE-20261106-numeros-milhar-ptbr
type: note
title: Números com ponto de milhar ("4.200") eram lidos como decimais
branch: software
tags: [metricas, licao-aprendida]
status: active
confidence: verified
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: [CTX-QUE-20261106-colunas-exportacao-meta]
valid_from: 2026-11-06
---

# Lição: separador de milhar em pt-BR

## Problema
"4.200" (milhar) virava 4,2 na leitura de CSVs — afetava a importação da Meta e o CSV manual do `analisar`.

## Solução validada
Corrigido em `agente/metricas.py` e coberto por teste (`tests/test_metricas.py`).

## Evitar
Qualquer parser novo de números de exportações (pt/en) deve reaproveitar a mesma função e ganhar teste com "4.200", "4,2" e "1,234.5".
