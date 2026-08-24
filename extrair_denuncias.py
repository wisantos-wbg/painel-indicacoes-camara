"""
Consolida os lotes JSON extraídos pelos agentes (data/raw_denuncias_*.json)
em um único CSV editável: data/diversos.csv

Ao contrário de Indicações e Requerimentos, denúncias não têm número formal
(são menções soltas nas falas dos vereadores). Reexecutável: casa cada
registro com um já existente na planilha por (Data_Sessao, Resumo) para
preservar edições manuais (Direcionada_A, Status_Acompanhamento,
Observacoes) já feitas pelo usuário.
"""
import json
import os
import glob
import csv
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_CSV = os.path.join(DATA_DIR, "diversos.csv")

sys.path.insert(0, BASE_DIR)

STATUS_PADRAO = "Pendente de Verificação"


def carregar_lotes():
    registros = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "raw_denuncias_*.json"))):
        with open(path, encoding="utf-8") as f:
            registros.extend(json.load(f))
    return registros


def carregar_existentes():
    existentes = {}
    secrets_path = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")
    try:
        import tomllib
        import gspread
        from sheets_utils import COLUNAS_DEN, ABA_DEN, SCOPES

        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        client = gspread.service_account_from_dict(secrets["gcp_service_account"], scopes=SCOPES)
        planilha = client.open_by_key(secrets["sheet_id"])
        ws = planilha.worksheet(ABA_DEN)
        valores = ws.get_all_values()
        if valores and valores[0] == COLUNAS_DEN:
            for linha in valores[1:]:
                row = dict(zip(COLUNAS_DEN, linha))
                chave = (row["Data_Sessao"], row["Resumo"])
                existentes[chave] = row
        if existentes:
            print(f"{len(existentes)} denúncias existentes carregadas da planilha Google Sheets.")
            return existentes
    except Exception as e:
        print(f"Aviso: não foi possível ler a planilha Google Sheets ({e}). Usando CSV local como referência.")

    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                chave = (row["Data_Sessao"], row["Resumo"])
                existentes[chave] = row
    return existentes


def main():
    registros = carregar_lotes()
    existentes = carregar_existentes()

    linhas = []
    vistos = set()
    for r in registros:
        ano = str(r.get("ano") or "").strip()
        if not ano:
            continue
        vereadores = ", ".join(r.get("vereadores") or [])
        resumo = (r.get("resumo") or "").strip()
        if not resumo:
            continue
        data_sessao = r.get("data_sessao") or ""
        chave = (data_sessao, resumo)
        if chave in vistos:
            continue
        vistos.add(chave)

        prev = existentes.get(chave)
        direcionada = prev["Direcionada_A"] if prev and prev.get("Direcionada_A") else (r.get("direcionada_a") or "")
        status = prev["Status_Acompanhamento"] if prev and prev.get("Status_Acompanhamento") else STATUS_PADRAO
        observ = prev["Observacoes"] if prev and prev.get("Observacoes") else (r.get("nota_revisao") or "")

        linhas.append({
            "Ano": ano,
            "Sessao": r.get("sessao") or "",
            "Data_Sessao": data_sessao,
            "Vereador": vereadores,
            "Resumo": resumo,
            "Direcionada_A": direcionada,
            "Tipo": r.get("tipo") or "",
            "Status_Acompanhamento": status,
            "Observacoes": observ,
        })

    linhas.sort(key=lambda x: x["Data_Sessao"])
    for i, linha in enumerate(linhas, 1):
        linha["ID"] = f"DEN-{i:03d}"

    campos = ["ID", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo",
              "Direcionada_A", "Tipo", "Status_Acompanhamento", "Observacoes"]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: linha[k] for k in campos})

    sem_direcionamento = sum(1 for l in linhas if not l["Direcionada_A"])
    print(f"Total de denúncias consolidadas: {len(linhas)}")
    print(f"Sem destinatário identificado: {sem_direcionamento}")
    print(f"CSV salvo em: {OUT_CSV}")


if __name__ == "__main__":
    main()
