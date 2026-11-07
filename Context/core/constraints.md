---
id: CTX-SUM-20261107-constraints
type: summary
title: Restrições duráveis do projeto
branch: core
tags: [guardrails, custo, aprovacao-humana]
status: active
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261105-briefing-estrategico-v1, CTX-SRC-20261106-readme]
---

# Restrições

## Éticas e de veracidade (inegociáveis)

- Nunca inventar estoque, preço, desconto, garantia, prazo, estado, bateria, histórico de peças ou procedência.
- Nada de prova social fictícia, urgência falsa, promessa absoluta ou vínculo com a Apple.
- Nunca orientar contorno de bloqueio de ativação/iCloud; nunca pedir senha/código; não expor IMEI completo.
- Imagem gerada por IA nunca representa a unidade à venda.
- Detalhe e implementação: branch `guardrails`.

## Operacionais

- Aprovação humana obrigatória antes de publicar; publicação é manual (`CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica`).
- Venda e captação separadas em criativos, CTAs e métricas (`CTX-DEC-20261105-separar-venda-e-captacao`).
- Operador único, não técnico: tudo deve ser possível pelo menu, sem editar JSON.

## Financeiras

- Crédito de API pré-pago e pequeno (saldo de ~US$ 3,70 em 06/11/2026). Custo por chamada é preocupação de primeira ordem; o menu mostra o custo antes de cada chamada paga.

## Técnicas

- Python ≥ 3.10; dependências em `pyproject.toml` (httpx, pillow, pydantic, python-dotenv, questionary, rich, typer).
- O dono usa **Windows** (`agente.bat`, `.venv\Scripts`); o código precisa funcionar lá (UTF-8 forçado no `.bat`). O desenvolvimento também ocorre em Linux.
- Uma única chave `OPENROUTER_API_KEY` no `.env` (nunca versionado).
- Saídas em `saida/` e fotos em `dados/fotos/` ficam fora do git; o backup incremental cobre esses dados.

## De plataforma

- Medidas e zonas seguras da Meta são referência e mudam; conferir na documentação vigente antes de publicar.
