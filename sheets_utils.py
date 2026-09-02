import gspread
import pandas as pd
import streamlit as st

COLUNAS = ["ID", "Numero_Indicacao", "Ano", "Sessao", "Data_Sessao", "Vereador",
           "Resumo", "Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]
ABA = "indicacoes"

COLUNAS_REQ = ["ID", "Numero_Requerimento", "Ano", "Sessao", "Data_Sessao", "Vereador",
               "Resumo", "Diretoria_Destino", "Resultado_Votacao", "Oficio_Resposta",
               "Status_Resposta", "Observacoes"]
ABA_REQ = "requerimentos"

COLUNAS_DEN = ["ID", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo",
               "Direcionada_A", "Tipo", "Status_Acompanhamento", "Observacoes"]
ABA_DEN = "diversos"

COLUNAS_2124 = ["ID", "Tipo", "Numero", "Ano", "Sessao", "Data_Sessao", "Vereador",
                "Resumo", "Setor_Diretoria", "Situacao", "Resultado_Votacao",
                "Oficio_Resposta", "Status", "Observacoes"]
ABA_2124 = "2021-2024"


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client():
    return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)


def _worksheet(aba: str, colunas: list):
    client = _client()
    planilha = client.open_by_key(st.secrets["sheet_id"])
    try:
        return planilha.worksheet(aba)
    except gspread.WorksheetNotFound:
        return planilha.add_worksheet(title=aba, rows=1000, cols=len(colunas))


def carregar_dataframe(aba: str = ABA, colunas: list = COLUNAS) -> pd.DataFrame:
    ws = _worksheet(aba, colunas)
    valores = ws.get_all_values()
    if not valores or valores[0] != colunas:
        return pd.DataFrame(columns=colunas)
    linhas = valores[1:]
    df = pd.DataFrame(linhas, columns=colunas)
    return df.fillna("")


def salvar_dataframe(df: pd.DataFrame, aba: str = ABA, colunas: list = COLUNAS):
    ws = _worksheet(aba, colunas)
    df = df[colunas].fillna("")
    ws.clear()
    ws.update([colunas] + df.values.tolist())
