# CREATIVE_STANDARDS — Padrões visuais e de geração de imagem

> Especificações de plataforma mudam. Trate as medidas abaixo como referência e **sinalize no checklist** que devem ser conferidas na documentação vigente da Meta antes de publicar.

## Dimensões de referência

| Formato | Proporção | Pixels | Observação |
|---|---|---|---|
| Feed (imagem/carrossel) | 4:5 | 1080 × 1350 | Padrão preferido para feed |
| Feed quadrado | 1:1 | 1080 × 1080 | Alternativa para anúncios |
| Reels | 9:16 (vertical) | 1080 × 1920 | Manter texto fora do topo (~14%) e da base (~35%), onde ficam interface e legenda |
| Stories | 9:16 (vertical) | 1080 × 1920 | Manter ~250 px livres no topo e na base |
| Anúncio | 4:5, 1:1 ou 9:16 | conforme posicionamento | Entregar uma versão por posicionamento |

**Não confundir 9:16 (vertical) com 16:9 (horizontal).** Nada neste projeto usa 16:9 por padrão.

## Linguagem visual (sistema neutro provisório)

- Limpa, moderna, tecnológica, alto contraste, hierarquia clara (título → informação → CTA).
- Fundos neutros: branco, cinza claro, grafite. Uma cor de destaque provisória.
- Tipografia sem serifa, títulos de até ~6 palavras, corpo legível no celular.
- Muito espaço em branco; um ponto focal por peça.

## Fotos reais vs. imagens geradas

| Situação | O que usar |
|---|---|
| Peça de unidade do estoque (frente `venda` com aparelho específico) | **Somente fotos reais da unidade.** Imagem gerada é proibida. |
| Conteúdo educacional, captação, campanhas gerais, conceitos | Imagem gerada permitida, desde que não represente falsamente um produto à venda |
| Bastidores, avaliação, depoimentos | Somente material real e autorizado |

## Diretrizes para prompts de imagem (Nano Banana / Gemini Image)

Escreva o prompt em **inglês** (melhor aderência do modelo), como uma descrição de cena, com:

1. **Assunto e ação:** o que aparece e o que está acontecendo.
2. **Produto realista:** cite o modelo e suas características físicas reais (ex.: iPhone 15 — câmera dupla em diagonal, Dynamic Island; iPhone 13 — câmera dupla em diagonal, notch). Proporções, câmeras e acabamentos devem ser realistas.
3. **Composição:** enquadramento, ângulo, espaço negativo reservado para texto (indique onde).
4. **Iluminação e estilo:** ex. "soft studio lighting, clean minimal tech aesthetic, neutral light-gray background".
5. **Proporção:** informe a proporção da peça (o código também envia o `aspect_ratio`).
6. **Texto na imagem:** prefira **sem texto** (o texto é aplicado na edição). Se necessário, no máximo um título curto entre aspas.
7. **Restrições explícitas:** "no Apple logo emphasis, no brand logos, no visible damage, no cracked screens, no people's faces unless specified, no watermark".

Proibido em prompts: avarias inexistentes, logotipos de terceiros como elemento de marca, selos de "oficial/autorizado", rostos de pessoas reais, imitação de criativos de concorrentes.

## Direção de arte — campos obrigatórios por peça

- Proporção e dimensões em pixels.
- Elementos visuais e hierarquia (o que aparece, em que ordem de leitura).
- Texto na tela (curto) e posição respeitando zonas seguras.
- Paleta (provisória) e tipografia.
- Fonte das imagens: foto real (qual) ou imagem gerada (qual prompt).
