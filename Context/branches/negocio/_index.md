# Branch: negocio

**Propósito:** a operação real da Vynco Mobile e o que o dono já confirmou ou ainda precisa decidir.
**Escopo:** dados comerciais, estoque, funis de venda e captação, pendências de negócio. Estratégia de conteúdo fica em `marketing`.

## Estado atual
- Loja em início de operação, Jales (SP) e região, sem loja física, avaliação de usados presencial.
- Dados essenciais preenchidos em `dados/negocio.json` (06/11/2026); garantia, devolução, redes sociais, paleta e logo pendentes.
- Estoque vazio → nenhuma oferta concreta possível.

## Fontes de verdade
`dados/negocio.json` e `dados/estoque.json` (só dados confirmados; `null` = pendente). Os registros abaixo resumem e apontam.

## Funis (briefing §11)
- **Venda:** conteúdo → mensagem → modelo e orçamento → opções reais → evidências → negociação.
- **Captação:** conteúdo → mensagem → dados mínimos do aparelho → elegibilidade → fotos/documentos de forma segura → avaliação presencial → proposta condicionada → Pix → estoque. Nunca pedir senha/código da Apple ID.

## Registros
| ID | Tipo | Status |
|---|---|---|
| `CTX-FCT-20261106-dados-confirmados-vynco` | fact | active |
| `CTX-FCT-20261106-estoque-vazio` | fact | active |
| `CTX-QUE-20261106-garantia-e-devolucao` | question | open |
| `CTX-QUE-20261106-identidade-visual` | question | open |
| `CTX-QUE-20261106-contas-redes-sociais` | question | open |
| `CTX-QUE-20261105-orcamento-e-capacidade-de-anuncios` | question | open |

## Decisões ativas (globais)
`CTX-DEC-20261105-separar-venda-e-captacao`, `CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica`.

## Relações
- `marketing`: o que comunicar depende do que está confirmado aqui.
- `guardrails`: o código bloqueia qualquer dado comercial que não venha de `dados/`.
