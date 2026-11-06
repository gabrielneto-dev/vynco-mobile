"""Registro local de peças, versões, status, imagens e calendários (arquivos JSON em saida/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agente.guardrails import Achado, tem_bloqueio
from agente.schemas import Brief, Calendario, Peca, Pilar, StatusPeca

SIGLA_PILAR = {
    Pilar.atracao: "ATR",
    Pilar.educacao: "EDU",
    Pilar.relacionamento: "REL",
    Pilar.conversao: "VEN",
    Pilar.captacao: "CAP",
}

_ORDEM = [StatusPeca.ideia, StatusPeca.em_criacao, StatusPeca.revisao, StatusPeca.aprovado, StatusPeca.publicado, StatusPeca.analisado]


class ErroRegistro(RuntimeError):
    pass


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Registro:
    def __init__(self, dir_saida: Path):
        self.dir = dir_saida
        self.arquivo = dir_saida / "registro.json"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.dados = self._ler()

    # ------------------------------------------------------------------ persistência
    def _ler(self) -> dict:
        if self.arquivo.exists():
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        return {"pecas": {}, "calendarios": {}, "revisoes": {}, "seq": {}}

    def _gravar(self) -> None:
        tmp = self.arquivo.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.dados, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.arquivo)

    def _proximo(self, chave: str) -> int:
        self.dados["seq"][chave] = self.dados["seq"].get(chave, 0) + 1
        return self.dados["seq"][chave]

    # ------------------------------------------------------------------ peças
    def dir_peca(self, peca_id: str) -> Path:
        return self.dir / "pecas" / peca_id

    def novo_id(self, pilar: Pilar) -> str:
        dia = datetime.now().strftime("%Y%m%d")
        return f"P-{dia}-{SIGLA_PILAR[pilar]}-{self._proximo('P' + dia):03d}"

    def proxima_versao(self, peca_id: str) -> int:
        entrada = self.dados["pecas"].get(peca_id)
        return (entrada["versao_atual"] + 1) if entrada else 1

    def salvar_peca(
        self,
        peca_id: str,
        peca: Peca,
        brief: Brief,
        achados: list[Achado],
        *,
        modelo: str,
        markdown: str,
    ) -> int:
        entrada = self.dados["pecas"].get(peca_id)
        versao = self.proxima_versao(peca_id)

        pasta = self.dir_peca(peca_id)
        pasta.mkdir(parents=True, exist_ok=True)
        doc = {
            "id": peca_id,
            "versao": versao,
            "criado_em": _agora(),
            "modelo": modelo,
            "brief": brief.model_dump(mode="json"),
            "peca": peca.model_dump(mode="json"),
            "achados": [a.to_dict() for a in achados],
        }
        (pasta / f"v{versao}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        (pasta / f"v{versao}.md").write_text(markdown, encoding="utf-8")

        if entrada is None:
            entrada = {
                "id": peca_id,
                "titulo": peca.titulo_interno,
                "pilar": brief.pilar.value,
                "frente": brief.frente.value,
                "formato": brief.formato.value,
                "publico": brief.publico.value,
                "produto_id": brief.produto_id,
                "origem": brief.origem,
                "criado_em": doc["criado_em"],
                "status": StatusPeca.revisao.value,
                "historico": [{"status": StatusPeca.revisao.value, "em": doc["criado_em"], "responsavel": "agente", "nota": "gerada"}],
                "imagens": [],
                "publicacao": None,
            }
        entrada["versao_atual"] = versao
        entrada["atualizado_em"] = doc["criado_em"]
        entrada["bloqueios"] = sum(1 for a in achados if a.nivel.value == "bloqueio")
        self.dados["pecas"][peca_id] = entrada
        self._gravar()
        return versao

    def carregar(self, peca_id: str, versao: int | None = None) -> dict:
        entrada = self.dados["pecas"].get(peca_id)
        if not entrada:
            raise ErroRegistro(f"Peça {peca_id} não encontrada.")
        v = versao or entrada["versao_atual"]
        caminho = self.dir_peca(peca_id) / f"v{v}.json"
        if not caminho.exists():
            raise ErroRegistro(f"Versão v{v} de {peca_id} não encontrada.")
        return json.loads(caminho.read_text(encoding="utf-8"))

    def carregar_modelos(self, peca_id: str, versao: int | None = None) -> tuple[Peca, Brief, list[Achado], dict]:
        doc = self.carregar(peca_id, versao)
        return (
            Peca.model_validate(doc["peca"]),
            Brief.model_validate(doc["brief"]),
            [Achado.from_dict(a) for a in doc["achados"]],
            doc,
        )

    def entrada(self, peca_id: str) -> dict:
        if peca_id not in self.dados["pecas"]:
            raise ErroRegistro(f"Peça {peca_id} não encontrada.")
        return self.dados["pecas"][peca_id]

    def listar(self, status: str | None = None, frente: str | None = None) -> list[dict]:
        itens = list(self.dados["pecas"].values())
        if status:
            itens = [i for i in itens if i["status"] == status]
        if frente:
            itens = [i for i in itens if i["frente"] == frente]
        return sorted(itens, key=lambda i: i["criado_em"], reverse=True)

    # ------------------------------------------------------------------ status
    def atualizar_status(self, peca_id: str, novo: StatusPeca, responsavel: str, nota: str | None = None) -> None:
        entrada = self.entrada(peca_id)
        atual = StatusPeca(entrada["status"])
        if novo == atual:
            return

        if novo == StatusPeca.aprovado:
            _, _, achados, _ = self.carregar_modelos(peca_id)
            if tem_bloqueio(achados):
                raise ErroRegistro("A versão atual tem bloqueios; corrija (nova versão) antes de aprovar.")
            if not responsavel or responsavel == "agente":
                raise ErroRegistro("Aprovação exige o nome do responsável humano (--responsavel).")
        if novo == StatusPeca.publicado and atual != StatusPeca.aprovado:
            raise ErroRegistro("Só peças aprovadas podem ser marcadas como publicadas.")
        if novo == StatusPeca.analisado and atual != StatusPeca.publicado:
            raise ErroRegistro("Só peças publicadas podem ser marcadas como analisadas.")
        if novo in _ORDEM and atual in _ORDEM and _ORDEM.index(novo) > _ORDEM.index(atual) + 1 and novo != StatusPeca.aprovado:
            raise ErroRegistro(f"Transição {atual.value} → {novo.value} pula etapas.")

        entrada["status"] = novo.value
        entrada["historico"].append({"status": novo.value, "em": _agora(), "responsavel": responsavel, "nota": nota})
        self._gravar()

    def registrar_publicacao(self, peca_id: str, *, url: str | None, data: str, campanha: str | None, criativo: str | None, responsavel: str) -> None:
        entrada = self.entrada(peca_id)
        if entrada["status"] != StatusPeca.aprovado.value:
            raise ErroRegistro("Só peças aprovadas podem ser registradas como publicadas.")
        entrada["publicacao"] = {"url_ou_id": url, "data": data, "campanha": campanha, "criativo": criativo, "versao": entrada["versao_atual"]}
        self._gravar()
        self.atualizar_status(peca_id, StatusPeca.publicado, responsavel, nota=f"publicada em {data}")

    # ------------------------------------------------------------------ imagens
    def salvar_imagem(self, peca_id: str | None, dados: bytes, extensao: str, prompt: str, modelo: str, proporcao: str) -> Path:
        if peca_id:
            entrada = self.entrada(peca_id)
            pasta = self.dir_peca(peca_id) / "imagens"
            prefixo = f"v{entrada['versao_atual']}"
        else:
            entrada = None
            pasta = self.dir / "imagens_livres"
            prefixo = datetime.now().strftime("%Y%m%d")
        pasta.mkdir(parents=True, exist_ok=True)
        n = len(list(pasta.glob(f"{prefixo}_*"))) // 2 + 1
        caminho = pasta / f"{prefixo}_{n:02d}.{extensao}"
        caminho.write_bytes(dados)
        meta = {"arquivo": caminho.name, "prompt": prompt, "modelo": modelo, "proporcao": proporcao, "criado_em": _agora(), "tipo": "imagem_gerada_ia"}
        caminho.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        if entrada is not None:
            entrada["imagens"].append(str(caminho.relative_to(self.dir)))
            self._gravar()
        return caminho

    # ------------------------------------------------------------------ artes finais
    def registrar_arte(self, peca_id: str, pasta: Path, *, rascunho: bool) -> None:
        entrada = self.entrada(peca_id)
        rel = str(pasta.relative_to(self.dir))
        artes = [a for a in entrada.get("artes", []) if a["pasta"] != rel]
        artes.append({"pasta": rel, "rascunho": rascunho, "em": _agora()})
        entrada["artes"] = artes
        self._gravar()

    # ------------------------------------------------------------------ calendários
    def novo_id_calendario(self) -> str:
        dia = datetime.now().strftime("%Y%m%d")
        return f"C-{dia}-{self._proximo('C' + dia):02d}"

    def salvar_calendario(self, cal_id: str, cal: Calendario, markdown: str, distribuicao: dict) -> Path:
        pasta = self.dir / "calendarios"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"{cal_id}.json"
        caminho.write_text(json.dumps({"id": cal_id, "calendario": cal.model_dump(mode="json"), "distribuicao": distribuicao}, ensure_ascii=False, indent=2), encoding="utf-8")
        (pasta / f"{cal_id}.md").write_text(markdown, encoding="utf-8")
        self.dados["calendarios"][cal_id] = {"id": cal_id, "periodo": cal.periodo, "itens": len(cal.itens), "criado_em": _agora()}
        self._gravar()
        return caminho

    def carregar_calendario(self, cal_id_ou_caminho: str) -> tuple[str, Calendario]:
        p = Path(cal_id_ou_caminho)
        if not p.exists():
            p = self.dir / "calendarios" / f"{cal_id_ou_caminho}.json"
        if not p.exists():
            raise ErroRegistro(f"Calendário {cal_id_ou_caminho} não encontrado.")
        doc = json.loads(p.read_text(encoding="utf-8"))
        return doc.get("id", p.stem), Calendario.model_validate(doc["calendario"])

    # ------------------------------------------------------------------ revisões
    def salvar_revisao(self, alvo: str, revisao_json: dict, markdown: str) -> Path:
        pasta = self.dir / "revisoes"
        pasta.mkdir(parents=True, exist_ok=True)
        rev_id = datetime.now().strftime("R-%Y%m%d-%H%M%S")
        (pasta / f"{rev_id}.json").write_text(json.dumps({"id": rev_id, "alvo": alvo, **revisao_json}, ensure_ascii=False, indent=2), encoding="utf-8")
        caminho = pasta / f"{rev_id}.md"
        caminho.write_text(markdown, encoding="utf-8")
        self.dados["revisoes"][rev_id] = {"id": rev_id, "alvo": alvo, "veredito": revisao_json.get("veredito"), "criado_em": _agora()}
        self._gravar()
        return caminho
