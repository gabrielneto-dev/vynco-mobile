# Branch: software

**Propósito:** como o agente de conteúdo é construído e operado.
**Escopo:** código Python em `agente/`, integração OpenRouter, custos, menu, arte, métricas, backup, testes. Regras de veracidade em código ficam em `guardrails`.

## Estado atual
MVP completo e testado com a API real (06/11/2026); menu interativo, cadastro, arte final, importação de métricas e backup prontos. Primeiro uso real com dados da Vynco Mobile gerou correções (`d307c9e`). 70 funções de teste em `tests/` (não executadas nesta sessão de bootstrap).

## Como rodar
Python ≥ 3.10, `pip install -e ".[dev]"`, `.env` com `OPENROUTER_API_KEY`. `python -m agente` (menu) ou `agente.bat` no Windows. Comandos: ver `README.md`. Testes: `pytest` (cliente falso, grátis).

## Mapa do código (`agente/`)
| Módulo | Papel |
|---|---|
| `config.py` | Variáveis de ambiente (`.env`): modelos, timeout, `MAX_TOKENS`, `ESFORCO_RACIOCINIO`, `COTACAO_DOLAR`, `DIR_*` |
| `contexto.py` | Carrega `contexto/*.md` + `dados/` (negocio confirmado/pendente, estoque) |
| `schemas.py` | Brief e saídas estruturadas (Pydantic) |
| `prompts.py` | Montagem dos prompts |
| `llm.py` | Cliente OpenRouter: JSON validado, nova tentativa, fallback do `response_format`, detecção de texto sem acento |
| `imagem.py` | Nano Banana (proporção, tamanho, imagens de referência) |
| `modos.py` | planejar, criar, lote, adaptar, revisar, analisar, imagens |
| `guardrails.py` | Verificações determinísticas (branch `guardrails`) |
| `armazenamento.py` | Registro de peças, versões, status, publicações em `saida/` |
| `cadastro.py` | Dados do negócio e estoque pelo menu |
| `arte.py` | Arte final com Pillow (4:5, 9:16, cartelas de Reel), zonas seguras, selo "Imagem ilustrativa" |
| `metricas.py` | Importação de exportações da Meta, normalização de números |
| `backup.py` | Espelho incremental de `saida/` e `dados/` para `BACKUP_DIR` (nunca apaga no destino; `.env` fora) |
| `menu.py` (1283 linhas), `visual.py` | Menu questionary/rich e exibição compartilhada |
| `cli.py` | Comandos typer |

## Registros
| ID | Tipo | Status |
|---|---|---|
| `CTX-DEC-20261106-haiku-padrao-sonnet-final` | decision | active |
| `CTX-DEC-20261106-openrouter-chave-unica` | decision | active |
| `CTX-FCT-20261106-custos-medidos` | fact | active (temporal) |
| `CTX-RES-20261106-haiku-vs-sonnet` | research | active |
| `CTX-NTE-20261106-haiku-perde-acentuacao` | note (lição) | active |
| `CTX-NTE-20261106-numeros-milhar-ptbr` | note (lição) | active |
| `CTX-QUE-20261106-colunas-exportacao-meta` | question | open |

## Riscos
`CTX-RSK-20261106-saldo-de-credito-api` (global). `menu.py` passa do limite de ~800 linhas recomendado — candidato a divisão quando for mexido.

## Relações
`guardrails` (verificações), `marketing` (métricas), `negocio` (dados lidos de `dados/`).
