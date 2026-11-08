#!/usr/bin/env bash
# Abre o menu do Agente de Conteúdo no Linux (equivalente ao agente.bat).
# Uso: ./agente.sh            -> menu interativo
#      ./agente.sh pendencias -> qualquer comando da CLI (os argumentos passam direto)

# Sempre roda a partir da pasta do projeto (onde este script está), de qualquer lugar.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
export PYTHONUTF8=1

if [ ! -x ".venv/bin/python" ]; then
    echo
    echo " Ambiente .venv não encontrado nesta pasta."
    echo " Crie com:  python3 -m venv .venv && .venv/bin/python -m pip install -e \".[dev]\""
    echo " Passo a passo: docs/execucao_linux_mint.md"
    echo
    read -rp " Enter para fechar..." _
    exit 1
fi

.venv/bin/python -m agente "$@"
codigo=$?

# Se der erro, mantém a janela aberta para ler a mensagem (útil quando aberto por atalho).
if [ "$codigo" -ne 0 ] && [ -t 0 ]; then
    echo
    read -rp " Enter para fechar..." _
fi
exit "$codigo"
