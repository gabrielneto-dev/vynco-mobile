# Como rodar e usar o agente no Linux Mint

Guia para usar o Agente de Conteúdo da Vynco Mobile no **Linux Mint 22.3 (Cinnamon)**. No Windows, o equivalente é o `agente.bat` com o `README.md`.

> **Testado nesta máquina em 07/11/2026:** Linux Mint 22.3, Python 3.14.8 (asdf), 70 de 70 testes passando, menu aberto no terminal, comando `pendencias` funcionando.
> Ainda **não** testado aqui: chamadas pagas, que precisam da chave no `.env`. O arquivo do atalho (seção 2) passou no `desktop-file-validate`, mas não foi instalado no menu do Mint.

---

## Resumo rápido

Se você já tem tudo instalado, só precisa de um comando:

```bash
cd ~/projects/vynco-mobile && ./agente.sh
```

Primeira vez nesta máquina? Siga as seções 1 a 3 (cerca de 5 minutos).

---

## 1. Instalar (uma vez só)

### 1.1 Escolha o Python

O projeto precisa de Python 3.10 ou mais novo. Nesta máquina há dois:

| Python | Como chamar | Situação |
|---|---|---|
| **3.14 (asdf)** | `python3` (é o padrão do seu terminal) | ✅ Pronto. Use este. |
| 3.12 (do sistema) | `/usr/bin/python3` | ⚠️ Antes, instale o pacote que cria ambientes: `sudo apt install python3-venv` |

Os comandos abaixo usam o `python3` do asdf.

### 1.2 Criar o ambiente e instalar

```bash
cd ~/projects/vynco-mobile
```

```bash
python3 -m venv .venv
```

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

- O `.venv` é uma pasta só do projeto, com as bibliotecas dele. Ela fica fora do git.
- **Não precisa "ativar" o ambiente:** o `agente.sh` já usa o Python certo de dentro do `.venv`.
- Se quiser ativar mesmo assim (para digitar `python` e `pytest` direto): `source .venv/bin/activate`. Para sair: `deactivate`.

### 1.3 Configurar a chave do OpenRouter

```bash
cp .env.example .env
```

```bash
xed .env
```

O `xed` é o editor de texto do Mint. Preencha a linha `OPENROUTER_API_KEY=` com a sua chave (a mesma usada no Windows) e salve.

- O `.env` **nunca** vai para o git.
- Não mande esse arquivo para ninguém.
- As outras linhas (modelos, cotação do dólar) já vêm com os padrões.

### 1.4 Conferir

```bash
./agente.sh pendencias
```

Mostra os dados do negócio (✓ preenchido, ⏳ pendente), o estoque e a configuração.
Se aparecer `Chave OpenRouter: ✗ FALTANDO no .env`, revise o passo 1.3.

---

## 2. Abrir o menu

### Pelo terminal (sempre funciona)

```bash
cd ~/projects/vynco-mobile && ./agente.sh
```

O `agente.sh` funciona de qualquer pasta. Se o comando der erro, a janela fica aberta para você ler a mensagem.

### Pelo menu do Mint (opcional)

Para ter o ícone **"Agente Vynco"** no menu Iniciar do Mint, rode este comando uma vez:

```bash
cat > ~/.local/share/applications/agente-vynco.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Agente Vynco
Comment=Agente de Conteúdo da Vynco Mobile
Exec=$HOME/projects/vynco-mobile/agente.sh
Terminal=true
Icon=utilities-terminal
Categories=Office;
EOF
```

- Depois disso, procure "Agente Vynco" no menu: ele abre um terminal com o agente.
- Para pôr na área de trabalho: clique com o botão direito no item do menu → "Adicionar à área de trabalho".
- Se o projeto mudar de pasta, apague o atalho e crie de novo:

  ```bash
  rm ~/.local/share/applications/agente-vynco.desktop
  ```

---

## 3. Como o menu funciona

| Tecla | O que faz |
|---|---|
| ↑ ↓ e Enter | Escolher uma opção |
| Ctrl+C | Voltar uma tela; na tela inicial, sair |
| Digitar e Enter | Responder perguntas de texto |

No topo aparece o painel de estado: modelo de texto e de imagem, chave do OpenRouter, dados do negócio, estoque, peças por status, último backup e **quanto você já gastou na sessão**.

**Toda opção que custa dinheiro mostra o custo estimado em reais antes**, e você confirma ou desiste.

---

## 4. Do zero à peça publicada

### O que o agente faz e o que ele não faz

O agente **planeja e escreve** as peças: legenda, roteiro, slides, ganchos, variações e checklist do que conferir. Ele também **monta a arte** em PNG.

O agente **não publica nada**. Quem aprova e posta no Instagram/Facebook é você. Depois, você registra no agente o que postou.

Duas regras que ele sempre segue:
- **Venda** (vender iPhone) e **captação** (comprar usado) nunca se misturam numa peça.
- **Nada é inventado:** dado que não está cadastrado vira `[PENDENTE: …]`. Peça com pendência não vira arte final.

### O caminho, opção por opção

| Passo | Opção do menu | Para quê | Custo |
|---|---|---|---|
| 1 | 🏪 Dados do negócio | Completar o que falta: garantia, devolução, Instagram, Facebook, paleta, logo | grátis |
| 2 | 📱 Estoque de aparelhos | Cadastrar cada unidade real, com fotos e preço aprovado. Só é necessário para peças de **venda** | grátis |
| 3 | 📅 Planejar calendário | Montar a pauta das semanas (ex.: 4 semanas, 4 posts por semana) | centavos com Haiku; ≈ R$ 0,40 por semana planejada com Sonnet (medido antes da redução de custo) — o menu mostra a estimativa |
| 4 | 📦 Gerar peças de um calendário | Escrever todas as peças da pauta. Se parar no meio, retoma de onde parou sem cobrar de novo | ≈ R$ 0,02 por peça (Haiku) |
| 4b | 📝 Criar peça | Alternativa: uma peça avulsa, com assistente passo a passo | ≈ R$ 0,02 (Haiku) / 0,39 (Sonnet) |
| 5 | 🎨 Gerar imagem de uma peça | Fundo conceitual por IA (opcional; **nunca** para unidade à venda, que usa foto real) | ≈ R$ 0,37 |
| 6 | 🧩 Montar arte final | PNG pronto, no tamanho certo, com título, CTA e marca | grátis |
| 7 | 📋 Peças e aprovação | Ler o checklist, **aprovar**, postar você mesmo, **registrar a publicação** com o link | grátis |
| 8 | 📥 Importar métricas da Meta | Ler a exportação do Instagram/Gerenciador de Anúncios e ligar os números às peças | grátis (com análise: pago) |
| 9 | 💾 Backup | Cópia de peças, artes, fotos e dados numa pasta (ver seção 6) | grátis |

### Dicas de uso

- **Haiku ou Sonnet** (opção 🧠 Modelo de texto): use o Haiku (padrão, barato) para rascunhos e para gerar a pauta inteira. Troque para o Sonnet na versão final de uma peça importante e para a 🔍 Revisão.
- **🔄 Reverificar regras** é grátis. Rode depois de cadastrar dados novos no negócio ou no estoque: as peças antigas são conferidas de novo.
- **🔀 Adaptar** transforma uma peça pronta em outro formato (ex.: carrossel → Stories) sem começar do zero.
- **Peça bloqueada?** O checklist diz o motivo: preço sem aprovação, promessa absoluta, `[PENDENTE]` etc. Corrija o dado ou gere de novo.
- **Arte só para conferir:** use o modo rascunho. Ele monta mesmo com `[PENDENTE]`, mas com uma tarja (não é para postar).
- **Unidade vendida:** no 📱 Estoque, marque como vendida. Ela sai das ofertas e o agente oferece arquivar as peças dela.

---

## 5. Onde ficam as coisas

| Pasta | O que tem | No git? |
|---|---|---|
| `saida/pecas/<ID>/` | Cada peça: `v1.md` (para ler), JSON, `imagens/`, `arte/…/01.png` (para postar) | não |
| `saida/calendarios/`, `revisoes/`, `analises/`, `metricas/` | Pautas, revisões, análises, métricas importadas | não |
| `dados/negocio.json`, `dados/estoque.json` | O que você cadastrou pelo menu | sim |
| `dados/fotos/` | Fotos reais das unidades | não |
| `contexto/*.md` | As regras que o agente segue (marca, públicos, tom). Para mudar o jeito como ele escreve, edite aqui | sim |

O menu abre arquivos e pastas direto no visualizador do Mint (Nemo, visualizador de imagens, editor).
Pelo terminal, o equivalente é:

```bash
xdg-open saida
```

---

## 6. Peças do Windows e backup no Linux

### Trazer o que já foi feito no Windows

O git só traz código e `dados/*.json`. As **peças, artes e fotos** ficaram no Windows e na pasta de backup (`AgenteConteudo-backup`, no OneDrive).
O backup tem duas pastas, `saida/` e `dados/`. Para continuar no Mint, copie as duas para dentro da pasta do projeto:

```bash
cp -rn /caminho/do/AgenteConteudo-backup/saida /caminho/do/AgenteConteudo-backup/dados ~/projects/vynco-mobile/
```

O `-n` não sobrescreve nada que já exista aqui. Troque `/caminho/do/` pelo local onde o backup está (pendrive, download do OneDrive pelo navegador etc.).

### Backup no Mint

O Mint não tem o OneDrive instalado, então o menu não sugere uma pasta sozinho. Em 💾 Backup, escolha informar o caminho e digite uma pasta, por exemplo:
- um pendrive ou HD externo, como `/media/neto/NOME-DO-DISCO/AgenteConteudo-backup`;
- qualquer pasta que um programa de sincronização mantenha na nuvem.

A pasta fica gravada no `.env` (`BACKUP_DIR`) e o backup roda sozinho ao sair do menu.
Ele só copia o que mudou e nunca apaga nada no destino. O `.env` com a chave não vai para o backup.

> **Cuidado ao usar nas duas máquinas:** o `dados/negocio.json` e o `dados/estoque.json` vão pelo git; as peças e as fotos, não.
> Ao trocar de máquina, faça `git pull` e copie a pasta `saida/` do backup para não ficar com duas versões diferentes.

---

## 7. Comandos diretos (sem menu)

Tudo do menu também existe como comando. Basta pôr o comando depois do `./agente.sh`:

```bash
./agente.sh listar --status revisao
```

```bash
./agente.sh reverificar P-20261106-EDU-001
```

```bash
./agente.sh arte P-20261106-EDU-001 --gancho 2
```

```bash
./agente.sh planejar --semanas 4 --inicio 2026-11-09
```

- Lista completa: `README.md`, seção "Comandos", ou `./agente.sh --help`.
- `planejar`, `lote`, `criar`, `adaptar`, `revisar`, `analisar`, `imagem` e `imagem-livre` **gastam crédito**.
- `listar`, `status`, `reverificar`, `arte`, `pendencias` e `importar-metricas` são grátis.

---

## 8. Atualizar o projeto

Quando houver mudanças no GitHub (feitas aqui, no Windows ou pelo Claude):

```bash
cd ~/projects/vynco-mobile && git pull
```

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

O segundo comando só é necessário se o `pyproject.toml` mudou; rodar sem necessidade não faz mal.

Para conferir se está tudo certo (grátis, sem internet, não usa a chave):

```bash
.venv/bin/python -m pytest -q
```

---

## 9. Problemas comuns

| Mensagem ou sintoma | Causa | Solução |
|---|---|---|
| `ensurepip is not available` ou `No module named 'ensurepip'` ao criar o `.venv` | Você usou o Python do sistema sem o `python3-venv` | Instale com `sudo apt install python3-venv`, ou use o `python3` do asdf |
| `Ambiente .venv não encontrado nesta pasta` | O `.venv` não foi criado (ou foi criado em outra pasta) | Refaça a seção 1.2 dentro da pasta do projeto |
| `bash: ./agente.sh: Permissão negada` | O arquivo perdeu a permissão de execução | `chmod +x agente.sh` |
| O `.venv` parou de funcionar depois de atualizar o Python do asdf | O `.venv` aponta para a versão antiga | `rm -rf .venv` e refaça a seção 1.2 |
| `Chave OpenRouter: ✗ FALTANDO` | `.env` ausente ou chave vazia | Seção 1.3 |
| Erro 401 ao gerar | Chave errada ou revogada | Confira a chave no painel do OpenRouter |
| Erro 402 ao gerar | Saldo de crédito acabou | Recarregue no OpenRouter. O lote retoma de onde parou |
| Emojis viram quadradinhos | Falta a fonte de emoji | `sudo apt install fonts-noto-color-emoji` (nesta máquina já está instalada) |
| O menu não responde às setas | Foi aberto fora de um terminal de verdade | Abra pelo terminal do Mint ou pelo atalho (`Terminal=true`) |
| Arte com letras feias | Faltam as fontes DejaVu | `sudo apt install fonts-dejavu-core` (já vem no Mint) |

---

## 10. Windows × Linux

| | Windows | Linux Mint |
|---|---|---|
| Abrir o menu | duplo clique em `agente.bat` | `./agente.sh` ou o atalho "Agente Vynco" |
| Python do ambiente | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Ativar o ambiente | `.venv\Scripts\activate` | `source .venv/bin/activate` |
| Copiar o `.env` | `copy .env.example .env` | `cp .env.example .env` |
| Backup sugerido | OneDrive (automático) | você informa a pasta |
| Fonte da arte | Segoe UI / Arial | DejaVu Sans |
| Abrir arquivos pelo menu | Explorador | Nemo / `xdg-open` |
