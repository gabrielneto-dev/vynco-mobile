# AGENTS.md — Agente de Conteúdo da Vynco Mobile

Instruções operacionais compartilhadas para qualquer agente de IA (Claude Code, Codex etc.) que trabalhe neste repositório.
O que o projeto **sabe** fica em `Context/`; aqui fica **como trabalhar**.

## Regras permanentes do projeto

- **Idioma:** código, documentação, mensagens do menu e commits em português do Brasil.
- **`contexto/` ≠ `Context/`.**
  - `contexto/*.md` é o contexto de *runtime* do agente de conteúdo: **todo** `.md` ali entra em **toda** chamada ao LLM (custa tokens e muda as peças). Para mudar o comportamento do agente, edite esses arquivos, não o código.
  - `Context/` é a memória do projeto para agentes de desenvolvimento. Nunca coloque material de `Context/` dentro de `contexto/`, nem o contrário.
- **Dados do negócio:** `dados/negocio.json` e `dados/estoque.json` só recebem informação confirmada pelo dono. Nunca preencha com suposições; campo desconhecido fica `null`.
- **Chamadas pagas:** comandos que chamam o OpenRouter (`planejar`, `lote`, `criar`, `adaptar`, `revisar`, `analisar`, `imagem`, `imagem-livre`) gastam crédito real. Peça confirmação antes de rodá-los. `reverificar`, `arte`, `listar`, `status`, `pendencias`, `importar-metricas` (sem `--analisar`) e o `pytest` são gratuitos.
- **Testes:** rode `pytest` antes de commitar. Os testes usam cliente falso e dados próprios (não dependem do `.env` nem do `negocio.json` real, nem da pasta de backup real); mantenha assim.
- **Guardrails:** todo falso positivo ou negativo encontrado nas verificações automáticas vira teste de regressão em `tests/test_guardrails.py` antes da correção.
- **Nunca versionar:** `.env`, `saida/`, `dados/fotos/` (já no `.gitignore`).
- **Publicação:** o agente não publica nada. Não implemente publicação automática, campanhas ou movimentação financeira sem autorização explícita do dono (ver `Context/global/decisions/`).

<!-- CONTEXT-ENGINEERING:START -->

# Sistema de contexto do projeto

Este projeto usa `Context/` como memória persistente e sistema de conhecimento.

## Descoberta de contexto

Para toda tarefa não trivial:

1. Leia `Context/MAP.md`.
2. Leia `Context/STATE.md`.
3. Decida quais branches de contexto são relevantes.
4. Leia apenas os `_index.md` dessas branches.
5. Abra registros atômicos só quando forem necessários.
6. Siga `related`, `depends_on`, `source_ids`, `supersedes` e `superseded_by` só quando afetarem de fato a tarefa (1 salto por padrão).
7. Não carregue `Context/` inteiro de forma recursiva.

Use carregamento progressivo (L0 → L1 → L2 → L3).

## Fontes de verdade

- `AGENTS.md` — instruções operacionais permanentes.
- `Context/MAP.md` — roteamento e navegação.
- `Context/STATE.md` — estado atual do projeto.
- `Context/core/**` — fundamentos estáveis.
- `Context/branches/**` — conhecimento por domínio.
- `Context/global/**` — decisões, perguntas, hipóteses, riscos e planos transversais.
- `Context/checkpoints/**` — checkpoints destilados de sessões/marcos.
- `Context/sources/**` — proveniência e evidências.
- `Context/_meta/**` — configuração, taxonomia, catálogo e manutenção do contexto.
- O código, `dados/` e `contexto/` continuam sendo a verdade sobre o comportamento e os dados reais; `Context/` aponta para eles em vez de copiá-los.

## Política de escrita

Ler contexto é automático em trabalho não trivial. Gravar contexto é controlado: não documente cada mensagem.

Execute o protocolo "salvar contexto" quando o usuário expressar intenção equivalente a:

- `salvar contexto` / `salve o contexto` / `save context`
- `persistir contexto` / `atualizar contexto`
- `atualizar memória do projeto`
- `criar checkpoint` / `checkpoint da sessão`

Ao ser acionado, siga `Context/README.md`. Não copie a conversa; persista conhecimento destilado e durável.
Depois de gravar, rode `python Context/_meta/catalogo.py` para reconstruir o catálogo e validar IDs e relações.

## Segurança

Nunca persista em `Context/` senhas, tokens, chaves de API (incluindo `OPENROUTER_API_KEY`), chaves privadas, cookies ou valores de credenciais.
Nomes de variáveis de ambiente e locais de cofres de segredo são permitidos.

## Manutenção

Se surgir uma regra operacional durável para o projeto inteiro, avalie se ela pertence a este `AGENTS.md`.
Não coloque estado transitório nem conhecimento detalhado aqui.

<!-- CONTEXT-ENGINEERING:END -->
