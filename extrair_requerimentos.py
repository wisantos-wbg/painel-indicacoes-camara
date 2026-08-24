"""
Consolida os lotes JSON extraídos pelos agentes (data/raw_requerimentos_*.json)
em um único CSV editável: data/requerimentos.csv

Reexecutável: se data/requerimentos.csv já existir (ou a planilha Google
Sheets), preserva edições manuais feitas pelo usuário (Resultado_Votacao,
Oficio_Resposta, Status_Resposta, Observacoes) para requerimentos já
existentes, casando por (Ano, Numero_Requerimento).
"""
import json
import os
import re
import glob
import csv
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_CSV = os.path.join(DATA_DIR, "requerimentos.csv")

sys.path.insert(0, BASE_DIR)

STATUS_PADRAO = "Pendente"


def carregar_lotes():
    registros = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "raw_requerimentos_*.json"))):
        with open(path, encoding="utf-8") as f:
            registros.extend(json.load(f))
    return registros


def normalizar_numero(num) -> str:
    s = re.sub(r"\D", "", str(num or ""))
    return s.zfill(3) if s else ""


def carregar_existentes():
    existentes = {}
    secrets_path = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")
    try:
        import tomllib
        import gspread
        from sheets_utils import COLUNAS_REQ, ABA_REQ, SCOPES

        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        client = gspread.service_account_from_dict(secrets["gcp_service_account"], scopes=SCOPES)
        planilha = client.open_by_key(secrets["sheet_id"])
        ws = planilha.worksheet(ABA_REQ)
        valores = ws.get_all_values()
        if valores and valores[0] == COLUNAS_REQ:
            for linha in valores[1:]:
                row = dict(zip(COLUNAS_REQ, linha))
                chave = (row["Ano"], row["Numero_Requerimento"])
                existentes[chave] = row
        if existentes:
            print(f"{len(existentes)} requerimentos existentes carregados da planilha Google Sheets.")
            return existentes
    except Exception as e:
        print(f"Aviso: não foi possível ler a planilha Google Sheets ({e}). Usando CSV local como referência.")

    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                chave = (row["Ano"], row["Numero_Requerimento"])
                existentes[chave] = row
    return existentes


SITUACOES_COM_ETIQUETA = {
    "Urgência Especial": "[Requerimento de Urgência Especial]",
    "Verbal/Não Formalizado": "[Pedido verbal, ainda não formalizado/numerado]",
    "Executivo": "[Apresentado pelo Poder Executivo, não por vereador]",
}


def montar_observacoes(situacao: str, nota_revisao: str) -> str:
    partes = []
    etiqueta = SITUACOES_COM_ETIQUETA.get((situacao or "").strip())
    if etiqueta:
        partes.append(etiqueta)
    if nota_revisao:
        partes.append(nota_revisao.strip())
    return " ".join(partes)


def main():
    registros = carregar_lotes()
    existentes = carregar_existentes()

    linhas = []
    vistos = set()
    sem_numero_seq = 0
    for r in registros:
        ano = str(r.get("ano") or "").strip()
        if not ano:
            continue
        numero = normalizar_numero(r.get("numero_requerimento"))
        if numero:
            chave = (ano, numero)
        else:
            # Pedido verbal/não formalizado sem número: chave sintética
            # única (não tenta casar com edições manuais anteriores).
            sem_numero_seq += 1
            chave = (ano, f"SN{sem_numero_seq:03d}")
        if chave in vistos:
            continue
        vistos.add(chave)

        prev = existentes.get(chave)
        vereadores = ", ".join(r.get("vereadores") or [])
        resumo = (r.get("resumo") or "").strip()
        observ_extraida = montar_observacoes(r.get("situacao"), r.get("nota_revisao"))

        diretoria = prev["Diretoria_Destino"] if prev and prev.get("Diretoria_Destino") else (r.get("diretoria_destino") or "")
        resultado = prev["Resultado_Votacao"] if prev and prev.get("Resultado_Votacao") else (r.get("resultado_votacao") or ("Aprovado" if numero else ""))
        oficio = prev["Oficio_Resposta"] if prev and prev.get("Oficio_Resposta") else (r.get("oficio_resposta") or "")
        status = prev["Status_Resposta"] if prev and prev.get("Status_Resposta") else (r.get("status_resposta") or STATUS_PADRAO)
        observ = prev["Observacoes"] if prev and prev.get("Observacoes") else observ_extraida

        linhas.append({
            "Numero_Requerimento": numero,
            "Ano": ano,
            "Sessao": r.get("sessao") or "",
            "Data_Sessao": r.get("data_sessao") or "",
            "Vereador": vereadores,
            "Resumo": resumo,
            "Diretoria_Destino": diretoria,
            "Resultado_Votacao": resultado,
            "Oficio_Resposta": oficio,
            "Status_Resposta": status,
            "Observacoes": observ,
        })

    linhas.sort(key=lambda x: (x["Data_Sessao"], x["Numero_Requerimento"]))
    for i, linha in enumerate(linhas, 1):
        linha["ID"] = f"REQ-{i:03d}"

    campos = ["ID", "Numero_Requerimento", "Ano", "Sessao", "Data_Sessao", "Vereador",
              "Resumo", "Diretoria_Destino", "Resultado_Votacao", "Oficio_Resposta",
              "Status_Resposta", "Observacoes"]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: linha[k] for k in campos})

    sem_diretoria = sum(1 for l in linhas if not l["Diretoria_Destino"])
    print(f"Total de requerimentos consolidados: {len(linhas)}")
    print(f"Sem diretoria identificada: {sem_diretoria}")
    print(f"CSV salvo em: {OUT_CSV}")


if __name__ == "__main__":
    main()
