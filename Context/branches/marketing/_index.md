# Branch: marketing

**Propósito:** a estratégia de comunicação que o agente executa.
**Escopo:** posicionamento, públicos, pilares, formatos, séries, tom de voz, campanhas pagas, métricas de negócio e hipóteses de conteúdo.

## Onde está o conteúdo operacional
O agente lê **`contexto/*.md`** em toda chamada — é ali que a estratégia vive de fato:
`BRIEFING.md` (resumo), `BRAND.md` (voz), `AUDIENCES.md` (públicos), `CONTENT_PILLARS.md`, `COPY_GUIDELINES.md`, `CREATIVE_STANDARDS.md` (medidas e imagem), `QUALITY_RULES.md`.
A origem é `docs/briefing_estrategico_v1.md`. Esta branch guarda só decisões, hipóteses e riscos — não copia aqueles arquivos.

## Estado atual
- Estratégia definida; **nada publicado ainda** → nenhuma hipótese testada, sem linha de base.
- Cadência de teste: 4 posts de feed/Reels por semana + Stories em dias com conteúdo real.
- Com estoque vazio, slots de venda viram educação/captação.

## Conceitos centrais
Posicionamento: equilíbrio entre preço competitivo, confiança e autoridade. Tom: especialista acessível, direto, sem gritos nem promessas absolutas.
Campanhas: **A** captação ("Solicitar avaliação"), **B** venda de estoque ("Consultar disponibilidade"), **C** marca (opcional).

## Registros
| ID | Tipo | Status |
|---|---|---|
| `CTX-DEC-20261105-cinco-pilares-editoriais` | decision | active |
| `CTX-DEC-20261105-sem-metas-sem-linha-de-base` | decision | active |
| `CTX-ASM-20261105-distribuicao-dos-pilares` | assumption | active (low) |
| `CTX-ASM-20261105-personas-iniciais` | assumption | active (low) |
| `CTX-ASM-20261105-hipoteses-de-conteudo` | assumption | active (low) |
| `CTX-RSK-20261106-medidas-de-plataforma-mudam` | risk | active |

## Decisões ativas (globais)
`CTX-DEC-20261105-separar-venda-e-captacao`, `CTX-DEC-20261105-aprovacao-humana-sem-publicacao-automatica`, `CTX-DEC-20261106-comportamento-via-contexto-runtime`.

## Relações
- `negocio`: dados confirmados que podem ser comunicados.
- `guardrails`: limites éticos garantidos por código.
- `software`: importação de métricas (`CTX-QUE-20261106-colunas-exportacao-meta`).
