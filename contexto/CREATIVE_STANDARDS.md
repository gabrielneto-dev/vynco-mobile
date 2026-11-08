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

O `prompt_imagem` descreve **só a cena**. O código acrescenta sozinho, em todo prompt: a descrição física exata do modelo de iPhone citado (número e posição das câmeras, notch ou Dynamic Island), o enquadramento casado com o layout da arte (título no topo, marca e CTA na base), a cor de fundo da paleta, o padrão fotográfico e as restrições. **Não repita esses blocos** e não dê porcentagens de espaço livre: instruções duplicadas ou conflitantes pioram o resultado.

Escreva em **inglês**, em 2 a 4 frases corridas (descrição de cena, não lista de palavras-chave):

1. **Um aparelho, um modelo, nome exato.** Escreva "iPhone 15", "iPhone 13" etc. (o código usa o nome para garantir as câmeras certas). Peça sobre vários modelos (ex.: captação de 13/14/15) mostra **um** aparelho do modelo base, nunca um Pro, salvo se o Pro for o assunto. Não descreva câmeras nem detalhes técnicos: o código faz isso.
2. **Ângulo e pose concretos.** Ex.: "lying face down on the surface, seen from directly above", "standing at a slight three-quarter angle, back facing the camera", "held in one hand, only the hand visible". Escolha a pose que conta a ideia da peça (avaliação → aparelho sobre a mesa de inspeção; bateria → tela acesa só com brilho, sem números).
3. **Superfície e ambiente.** Material e cor do apoio (ex.: "matte light-gray paper sweep", "pale oak desk"), poucos objetos de apoio e só se servirem à ideia (ex.: "a folded microfiber cloth").
4. **Luz e clima.** Ex.: "soft window light from the left, calm and trustworthy mood".
5. **Sem texto, ícones ou interface na imagem.** Títulos, setas, selos, números e ícones entram na edição (arte final), onde ficam legíveis e consistentes entre peças. Tela acesa só com cor/brilho genérico, nunca com interface legível.

Exemplo bom: `An iPhone 14 in midnight lies face down on a matte light-gray paper sweep, seen from directly above, next to a neatly folded microfiber cloth. Soft window light from the left creates a gentle shadow; calm, trustworthy mood.`

Proibido em prompts: avarias inexistentes, logotipos de terceiros como elemento de marca, selos de "oficial/autorizado", rostos de pessoas reais, imitação de criativos de concorrentes.

## Texto na tela (`texto_tela` das cenas/slides)

A arte final é montada a partir desse campo, então a forma dele vira o layout:

- **Lista** (critérios, checklist): itens separados por ` | ` → cada item ganha um ✓. Ex.: `iPhone 13, 14 ou 15 | Bateria acima de 80% | Sem bloqueio`.
- **Etapas** (processo, passo a passo): itens separados por ` > ` → círculos numerados ligados. Ex.: `Conversa no WhatsApp > Avaliação presencial > Pix`.
- **Frase única**: até ~12 palavras, sem separadores.
- **Última cena com CTA**: a frase do CTA seguida do WhatsApp no formato `(DD) 9XXXX-XXXX`; o número vira o botão de destaque.
- Itens curtos (até ~5 palavras cada), no máximo 4 por cena. Não repita o título da capa.

## Direção de arte — campos obrigatórios por peça

- Proporção e dimensões em pixels.
- Elementos visuais e hierarquia (o que aparece, em que ordem de leitura).
- Texto na tela (curto) e posição respeitando zonas seguras.
- Paleta (provisória) e tipografia.
- Fonte das imagens: foto real (qual) ou imagem gerada (qual prompt).
