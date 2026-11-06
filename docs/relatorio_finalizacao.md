# Relatório de finalização do MVP

**Data:** 06/11/2026 · **Modelo de texto:** `anthropic/claude-sonnet-5.5` · **Imagem:** `google/gemini-3.1-flash-image` (Nano Banana 2)

## Resumo

Todos os modos do agente foram testados com a API real. O MVP atende aos 8 critérios de aceite do briefing (seção 17); em um deles há uma ressalva, que é registrar o desempenho, só possível depois de publicar.

Os testes reais encontraram **1 bug de código** e **3 falsos positivos** nas verificações automáticas. Todos foram corrigidos e ganharam teste de regressão (26 testes passando). **Nenhum falso negativo** apareceu: o texto com 8 violações propositais teve todas detectadas.

**Gasto:** cerca de **US$ 0,91** nesta finalização e US$ 1,30 no total do projeto. O saldo ficou em torno de US$ 3,70.

## Testes reais

| # | Teste | Resultado | Custo | Tempo | Evidência |
|---|---|---|---:|---:|---|
| 1 | `planejar --semanas 1` | ✅ 4 itens, frentes coerentes com os pilares. Sem estoque, trocou o slot de venda por captação/relacionamento | US$ 0,07 | 31 s | `saida/calendarios/C-20261106-01.md` |
| 2 | `lote --limite 3` | ⚠️→✅ Quebrava ao exibir o resultado (bug); corrigido. Agora retoma de onde parou | US$ 0,30 | 45 s + 111 s | ATR-003, EDU-004, CAP-005 |
| 3 | Reel (do lote) | ✅ 6 cenas, 28 s, narração e texto na tela, ressalva honesta ("um sinal isolado não prova golpe") | (no lote) | — | `P-20261106-ATR-003` |
| 4 | `adaptar` carrossel → Stories | ✅ 9:16 em 1080×1920, 7 quadros com duração, CTA de relacionamento, afirmações preservadas | US$ 0,11 | 42 s | `P-20261106-EDU-006` |
| 5 | `revisar` texto com 8 violações | ✅ Veredito `bloqueado`; 7 achados automáticos, o resto (mistura de frentes, tom) pelo modelo; reescreveu como peça de captação | US$ 0,07 | 28 s | `saida/revisoes/R-20261106-091941.md` |
| 6 | `revisar` peça CAP-002 | ✅ `ajustes_necessarios`, só itens de severidade média/baixa, todos pertinentes | US$ 0,16 | 82 s | `saida/revisoes/R-20261106-092110.md` |
| 7 | `analisar` CSV de exemplo | ✅ Declarou a base insuficiente (n=1 por grupo), percebeu os IDs fictícios, não inventou meta | US$ 0,09 | 40 s | `saida/analises/A-20261106-01.md` |
| 8 | Venda com unidade do estoque (pasta isolada) | ✅ Bateria 88% igual ao estoque, preço e garantia `[PENDENTE]`, sem prompt de imagem, `imagem` recusada, marca de uso **mostrada** | US$ 0,11 | 45 s | pasta temporária (fora do projeto) |
| — | Testes anteriores | ✅ Carrossel (Haiku), anúncio (Sonnet), imagens em 4:5 padrão e 2K | US$ 0,29 | — | EDU-001, CAP-002 |

## Critérios de aceite do MVP (briefing, seção 17)

| # | Critério | Status | Evidência |
|---|---|---|---|
| 1 | Pauta por objetivos sem misturar venda e captação | ✅ | Calendário C-20261106-01: frente sempre coerente com o pilar |
| 2 | Reel, carrossel, imagem estática e anúncio com todos os campos | ✅ | ATR-003 (reel), EDU-004 (carrossel), CAP-005 (imagem), CAP-002 (anúncio), EDU-006 (stories) |
| 3 | Variações significativas | ✅ | Cada variação muda um eixo declarado (gancho ou ângulo) e traz uma hipótese |
| 4 | Voz e padrão visual consistentes | ✅ | Tom direto e sem gritos; 4:5/9:16 corretos; paleta e logo sempre `[PENDENTE]` |
| 5 | Nunca inventar estoque, preço ou prova social | ✅ | Venda: preço e garantia pendentes, bateria exata; nenhum depoimento inventado |
| 6 | Alertar o que exige verificação humana | ✅ | Checklists de 8 a 14 itens por peça, mais as verificações automáticas |
| 7 | Exportar e registrar versões | ✅ | JSON + Markdown por versão (v1, v2), registro com histórico de status |
| 8 | Métrica por peça | ⚠️ | Toda peça tem métrica e critério. A medição real depende de publicar e exportar os dados para o `analisar` |

## Qualidade editorial

- **Aderência ao briefing:**
  - as peças usam as séries ("iPhone sem cilada"), os públicos e os CTAs por etapa;
  - em captação, sempre aparece "a proposta depende da avaliação" e nenhuma cotação é prometida;
  - a frase "não pedimos senha" aparece só na forma negativa.
- **Honestidade:** o agente marca as próprias especificações técnicas para conferência humana e prefere `[PENDENTE]` a qualquer suposição. A peça de venda escolheu **mostrar** a marca de uso.
- **Haiku × Sonnet:**
  - O Haiku (US$ 0,004 por peça) produz peças corretas e seguras, mas mais genéricas.
  - O Sonnet (US$ 0,10 a 0,12 por peça) traz justificativas melhores, checklists mais ricos e revisões mais finas.
  - **Recomendação:** Haiku para rascunhos e exploração; Sonnet para a peça final e para a revisão.
- **Imagens:** realistas, sem logo e sem avarias, com a proporção respeitada. O tamanho padrão (928×1152) fica abaixo do feed; com `--tamanho 2K` sai em 1856×2304.

## Verificações automáticas

| Tipo | Caso | Correção |
|---|---|---|
| Falso positivo | "pular a **verificação** do iCloud" lido como contornar bloqueio | Verbos ambíguos só disparam quando o objeto é o próprio bloqueio |
| Falso positivo | "em **nenhum** momento pedimos senha" lido como coleta de dados | "nenhum", "momento algum" etc. entraram como negação |
| Falso positivo | "página **oficial** da Apple" lido como vínculo | A regra só vale para alegações sobre a loja e respeita negação ("não somos autorizada") |
| Falso positivo | "tela sem **riscos**" (arranhões) lido como promessa absoluta | Condição física é removida antes da regra |
| Falso negativo | Nenhum encontrado | — |

**Bug de código:** o `lote` quebrava ao exibir o resultado (o `except ... as e` sobrescrevia o atalho de escape). Corrigido. O `lote` também passou a pular os itens já gerados, para não cobrar de novo.

Lição: as regras por palavra-chave precisam de contexto, porque o português tem muita ambiguidade (riscos, oficial, pular). Cada falso positivo novo deve virar teste em `tests/test_guardrails.py`.

## Riscos e limitações restantes

1. **Dados do negócio vazios:** toda peça sai com `[PENDENTE]`. Nada é publicável sem preencher o `dados/negocio.json`.
2. **Medidas de plataforma** (zonas seguras, tamanhos) são referência; precisam ser conferidas na documentação da Meta.
3. **Imagem sem texto:** título, passos e logo ainda são aplicados à mão.
4. **Especificações de iPhone** citadas pelo modelo precisam de conferência humana (o checklist já pede).
5. **Custo do Sonnet:** cerca de US$ 0,10 por peça e US$ 0,16 por revisão. Um mês de 16 peças, com revisão e imagem, sai por uns US$ 5 a 6.
6. **Regras por palavra-chave:** novos falsos positivos vão aparecer. O fluxo para tratar já existe (corrigir → teste → `reverificar`).

## Próximos passos priorizados

1. **(Negócio)** Preencher `negocio.json`: nome, cidade, WhatsApp, formato da avaliação, critérios de compra; depois rodar `reverificar`.
2. **(Negócio)** Cadastrar o estoque real com fotos e preço aprovado.
3. **(Código)** Menu interativo no terminal, em andamento.
4. **(Código, opcional)** Compor a arte final: título, passos e logo aplicados sobre a imagem gerada.
5. **(Código, opcional)** Importar métricas da Meta para o `analisar`.
