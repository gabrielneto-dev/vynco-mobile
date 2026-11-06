# Agente de Conteúdo — Loja de iPhones

MVP do agente descrito em [docs/briefing_estrategico_v1.md](docs/briefing_estrategico_v1.md), feito em **Python** com:

- **OpenRouter** para texto (planejar, criar, adaptar, revisar, analisar). Padrão: `anthropic/claude-haiku-5.5` (≈ R$ 0,02 por peça); `anthropic/claude-sonnet-5.5` para peças finais (≈ R$ 0,39).
- **Nano Banana** (Gemini Image) via OpenRouter para imagens conceituais. Padrão: `google/gemini-3.1-flash-image` (Nano Banana 2); `google/gemini-3-pro-image` para o Pro.

Uma única chave do OpenRouter cobre texto e imagem.

## Instalação

Requer Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (no Git Bash: source .venv/Scripts/activate)
pip install -e ".[dev]"
copy .env.example .env          # e preencha OPENROUTER_API_KEY
python -m agente pendencias     # confere configuração, dados pendentes e estoque
```

## Como está organizado

```
contexto/        Engenharia de contexto (o agente lê tudo em toda chamada)
  BRIEFING.md, BRAND.md, AUDIENCES.md, CONTENT_PILLARS.md,
  COPY_GUIDELINES.md, CREATIVE_STANDARDS.md, QUALITY_RULES.md
dados/
  negocio.json   Dados comerciais CONFIRMADOS (null = pendente → vira [PENDENTE: ...])
  estoque.json   Unidades reais e verificadas (vazio = nenhuma oferta de venda)
agente/          Código
  schemas.py     Brief de entrada e saídas estruturadas (Pydantic)
  llm.py         Cliente OpenRouter com saída JSON validada e nova tentativa automática
  imagem.py      Nano Banana via OpenRouter (aspect_ratio, tamanho, imagens de referência)
  guardrails.py  Regras determinísticas de QUALITY_RULES (rodam sempre, sem depender do LLM)
  modos.py       Os 5 modos + lote + imagens
  armazenamento.py  Registro de peças, versões, status, publicações
  cli.py         Comandos
saida/           Tudo que é gerado (JSON + Markdown + imagens), fora do git
```

Para mudar o comportamento do agente, edite os arquivos em `contexto/` — não o código. Arquivos `.md` novos colocados ali também entram no contexto.

## Menu interativo

```bash
python -m agente
```

Abre o menu no terminal (setas + Enter, Ctrl+C volta). Ele mostra o estado do projeto (modelos, pendências, estoque, peças por status, custo da sessão), cobre todas as funções abaixo, mostra o **custo estimado antes de cada chamada paga** e deixa trocar entre Sonnet (peças finais) e Haiku (rascunhos). Em "Peças e aprovação" você abre, aprova, registra publicação e arquiva peças.

## Comandos (uso direto, sem menu)

```bash
# Planejar 4 semanas com 4 posts/semana
python -m agente planejar --semanas 4 --inicio 2026-11-09

# Gerar todas as peças do calendário (itens de venda são pulados sem estoque)
python -m agente lote C-20261106-01

# Criar uma peça
python -m agente criar --pilar educacao --formato carrossel --objetivo "Checklist de bateria, Face ID, tela e iCloud"
python -m agente criar --pilar captacao --formato anuncio --objetivo "Como funciona a avaliação do seu iPhone 13/14/15" --imagem
python -m agente criar --pilar conversao --formato imagem --produto U1 --objetivo "iPhone 14 disponível: ficha real"

# Adaptar uma peça para outro formato
python -m agente adaptar P-20261106-EDU-001 --formato stories

# Revisar (peça registrada, arquivo ou texto)
python -m agente revisar P-20261106-EDU-001
python -m agente revisar "iPhone 14 com o menor preço da cidade, última unidade!"

# Reaplicar as verificações sem custo de API (após mudar regras, negocio.json ou estoque)
python -m agente reverificar P-20261106-EDU-001

# Imagens com Nano Banana (padrão ~928x1152 em 4:5; use --tamanho 2K para passar de 1080x1350)
python -m agente imagem P-20261106-EDU-001 --quantidade 2
python -m agente imagem P-20261106-EDU-001 --tamanho 2K
python -m agente imagem P-20261106-EDU-001 --modelo google/gemini-3-pro-image --tamanho 2K
python -m agente imagem-livre "Minimal flat lay of an iPhone 15 on light gray, soft light" --proporcao 9:16

# Fluxo de aprovação e publicação (manual)
python -m agente listar --status revisao
python -m agente status P-20261106-EDU-001 aprovado --responsavel "Gabriel"
python -m agente publicado P-20261106-EDU-001 --data 2026-11-10 --url https://instagram.com/p/... --responsavel "Gabriel"

# Analisar resultados reais (CSV exportado/planilha)
python -m agente analisar exemplos/resultados_exemplo.csv
```

## Garantias embutidas (do briefing)

| Regra do briefing | Como é garantida |
|---|---|
| Não inventar estoque/preço/condição | Só `dados/` entra como fato; preço sem `preco_aprovado_brl` **bloqueia**; bateria diferente do estoque **bloqueia** |
| Oferta concreta exige dados | `criar --pilar conversao` exige `--produto` (ou `--generico`, sem preço nem disponibilidade) |
| Não anunciar indisponível | Produto com `disponivel: false` é recusado |
| Imagem gerada não representa unidade vendida | Peça com produto do estoque não recebe prompt e `imagem` é recusada |
| Promessas absolutas, vínculo Apple, IMEI, pedir senha, contornar iCloud | Bloqueio automático |
| Urgência, prova social, garantia/parcelamento não definidos, `[PENDENTE]` | Exigem revisão humana |
| Venda e captação separadas | Frente derivada do pilar + alerta de mistura de CTAs |
| Aprovação humana | `status aprovado` exige `--responsavel` e zero bloqueios; `publicado` só após aprovado |
| Sem publicação automática | O agente não tem integração de publicação; `publicado` só registra o que foi feito à mão |
| Metas sem dados | Análise usa agregados calculados pelo código e declara quando a base é insuficiente |

## Testes

```bash
pytest
```

Os testes usam um cliente falso: não gastam créditos nem precisam de chave.

## Próximos passos sugeridos (Etapa 3 do roadmap)

- Preencher `dados/negocio.json` e cadastrar estoque real.
- Interface web simples (ex.: Streamlit) sobre os mesmos módulos.
- Integração com WhatsApp/CRM e importação automática de métricas da Meta.
