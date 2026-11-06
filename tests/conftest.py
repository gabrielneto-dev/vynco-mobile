"""Fixtures: agente completo com cliente falso (sem chamadas reais à API)."""

from __future__ import annotations

import base64
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from agente.armazenamento import Registro
from agente.config import RAIZ, carregar_config
from agente.contexto import carregar_contexto
from agente.llm import ClienteOpenRouter
from agente.modos import Agente
from agente.schemas import Calendario, Peca, Revisao

def _png_valido() -> str:
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 80), (180, 180, 185)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


PNG_1PX = _png_valido()


def peca_exemplo(**alteracoes) -> dict:
    base = {
        "titulo_interno": "3 sinais de alerta ao comprar iPhone usado",
        "objetivo": "Gerar descoberta e compartilhamentos entre compradores de usados.",
        "objecao_ou_interesse": "Medo de cair em golpe ao comprar usado.",
        "ideia_central": "Três verificações rápidas evitam a maioria dos problemas.",
        "justificativa_estrategica": "Checklists tendem a gerar salvamentos (hipótese a testar).",
        "ganchos": ["Gancho 1", "Gancho 2", "Gancho 3"],
        "copy_principal": "Antes de pagar, confira bateria, Face ID e se o iCloud foi desvinculado pelo dono.",
        "legenda": "Salve para consultar antes de comprar. Nunca pedimos sua senha do Apple ID.",
        "cta": "Envie para quem vai comprar um iPhone",
        "roteiro": [{"ordem": 1, "visual": "Mão segurando iPhone", "texto_tela": "3 sinais de alerta", "narracao": "Antes de pagar...", "duracao_s": 3}],
        "direcao_arte": {
            "proporcao": "9:16",
            "dimensoes_px": "1080x1920",
            "elementos_visuais": ["iPhone 14 em mesa clara"],
            "hierarquia": "título → dica → CTA",
            "paleta": "branco, grafite, destaque provisório",
            "tipografia": "sem serifa",
            "zonas_seguras": "texto fora do topo 14% e base 35%",
            "fonte_imagens": "imagem gerada: conceito de inspeção",
        },
        "prompt_imagem": "A hand holding an iPhone 14 over a clean light-gray desk, soft studio lighting.",
        "variacoes": [
            {"nome": "V1", "eixo": "gancho", "hipotese": "Pergunta gera mais retenção", "gancho": "Você confere isso?", "texto": "..."},
            {"nome": "V2", "eixo": "angulo", "hipotese": "Ângulo de prejuízo", "gancho": "O erro que custa caro", "texto": "..."},
        ],
        "afirmacoes": [{"texto": "Checklists geram salvamentos", "status": "hipotese_criativa", "fonte": None}],
        "checklist_validacao": [{"campo": "Medidas de zona segura", "motivo": "Conferir especificação vigente", "status": "informacao_pendente"}],
        "metrica": {"principal": "compartilhamentos", "apoio": ["salvamentos", "alcance"], "criterio_avaliacao": "comparar com a linha de base de Reels de atração"},
    }
    base.update(alteracoes)
    return base


def calendario_exemplo() -> dict:
    itens = []
    pilares = [("atracao", "marca", "reel", "A", "descoberta"), ("educacao", "marca", "carrossel", "A", "confianca"),
               ("captacao", "captacao", "imagem", "C", "intencao"), ("conversao", "venda", "imagem", "A", "intencao")]
    for n, (p, f, fmt, pub, et) in enumerate(pilares, 1):
        itens.append({"data": f"2026-11-{9 + n:02d}", "slot": n, "pilar": p, "frente": f, "formato": fmt, "publico": pub, "etapa": et,
                      "tema": f"Tema {n}", "gancho_sugerido": "g", "cta": "c", "justificativa": "j"})
    return {"periodo": "2026-11-10 a 2026-11-16", "premissas": ["p"], "itens": itens, "stories_sugeridos": ["s"],
            "observacao_estoque": "vazio", "pendencias": ["nome da loja"]}


class ClienteFalso(ClienteOpenRouter):
    def __init__(self, cfg, respostas: dict | None = None):
        super().__init__(cfg)
        self.respostas = respostas or {}
        self.chamadas: list[tuple[str, str]] = []

    def gerar_estruturado(self, sistema, usuario, modelo_saida, *, modelo=None, tentativas=2):
        self.chamadas.append((sistema, usuario))
        padrao = {Peca: peca_exemplo(), Calendario: calendario_exemplo(),
                  Revisao: {"veredito": "pronto_para_aprovacao_humana", "resumo": "ok", "problemas": [], "pontos_fortes": [], "campos_para_validar": []}}
        dados = self.respostas.get(modelo_saida, padrao.get(modelo_saida))
        return modelo_saida.model_validate(dados)

    def post(self, payload):
        self.chamadas.append(("post", json.dumps(payload)[:200]))
        return {"choices": [{"message": {"content": "ok", "images": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PNG_1PX}"}}]}}]}


@pytest.fixture
def agente(tmp_path: Path) -> Agente:
    dados = tmp_path / "dados"
    shutil.copytree(RAIZ / "dados", dados)
    cfg = replace(carregar_config(), dir_dados=dados, dir_saida=tmp_path / "saida", api_key="teste")
    return Agente(cfg, ClienteFalso(cfg), carregar_contexto(cfg), Registro(cfg.dir_saida))


def com_estoque(agente: Agente, **campos) -> Agente:
    unidade = {"id": "U1", "modelo": "iPhone 14", "armazenamento_gb": 128, "saude_bateria_pct": 88, "disponivel": True, **campos}
    (agente.cfg.dir_dados / "estoque.json").write_text(json.dumps([unidade]), encoding="utf-8")
    agente.ctx = carregar_contexto(agente.cfg)
    return agente
