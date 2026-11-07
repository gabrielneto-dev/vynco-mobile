# Branch: guardrails

**Propósito:** os limites de veracidade e ética do agente e as verificações automáticas que os garantem.
**Escopo:** `contexto/QUALITY_RULES.md` (o que o LLM é instruído a fazer) + `agente/guardrails.py` (o que o código verifica sempre, sem depender do LLM) + `tests/test_guardrails.py`.

## Estado atual
Regras implementadas e testadas; 5 falsos positivos corrigidos, nenhum falso negativo conhecido. A tabela "Garantias embutidas" do `README.md` mapeia cada regra do briefing para o mecanismo no código — consulte-a em vez de duplicar aqui.

## Conceitos centrais
- Toda afirmação é `fato_confirmado`, `hipotese_criativa` ou `informacao_pendente` (`[PENDENTE: …]`).
- Achados têm nível: **bloqueio** (impede aprovação: preço sem `preco_aprovado_brl`, bateria diferente do estoque, promessa absoluta, vínculo Apple, IMEI, pedir senha, contornar iCloud) ou **revisão humana** (urgência, prova social, garantia/parcelamento não definidos, `[PENDENTE]`, texto sem acentuação).
- `[PENDENTE]` em texto visível impede a arte final (exceto `--rascunho`, com tarja).

## Registros
| ID | Tipo | Status |
|---|---|---|
| `CTX-DEC-20261105-imagem-gerada-nao-representa-unidade` | decision | active |
| `CTX-NTE-20261106-falsos-positivos-palavra-chave` | note (lição) | active |
| `CTX-RSK-20261106-novos-falsos-positivos` | risk | active |
| `CTX-RSK-20261106-especificacoes-iphone-pelo-modelo` | risk | active |

## Decisões ativas (globais)
`CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica`, `CTX-DEC-20261105-separar-venda-e-captacao`.

## Regra operacional
Falso positivo/negativo novo → teste em `tests/test_guardrails.py` → correção → `reverificar` (está no `AGENTS.md`).

## Relações
`negocio` (só `dados/` vira fato), `software` (implementação), `marketing` (tom e limites de copy).
