# Project State

Last updated: 2026-11-07
Latest checkpoint: `Context/checkpoints/CP-20261107-1129-bootstrap-contexto.md`

## Current objective
Sair do MVP para o uso real: completar os dados do negócio, publicar as primeiras peças (manualmente) e formar a linha de base de métricas.

## Working
- MVP completo: planejar, criar, lote, adaptar, revisar, analisar, imagem, arte final, cadastro, importação de métricas, backup, menu (`d307c9e`).
- Os 8 critérios de aceite do briefing atendidos (nº 8 com ressalva: medição real depende de publicar).
- Guardrails sem falso negativo conhecido; Haiku como padrão com correção de acentuação.
- Memória `Context/` + `AGENTS.md`/`CLAUDE.md` instalados (07/11/2026, branch `claude/context-engineering-bootstrap-6c3fd0`, ainda não mesclada na `main`).

## In progress
Nada em andamento no código.

## Blockers
- **Estoque vazio** → nenhuma peça de venda concreta (`CTX-FCT-20261106-estoque-vazio`).
- **Sem contas de Instagram/Facebook registradas** → sem publicação nem métricas reais (`CTX-QUE-20261106-contas-redes-sociais`).

## Active decisions
- Aprovação humana; nenhuma publicação automática (`CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica`).
- Venda × captação separadas (`CTX-DEC-20261105-separar-venda-e-captacao`).
- Haiku padrão, Sonnet para final/revisão (`CTX-DEC-20261106-haiku-padrao-sonnet-final`).

## Open critical questions
- Garantia e devolução (`CTX-QUE-20261106-garantia-e-devolucao`).
- Colunas reais da exportação da Meta (`CTX-QUE-20261106-colunas-exportacao-meta`).
- Orçamento e capacidade para anúncios (`CTX-QUE-20261105-orcamento-e-capacidade-de-anuncios`).

## Next likely steps
1. (Dono) Preencher garantia, devolução, redes sociais, paleta e logo pelo menu; `reverificar` as peças.
2. (Dono) Cadastrar unidades reais com fotos e preço aprovado.
3. Publicar as primeiras peças e registrar com `publicado`.
4. Importar a primeira exportação real da Meta e calibrar `agente/metricas.py`.
5. Não verificado nesta sessão: rodar `pytest` num ambiente com as dependências.
