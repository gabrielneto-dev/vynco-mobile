# Agente de Conteúdo — Loja de iPhones

MVP do agente descrito em [docs/briefing_estrategico_v1.md](docs/briefing_estrategico_v1.md), feito em **Python** com:

- **OpenRouter** para texto (planejar, criar, adaptar, revisar, analisar). Padrão: `anthropic/claude-haiku-5.5` (≈ R$ 0,02 por peça); `anthropic/claude-sonnet-5.5` para peças finais (≈ R$ 0,39).
- **Nano Banana** (Gemini Image) via OpenRouter para imagens conceituais. Padrão: `google/gemini-3.1-flash-image` (Nano Banana 2); `google/gemini-3-pro-image` para o Pro.

Uma única chave do OpenRouter cobre texto e imagem.

## Instalação

Requer Python 3.10+. No **Linux Mint**, siga [docs/execucao_linux_mint.md](docs/execucao_linux_mint.md) (instalação, `agente.sh`, atalho e uso passo a passo).

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
  cadastro.py    Dados do negócio e estoque (usado pelo menu)
  arte.py        Arte final (orquestra os estilos editorial/nativo/oferta em arte_*.py; Pillow, local)
  design.py      Tokens do padrão visual · validacao_design.py: confere a arte contra o padrão
  metricas.py    Importação das métricas exportadas da Meta
  backup.py      Backup incremental para pasta sincronizada
  menu.py        Menu interativo · visual.py: exibição compartilhada
  cli.py         Comandos
saida/           Tudo que é gerado (JSON + Markdown + imagens + artes), fora do git
  pecas/<ID>/v1.md, imagens/, arte/<versão-gancho-fundo>/01.png…
  metricas/      CSVs normalizados das importações
```

Para mudar o comportamento do agente, edite os arquivos em `contexto/` — não o código. Arquivos `.md` novos colocados ali também entram no contexto.

## Menu interativo

```bash
python -m agente
```

Ou dê duplo clique em `agente.bat`. Abre o menu no terminal (setas + Enter, Ctrl+C volta). Ele mostra o estado do projeto (modelos, dados do negócio, estoque, peças por status, último backup, custo da sessão), cobre todas as funções abaixo, mostra o **custo estimado em reais antes de cada chamada paga** e deixa trocar entre Haiku (padrão) e Sonnet (peças finais).

### Do zero à peça publicada

1. **🏪 Dados do negócio** — nome, cidade, WhatsApp, critérios de compra, paleta e logo (sem editar JSON).
2. **📱 Estoque** — cadastre as unidades com fotos reais (só necessário para peças de venda).
3. **📅 Planejar** e **📦 Gerar peças** (≈ R$ 0,02 por peça com Haiku).
4. **🎨 Gerar imagem** (opcional, ≈ R$ 0,37) e **🧩 Montar arte final** — PNGs prontos, nas medidas certas, sem Canva (grátis).
5. **📋 Peças e aprovação** — confira o checklist, aprove, publique **você mesmo** e registre a publicação (com o link do post).
6. **📥 Importar métricas da Meta** — liga os números às peças e roda a análise.
7. **💾 Backup** — configure uma vez (OneDrive); depois roda sozinho ao sair.

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

# Arte final pronta para postar (local, sem custo) — padrão visual em docs/padrao_visual.md
python -m agente arte P-20261106-EDU-001 --gancho 2
python -m agente arte P-20261106-EDU-001 --estilo nativo   # auto | editorial | nativo | oferta
python -m agente arte P-20261106-EDU-001 --rascunho      # gera mesmo com [PENDENTE], com tarja
python -m agente validar-arte P-20261106-EDU-001          # confere a última arte contra o padrão (grátis)

# Fluxo de aprovação e publicação (manual)
python -m agente listar --status revisao
python -m agente status P-20261106-EDU-001 aprovado --responsavel "Gabriel"
python -m agente publicado P-20261106-EDU-001 --data 2026-11-10 --url https://instagram.com/p/... --responsavel "Gabriel"

# Métricas: importar a exportação da Meta (liga às peças) e analisar
python -m agente importar-metricas insights_instagram.csv --analisar
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
| `[PENDENTE]` não vai ao ar | A arte final é recusada se algum texto visível tiver pendência (rascunho só com tarja) |
| Unidade vendida | "Marcar como vendido" tira das ofertas e oferece arquivar as peças dela |
| Transparência de imagem | Fundo gerado por IA recebe o selo "Imagem ilustrativa" na arte final |

## Testes

```bash
pytest
```

Os testes usam um cliente falso: não gastam créditos nem precisam de chave.

## Próximos passos sugeridos

- Calibrar a importação de métricas com uma exportação real da Meta (os nomes de colunas variam por idioma/versão).
- Interface web simples (ex.: Streamlit) sobre os mesmos módulos.
- Integração com WhatsApp/CRM para contar conversas qualificadas automaticamente.
