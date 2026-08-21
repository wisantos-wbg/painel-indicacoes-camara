"""
Consolida os lotes JSON extraídos pelos agentes (data/raw_extract_lote*.json)
em um único CSV editável: data/indicacoes.csv

Também aplica classificação automática de Setor por palavras-chave.
Reexecutável: se data/indicacoes.csv já existir, preserva edições manuais
feitas pelo usuário (Setor, Oficio_Resposta, Status_Atendimento, Observacoes)
para indicações já existentes, casando por (Ano, Numero_Indicacao).
"""
import json
import os
import re
import glob
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_CSV = os.path.join(DATA_DIR, "indicacoes.csv")

STATUS_PADRAO = "Pendente de Análise"

SETORES_KEYWORDS = [
    ("Saúde", [
        "saúde", "posto de saúde", "ubs", "unidade básica", "hospital", "médic",
        "enferm", "ambulânc", "ginecolog", "odontol", "psicólog", "vacin",
        "farmác", "remédio", "medicamento", "castra", "clínica", "atendimento clínico",
    ]),
    ("Educação", [
        "escola", "educaç", "creche", "emei", "emef", "aluno", "professor",
        "merenda", "material escolar", "reforço escolar", "biblioteca",
    ]),
    ("Trânsito e Mobilidade", [
        "lombada", "semáforo", "sinalização", "faixa de pedestre", "trânsito",
        "estacionamento", "rotatória", "ciclovia", "radar", "velocidade",
        "mobilidade", "ônibus", "transporte público", "ponto de ônibus",
    ]),
    ("Obras e Serviços Públicos", [
        "tapa-buraco", "tapa buraco", "buraco", "asfalto", "asfáltic", "recapeamento",
        "pavimentaç", "iluminação pública", "poste", "calçada", "meio-fio", "meio fio",
        "bueiro", "boca de lobo", "galeria pluvial", "esgoto", "água pluvial",
        "rede de água", "saneamento", "obra", "reforma", "construção", "manutenção predial",
        "cascalhamento", "patrolamento", "estrada rural", "estrada vicinal",
    ]),
    ("Meio Ambiente", [
        "meio ambiente", "árvore", "poda", "arboriz", "praça", "jardim", "limpeza urbana",
        "coleta de lixo", "resíduo", "reciclagem", "animal", "zoonose", "área verde",
        "parque",
    ]),
    ("Esporte e Lazer", [
        "esporte", "quadra", "poliesportiv", "campo de futebol", "ginásio", "lazer",
        "playground", "parquinho", "skate", "bocha", "academia ao ar livre",
    ]),
    ("Administração e Finanças", [
        "concurso público", "servidor", "quadro de pessoal", "orçamento", "licitaç",
        "contrato administrativo", "diária", "folha de pagamento", "informátic",
        "computador", "sistema administrativo", "recursos humanos",
    ]),
    ("Agricultura e Meio Rural", [
        "agricultura", "produtor rural", "zona rural", "patrulha agrícola", "trator",
        "irrigaç", "assentamento", "agropecuár", "rural",
    ]),
]


def classificar_setor(resumo: str) -> str:
    texto = (resumo or "").lower()
    for setor, termos in SETORES_KEYWORDS:
        for termo in termos:
            if termo in texto:
                return setor
    return "A Classificar"


def carregar_lotes():
    registros = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "raw_extract_lote*.json"))):
        with open(path, encoding="utf-8") as f:
            registros.extend(json.load(f))
    return registros


def normalizar_numero(num) -> str:
    s = re.sub(r"\D", "", str(num or ""))
    return s.zfill(3) if s else ""


def carregar_existentes():
    existentes = {}
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                chave = (row["Ano"], row["Numero_Indicacao"])
                existentes[chave] = row
    return existentes


def main():
    registros = carregar_lotes()
    existentes = carregar_existentes()

    linhas = []
    vistos = set()
    for r in registros:
        ano = str(r.get("ano") or "").strip()
        numero = normalizar_numero(r.get("numero_indicacao"))
        chave = (ano, numero)
        if not ano or not numero:
            continue
        if chave in vistos:
            continue
        vistos.add(chave)

        prev = existentes.get(chave)
        vereadores = ", ".join(r.get("vereadores") or [])
        resumo = (r.get("resumo") or "").strip()

        setor = prev["Setor"] if prev and prev.get("Setor") else classificar_setor(resumo)
        oficio = prev["Oficio_Resposta"] if prev and prev.get("Oficio_Resposta") else (r.get("oficio_resposta") or "")
        status = prev["Status_Atendimento"] if prev and prev.get("Status_Atendimento") else (r.get("status_atendimento") or STATUS_PADRAO)
        observ = prev["Observacoes"] if prev and prev.get("Observacoes") else (r.get("nota_revisao") or "")

        linhas.append({
            "Numero_Indicacao": numero,
            "Ano": ano,
            "Sessao": r.get("sessao") or "",
            "Data_Sessao": r.get("data_sessao") or "",
            "Vereador": vereadores,
            "Resumo": resumo,
            "Setor": setor,
            "Oficio_Resposta": oficio,
            "Status_Atendimento": status,
            "Observacoes": observ,
        })

    linhas.sort(key=lambda x: (x["Data_Sessao"], x["Numero_Indicacao"]))
    for i, linha in enumerate(linhas, 1):
        linha_id = f"IND-{i:03d}"
        linha["ID"] = linha_id

    campos = ["ID", "Numero_Indicacao", "Ano", "Sessao", "Data_Sessao", "Vereador",
              "Resumo", "Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: linha[k] for k in campos})

    sem_setor = sum(1 for l in linhas if l["Setor"] == "A Classificar")
    print(f"Total de indicações consolidadas: {len(linhas)}")
    print(f"Sem setor classificado automaticamente: {sem_setor}")
    print(f"CSV salvo em: {OUT_CSV}")


if __name__ == "__main__":
    main()
