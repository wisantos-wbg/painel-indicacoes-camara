import gspread
import pandas as pd
import streamlit as st

COLUNAS = ["ID", "Numero_Indicacao", "Ano", "Sessao", "Data_Sessao", "Vereador",
           "Resumo", "Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]

ABA = "indicacoes"


def _worksheet():
    client = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    planilha = client.open_by_key(st.secrets["sheet_id"])
    try:
        return planilha.worksheet(ABA)
    except gspread.WorksheetNotFound:
        return planilha.add_worksheet(title=ABA, rows=1000, cols=len(COLUNAS))


def carregar_dataframe() -> pd.DataFrame:
    ws = _worksheet()
    valores = ws.get_all_values()
    if not valores or valores[0] != COLUNAS:
        return pd.DataFrame(columns=COLUNAS)
    linhas = valores[1:]
    df = pd.DataFrame(linhas, columns=COLUNAS)
    return df.fillna("")


def salvar_dataframe(df: pd.DataFrame):
    ws = _worksheet()
    df = df[COLUNAS].fillna("")
    ws.clear()
    ws.update([COLUNAS] + df.values.tolist())
