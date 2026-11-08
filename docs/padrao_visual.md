# Padrão visual da Vynco Mobile (v1, nov/2026)

Como as artes do agente devem parecer, de onde isso veio e como é conferido.
As regras objetivas estão em código (`agente/design.py`) e são checadas automaticamente por `python -m agente validar-arte <ID>`. Este documento explica o porquê.

---

## 1. O que a pesquisa mostrou

Pesquisa feita em 08/11/2026 na Biblioteca de Anúncios da Meta e no Instagram (perfis abertos com login, só visualização).

### Biblioteca de Anúncios (Brasil, ativos, só imagem, ordenados por impressões)

| Busca | Resultados | O que domina |
|---|---|---|
| "iphone seminovo" | ~63 | Foto **real** do aparelho na mão ou em vitrine; fundo natural (madeira, planta, tijolo, balcão); **quase nenhum texto na imagem**. Ficha (modelo, GB, bateria %, garantia) vai na legenda. |
| "troca iphone usado" | ~69 | Mesmo padrão. Caixa do aparelho ao lado como prova de procedência. Stories com etiquetas nativas (pílula branca, figurinha de localização). |
| "venda seu iphone" | ~26 | Anúncios de pessoas físicas e lojas pequenas; fotos de celular, sem tratamento. |
| "iplace" | ~7 | Catálogo: aparelho recortado em fundo branco (anúncio dinâmico). |

- O anúncio **mais longevo** encontrado (ativo desde mar/2025, sinal público de que dá resultado) é um carrossel de fotos reais de vitrine com legenda curta.
- Criativos "desenhados" são minoria. O melhor exemplo é fundo escuro, **nome do modelo enorme**, selo de GB, **selo de preço** e uma fileira de 3 ícones de benefício.

### Instagram

| Perfil | Porte | Padrão visual | O que aproveitar |
|---|---|---|---|
| @iplace (maior Apple Premium Partner da AL) | 1 mi | Editorial premium: foto de estilo de vida ou fundo preto/branco, título curto em frase normal (2–3 linhas), texto de apoio pequeno, logo pequeno no topo à esquerda, **uma** cor de destaque, numeral gigante na cor de destaque ("3 motivos…"). Slides internos: pergunta na cor de destaque no topo, imagem emoldurada, corpo curto. | Template **editorial**. |
| @canaltech | 577 mil | Reels com pessoa falando + **faixa de título na cor da marca**, sempre igual → reconhecível no feed. | Consistência: o mesmo tratamento de título em tudo. |
| @iphones.sorocaba (loja de seminovos) | 28 mil | Pessoas da equipe, texto nativo do Instagram sobre foto/vídeo, post em formato "tweet" do próprio perfil, promoções pontuais muito carregadas. | Rosto e bastidor reais (exige material real); etiquetas nativas. |
| @tgf.store.oficial (Rio Preto) | 13 mil | Pessoa na loja + legenda em caixa-alta com palavra destacada em laranja; destaques com prova social ("Cliente 2500"). | Palavra destacada na cor de destaque. Prova social só com dado real. |
| @casadoiphonejales (concorrente local) | 539 | Fotos de celular contra parede cinza + logo neon roxo. Sem padrão de texto. | Espaço para se diferenciar com consistência e conteúdo educativo. |
| Busca "iphone seminovo" (orgânico) | — | Três arquétipos: Reels com pessoa segurando o aparelho e tarja de legenda; **tabelas de preço poluídas** (azul/preto neon, dezenas de preços); foto real com etiqueta branca curta ("Testes básicos antes de comprar um iPhone usado"). | Etiqueta branca curta sobre foto real. A tabela poluída é **antipadrão**. |
| @macmagazine | 58 mil | Só foto, sem texto. | Não serve de referência para arte. |

### Boas práticas das fontes de mercado

São blogs e ferramentas de mercado, não documentação oficial da Meta, então são hipóteses a testar:
- **Gancho:** decidido em 1–3 s; desenhe para leitura instantânea, não para leitura atenta.
- **Texto:** título até ~7 palavras; no máximo ~3 benefícios; um ponto focal.
- **Regra dos 20%:** acabou, mas texto demais ainda derruba o desempenho.
- **Polimento:** excessivo pode ativar o "pular anúncio". Criativo com cara nativa costuma render mais, **desde que a mensagem fique clara**.
- **Zonas seguras de anúncio em Reels/Stories** (diagrama da Meta, 2026): 14% no topo, 35% na base, 6% nas laterais. Para Stories orgânico as fontes divergem (20% a 35% na base). Confira no Gerenciador de Anúncios antes de impulsionar.

Fontes: [Billo — Meta safe zones 2026](https://billo.app/blog/meta-ads-safe-zones), [AdManage — Reels safe zone](https://admanage.ai/instagram-reels-safe-zone), [Segwise — anatomia do anúncio estático](https://segwise.ai/blog/anatomy-high-converting-static-ad), [Segwise — anúncios "sem graça" que vencem](https://segwise.ai/blog/why-boring-ads-beat-polished-ads.md), [AdLibrary — padrões de anúncios](https://adlibrary.com/posts/how-to-clone-high-performing-ads), [Coupler — boas práticas Instagram Ads 2026](https://blog.coupler.io/instagram-ads-best-practises/).

---

## 2. Direção: híbrida

| Estilo | Quando | Por quê |
|---|---|---|
| **Nativo** | Stories, anúncios (captação e atração) | É o que domina e dura na Biblioteca de Anúncios: parece post, não propaganda. |
| **Editorial** | Carrossel educativo, capa de feed orgânico | Constrói marca e confiança como a iPlace; diferencia da concorrência local. |
| **Oferta** | Venda de unidade real do estoque | Ficha clara (modelo, GB, bateria, garantia, preço) é o que o comprador procura. Só com foto real e dados confirmados. |

O estilo sai automático do formato e da frente da peça (`design.estilo_padrao`), e dá para trocar no menu ou com `--estilo`.

---

## 3. Fundamentos (todos os estilos)

- **Tipografia:** Inter (OFL, em `agente/fontes/`). Título em ExtraBold, destaques em Bold, corpo em Regular. Frase normal, nunca tudo em caixa-alta.
- **Cor:** fundo neutro, texto grafite e **uma** cor de destaque (paleta provisória `#F4F4F6 / #1F2328 / #2563EB`, azul escolhido por ter contraste AA com texto branco até o dono definir a dele). O destaque só vai no CTA, no numeral ou na palavra-chave, um por área.
- **Texto:**
  - título até 7 palavras;
  - até 4 itens por slide, até 5 palavras por item;
  - área de texto até 30% da arte (fora o fundo de etiquetas);
  - contraste mínimo de 4,5:1 (corpo) e 3:1 (título grande).
- **Tamanho mínimo** (arte de 1080 px de largura): título 56 px, corpo 30 px, rodapé 22 px. O título precisa continuar legível com a arte reduzida ao tamanho do feed no celular (~375 px).
- **Zonas seguras** (em `design.ZONAS`):

  | Formato | Topo | Base | Laterais |
  |---|---|---|---|
  | Feed | 80 px | 80 px | 80 px |
  | Stories | 14% | 20% | 6% |
  | Reels | 14% | 35% | 6%, mais a coluna de botões à direita |

- **Ponto focal:** um aparelho ou uma ideia por arte. O texto nunca cobre o aparelho.
- **Transparência:** fundo gerado por IA leva o selo "Imagem ilustrativa"; venda de unidade real só com foto real.

---

## 4. Templates

### 4.1 Editorial (base iPlace)

**Capa**
- Logo/nome pequeno no topo à esquerda.
- Título curto na maior faixa livre da foto (ou no centro, em fundo liso), com barra de destaque acima.
- Número do título (ex.: "3 erros") na cor de destaque.
- CTA em pílula na base à esquerda (se houver) e selo de imagem ilustrativa à direita.

**Slides internos** (carrossel)
- Numeral do slide na cor de destaque.
- Conteúdo em lista com ✓ (` | `), etapas numeradas (` > `) ou frase curta.
- Rodapé com marca e "n/total ›".

**Último slide:** frase do CTA + botão "WhatsApp (DD) 9XXXX-XXXX".

### 4.2 Nativo (base Biblioteca de Anúncios)

- **Foto:** cobre tudo (aparelho na mão, cenário real, luz natural). Gerada por IA só para captação e atração, nunca para unidade à venda.
- **Título:** em **etiqueta** no estilo do Instagram, centralizada: uma pílula branca por linha, texto preto em Bold, no máximo 3 linhas.
- **Localização:** etiqueta pequena com alfinete e a cidade/região cadastrada (`cidade_regiao_atendimento`).
- **CTA:** pílula na cor de destaque, perto da base da zona segura.
- **Marca:** discreta (nome pequeno em etiqueta no topo à esquerda).
- **Stories seguintes:** a mesma foto desfocada e escurecida, com etiquetas (lista com ✓, etapas numeradas ou frase), para a sequência parecer uma coisa só.

### 4.3 Oferta (base criativos de vitrine)

- Foto real da unidade cobrindo tudo, com degradê escuro na base.
- **Ficha:** nome do modelo grande, selo de GB, fileira de até 3 selos (bateria %, garantia, condição), cada um **só** se o dado estiver confirmado em `estoque.json`/`negocio.json`.
- **Preço:** selo só com `preco_aprovado_brl`; sem ele, não há selo de preço.

---

## 5. Antipadrões (não fazer)

- Tabela de preços poluída, fundo neon, dezenas de itens.
- Tudo em caixa-alta, emoji em excesso, "MELHOR PREÇO DA REGIÃO", urgência falsa (proibidos também pelo `QUALITY_RULES.md`).
- Texto cobrindo o aparelho; mais de 4 itens num slide; duas cores de destaque competindo.
- Imagem gerada representando unidade à venda; logotipo da Apple como elemento de marca; selo de "oficial/autorizado".
- Prova social ("+2.500 clientes") sem número real cadastrado.

---

## 6. Como é conferido

`python -m agente validar-arte <ID>` (grátis) roda as regras abaixo na última arte da peça e grava `validacao.json` e `validacao.md` na pasta da arte. Isso também roda sozinho ao montar a arte.

| # | Regra | Falha quando |
|---|---|---|
| 1 | Tamanho | A arte não tem o tamanho do formato. |
| 2 | Zona segura | Texto, logo ou CTA fora da área segura. |
| 3 | Contraste | Abaixo de 4,5:1 (corpo) ou 3:1 (título). |
| 4 | Fonte mínima | Título < 56 px, corpo < 30 px, rodapé < 22 px. |
| 5 | Miniatura | Título ilegível reduzido à largura do celular. |
| 6 | Quantidade de texto | Título > 7 palavras, > 4 itens, item > 5 palavras, texto > 30% da área (avisos). |
| 7 | Hierarquia | Título menor que 1,6× o corpo. |
| 8 | Aparelho coberto | Texto em cima do objeto principal da foto. |
| 9 | Marca e transparência | Sem assinatura, ou fundo IA sem selo. |
| 10 | Coerência de estilo | Estilo diferente do esperado (aviso); venda com fundo IA (falha). |

**Resultados:**
- **Falha:** não segue o padrão. A arte é gerada mesmo assim (a decisão é humana), mas deve ser corrigida antes de publicar.
- **Aviso:** pede olho humano.

**Revisão humana**, além das regras automáticas:
- Dá para entender a mensagem em 2 s, no celular?
- O aparelho é do modelo certo, sem defeito inventado?
- A arte parece da mesma marca das anteriores?

---

## 7. Validação do padrão v1 (08/11/2026)

Teste real: 4 peças novas (Haiku) + 4 imagens 2K (Nano Banana 2), cerca de R$ 2,30. Também foi refeita a peça antiga `P-20261108-CAP-001`. Prancha: [`docs/referencias/prancha_validacao_v1.png`](referencias/prancha_validacao_v1.png).

| Peça | Formato · estilo | Automático | Revisão visual |
|---|---|---|---|
| P-20261108-CAP-002 | Stories de captação · nativo | 0 falhas, 0 avisos | Cara de post: foto na mão, etiquetas, localização, WhatsApp em destaque no último story. Etiqueta do título encosta no topo do aparelho (cenário com textura: a regra 8 não mede). |
| P-20261108-EDU-003 | Carrossel educativo · editorial | 0 falhas, 3 avisos | Capa limpa no padrão iPlace; listas e etapas legíveis. Avisos: itens com 6–7 palavras (texto da peça, não do layout). |
| P-20261108-CAP-004 | Anúncio de captação · nativo | 0 falhas, 0 avisos | Título em uma etiqueta, localização, CTA em destaque; foto realista com o modelo certo. |
| P-20261108-ATR-005 | Imagem de atração · editorial | 0 falhas, 0 avisos | Título forte no topo, aparelho inteiro, CTA e selo na base. |
| P-20261108-CAP-001 (antiga) | Stories · nativo | 1 falha | Gancho de 12 palavras não cabe acima do aparelho e o invade. **Correto:** o padrão pede até 7 palavras. |

### O que a validação corrigiu no próprio sistema

- **Zona segura:** marca e numeral do carrossel encostavam na margem.
- **Contraste:** azul provisório `#2F6BFF` tinha 4,5:1 com branco, no limite; trocado por `#2563EB`, com 5,2:1.
- **Aparelho coberto:** a localização (nativo) caía sobre o aparelho; agora desce para perto do CTA.
- **Título mínimo:** o título encolhia até 46 px para caber; agora o mínimo é 56 px.
- **Último slide:** a lista do último slide virava checklist; agora vira fechamento.
- **Ganchos:** passaram a ser pedidos com até 7 palavras.

### Limites conhecidos

- **Regra 8 (aparelho coberto):** só mede foto de fundo liso (estúdio). Em cenário com textura, fica para a revisão humana.
- **Itens com mais de 5 palavras:** dependem do texto que o modelo escreve. O `CREATIVE_STANDARDS.md` pede itens curtos, e o validador avisa.
