# Context/ — manual da memória do projeto

`Context/` é a memória operacional do projeto para agentes de desenvolvimento (Claude Code, Codex e outros).
Ela existe para que uma sessão nova, sem nenhuma lembrança da conversa anterior, consiga entender o projeto e continuar o trabalho.

> **SESSÃO ≠ MEMÓRIA.** A sessão é descartável; o que precisa sobreviver fica aqui.
>
> **Não confundir com `contexto/`** (minúsculo, em português): aquela pasta é o contexto de *runtime* que o agente de conteúdo envia ao LLM em toda chamada. Nada desta pasta deve ir para lá.

## 1. Estrutura

```text
Context/
├── README.md        este manual
├── MAP.md           L0 — roteador: pergunta → branch → índice → registro
├── STATE.md         L0 — estado atual (pequeno; não é histórico)
├── _meta/           config.yaml, taxonomy.yaml, catalog.jsonl (derivado), changelog.md,
│                    catalogo.py (reconstrói e valida), templates/
├── core/            fundamentos estáveis: overview, goals, constraints, glossary
├── branches/<b>/    L1 _index.md + L2 registros por tipo (facts/, decisions/, questions/…)
├── global/          registros transversais (decisões, hipóteses, perguntas, planos, riscos)
├── checkpoints/     fotografias de continuidade de cada "salvar contexto"
├── sources/         L3 — proveniência (aponta para docs/, commits, arquivos)
├── future/          ideias e possibilidades NÃO aprovadas
└── archive/         material fora do conjunto ativo, mantido por valor histórico
```

Diretórios de tipo vazios são omitidos; crie quando o primeiro registro daquele tipo surgir.

## 2. Fontes de verdade

| Pergunta | Onde |
|---|---|
| Como trabalhar neste repositório | `AGENTS.md` |
| Por onde começar a procurar | `MAP.md` |
| Onde o projeto está agora | `STATE.md` |
| O que o projeto é, quer e não pode | `core/` |
| Conhecimento de um domínio | `branches/<b>/_index.md` → registros |
| Comportamento real do agente | código em `agente/` e regras em `contexto/` |
| Dados reais do negócio e do estoque | `dados/negocio.json`, `dados/estoque.json` |
| Origem de uma informação | `sources/` via `source_ids` |

Os arquivos Markdown são canônicos. `catalog.jsonl` é derivado e pode ser reconstruído.
`Context/` **aponta** para o código, `dados/` e `docs/`; não os copia. Se um registro divergir do código ou de `dados/`, o código/dados vencem e o registro deve ser corrigido.

## 3. Níveis de carregamento

| Nível | Arquivos | Quando ler |
|---|---|---|
| L0 | `MAP.md`, `STATE.md` | Sempre, em tarefa não trivial |
| L1 | `branches/<b>/_index.md` | Só das branches relevantes |
| L2 | registros atômicos | Só os que a tarefa exige |
| L3 | `sources/`, `docs/`, commits, `saida/` | Só para evidência ou validação |

## 4. Tipos de registro

| Prefixo | Tipo | Significa | Pasta |
|---|---|---|---|
| FCT | fact | verdadeiro no escopo atual | `facts/` |
| ASM | assumption | hipótese usada sem confirmação | `assumptions/` |
| QUE | question | pergunta aberta (elemento de primeira classe) | `questions/` |
| RES | research | investigação, com fontes e limitações | `research/` |
| DEC | decision | escolha feita, com motivo | `decisions/` |
| PLN | plan | candidate → planned → in-progress → completed/cancelled | `plans/` |
| RSK | risk | risco, impacto, mitigação | `risks/` |
| EXP | experiment | hipótese, setup, resultado | `experiments/` |
| NTE | note | lição aprendida, conhecimento negativo, observação | `notes/` |
| SRC | source | proveniência | `sources/` |
| SUM | summary | consolidação de vários registros | onde fizer sentido |
| CP | checkpoint | fotografia de sessão | `checkpoints/` |

Hipótese não é fato. Pesquisa não é decisão. Ideia futura não é plano aprovado.

## 5. Metadados (YAML frontmatter)

Mínimo obrigatório: `id`, `type`, `title`, `branch`, `tags`, `status`, `created_at`, `updated_at`.
Opcionais: `confidence`, `source_ids`, `related`, `depends_on`, `supersedes`, `superseded_by`, `valid_from`, `valid_until`, `revisit_at`, `resolved_by`.

```yaml
---
id: CTX-DEC-20261106-haiku-padrao-sonnet-final
type: decision
title: Haiku como modelo padrão; Sonnet para peças finais e revisão
branch: software            # ou global, core
tags: [llm, custo]
status: active
confidence: high
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
related: []
depends_on: []
supersedes: null
superseded_by: null
valid_from: 2026-11-06
valid_until: null
revisit_at: null
---
```

Formato aceito pelo `catalogo.py`: `chave: valor`, listas inline `[a, b]` ou em bloco (`- item`). Sem estruturas aninhadas.

## 6. Nomenclatura

- Arquivo: `<TIPO>-<AAAAMMDD>-<slug-kebab-case>.md` (ex.: `DEC-20261106-haiku-padrao-sonnet-final.md`).
- ID: `CTX-<TIPO>-<AAAAMMDD>-<slug>` — igual ao nome do arquivo com prefixo `CTX-`.
- A data é a de **origem** do conhecimento quando conhecida (ex.: data do briefing); senão, a de criação do registro.
- IDs são estáveis: mover um arquivo não muda o ID. Nunca reutilize um ID.
- Evite nomes genéricos (`notas.md`, `novo.md`, `final2.md`).

## 7. Tags

Tags em `kebab-case`, normalizadas em `_meta/taxonomy.yaml`. Antes de criar uma tag nova, procure uma canônica equivalente. Ao criar, adicione-a à taxonomia.

## 8. Protocolo de recuperação

1. **Entender a tarefa:** objetivo, entidades, branches e tags prováveis, tipo de conhecimento, restrições.
2. **L0:** ler `MAP.md` e `STATE.md`.
3. **L1:** ler o `_index.md` das branches relevantes.
4. **L2 — busca direcionada:**
   ```bash
   rg -l "tags:.*guardrails" Context/
   rg "status: open" Context/ -l
   rg "type: decision" Context/branches/software -l
   rg -i "acentua" Context/
   ```
   (ou `grep -rn`; ou filtrar `_meta/catalog.jsonl`). São exemplos, não dependências.
5. **Relações:** siga `related`, `depends_on`, `source_ids`, supersession — 1 salto por padrão.
6. **Prioridade:** correspondência direta → branch → tags → status ativo → relações → mais recente → maior confiança → melhor fonte → validade.
7. Registros `superseded`, `deprecated` ou `archived` não são o estado atual: siga o `superseded_by`.

## 9. Protocolo "salvar contexto"

Acionado por intenção equivalente a: *salvar contexto, salve o contexto, save context, persistir contexto, atualizar contexto, atualizar memória do projeto, criar checkpoint, checkpoint da sessão.*

Não é um resumo da conversa. É uma reconstrução destilada da sessão.

```text
SESSÃO → INSPECIONAR MUDANÇAS (git status/diff/log) → ANALISAR → DESTILAR
→ CLASSIFICAR → DEDUPLICAR → RELACIONAR → CRIAR/ATUALIZAR REGISTROS
→ CHECKPOINT → STATE → _index das branches → MAP (se preciso)
→ catálogo (python Context/_meta/catalogo.py) → changelog (se estrutural)
→ AVALIAR AGENTS.md → VALIDAR
```

1. **Inspecionar:** use `git status`, `git diff` e `git log` para saber o que mudou de verdade; não confie só na lembrança da conversa.
2. **Analisar:** objetivo, tarefas, problemas, causas, tentativas que falharam, soluções validadas, decisões e motivos, arquivos afetados, testes e resultados, fatos, hipóteses, perguntas abertas/respondidas, riscos, pendências, próximos passos, informação que ficou obsoleta, regras operacionais novas.
3. **Filtrar:** *uma sessão nova precisaria disso para continuar, evitar retrabalho ou decidir melhor?* Se não, descarte (cumprimentos, tentativas triviais, raciocínio redundante, texto literal).
4. **Classificar** pelo tipo canônico (seção 4).
5. **Deduplicar:** procure por assunto, tags, títulos e IDs antes de criar. Prefira atualizar um registro existente (e `updated_at`) a criar duplicata. Se o conhecimento mudou de verdade, use supersession.
6. **Relacionar** por ID (`related`, `depends_on`, `source_ids`).
7. **Checkpoint** em `checkpoints/CP-AAAAMMDD-HHMM-<slug>.md` (modelo em `_meta/templates/checkpoint.md`). O checkpoint não substitui os registros: conhecimento durável vai para o tipo correto.
8. **STATE:** reescreva para refletir só o presente e aponte o checkpoint mais recente.
9. **Índices e MAP:** atualize o `_index.md` das branches tocadas; o MAP só se surgir rota ou branch nova.
10. **Catálogo:** `python Context/_meta/catalogo.py` (reconstrói e valida IDs, relações, campos obrigatórios e padrões de segredo). Corrija o que ele apontar.
11. **AGENTS.md:** surgiu uma regra durável sobre *como* trabalhar (ex.: "sempre rodar X antes de Y")? Atualize `AGENTS.md` fora do bloco gerenciado. Conhecimento sobre *o que* (arquitetura, decisão, fato) fica em `Context/`.

### Conhecimento negativo

Falhas viram memória quando alguém poderia repeti-las. Registre (em `notes/`, tag `licao-aprendida`): abordagem, condição, resultado, causa conhecida e quando valeria tentar de novo. Formato: *Problema → Investigação → Solução validada → Evitar.*

## 10. Outros comandos semânticos

| Intenção | O que fazer |
|---|---|
| `carregar contexto` | Ler MAP, STATE e as branches relevantes antes de continuar |
| `buscar contexto <assunto>` | Buscar por tags, títulos, conteúdo, IDs e relações; devolver primeiro os mais relevantes |
| `status do contexto` | Resumir STATE, último checkpoint, branches, perguntas críticas e bloqueios |
| `auditar contexto` | Rodar a auditoria da seção 14 |

São intenções, não comandos com parser.

## 11. Ciclo de vida, supersession e arquivo

- **Pergunta respondida:** `status: answered`, `resolved_by: <ID>` e seção `## Resposta` com a evidência. Não apague a pergunta.
- **Informação que deixou de valer:** no antigo, `status: superseded` e `superseded_by: <novo>`; no novo, `supersedes: <antigo>`. Não apague.
- **Fora do conjunto ativo:** mova para `archive/` mantendo o ID e `status: archived`.
- **Temporalidade:** preços, custos, versões de modelos, especificações de plataforma e dados de estoque mudam. Use `valid_from`, `valid_until`, `revisit_at`.
- **Planos:** `candidate`, `planned`, `in-progress`, `completed`, `cancelled`. Possibilidade não é compromisso (use `future/`).

## 12. Conflitos

Não escolha em silêncio. Compare data, status, escopo, origem, confiança, decisões posteriores e validade.
Se a ambiguidade continuar, crie ou atualize uma `question` e registre o conflito no corpo dos registros envolvidos.
Regra do projeto: dado confirmado em `dados/negocio.json` prevalece sobre o briefing (mais antigo) para dados operacionais do negócio.

## 13. Fontes

Informação externa ou documental importante ganha um registro em `sources/` (o que é, onde está, data, confiabilidade) e é citada por `source_ids`. Não converta informação temporal externa em fato absoluto sem data e origem.

## 14. Auditoria (`auditar contexto`)

Rode `python Context/_meta/catalogo.py` e depois verifique manualmente:
IDs duplicados ou inexistentes · tags sinônimas · registros contraditórios · status errado (pergunta respondida ainda `open`) · `superseded` apresentado como ativo · links quebrados · branches redundantes ou grandes demais · `_index.md` inchado · registro com vários assuntos (dividir) · MAP desatualizado · STATE com histórico · catálogo divergente · regras duplicadas entre AGENTS.md e CLAUDE.md · segredos persistidos.
Corrija preservando o histórico relevante; registre mudanças estruturais em `_meta/changelog.md`.

## 15. Adicionar uma branch

1. Confirme que é uma área de conhecimento relativamente independente (não crie branch para um único registro).
2. Crie `branches/<nome-kebab>/_index.md` (propósito, escopo, estado, conceitos, registros importantes, decisões ativas, perguntas, riscos, relações, rotas).
3. Adicione a rota em `MAP.md`, a branch em `_meta/taxonomy.yaml` e uma linha em `_meta/changelog.md`.

## 16. Reconstruir o catálogo

```bash
python Context/_meta/catalogo.py          # reconstrói _meta/catalog.jsonl e valida
python Context/_meta/catalogo.py --check  # só valida (não grava); sai com código 1 se houver erro
```

Só usa a biblioteca padrão do Python. Se houver divergência entre catálogo e registros, os registros vencem: reconstrua.

## 17. Segurança

Nunca grave valores de senha, token, chave de API, chave privada, cookie, segredo, credencial ou código de recuperação.
Permitido: "a integração usa `OPENROUTER_API_KEY` (no `.env`, fora do git)". Proibido: o valor da chave.
Encontrou um segredo em `Context/`? Não replique, remova/mascare e avise o usuário para rotacioná-lo.
Dados pessoais de clientes ou vendedores (nome, IMEI, telefone pessoal) também não entram aqui.
