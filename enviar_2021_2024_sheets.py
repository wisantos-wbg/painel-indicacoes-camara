"""
Envia o conteúdo de data/consolidado_2021_2024.csv (Indicações + Requerimentos +
Denúncias da 18ª Legislatura, 2021-2024, numa aba única) para a planilha Google
Sheets configurada em .streamlit/secrets.toml.
"""
import os

import pandas as pd
import tomllib

from sheets_utils import SCOPES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "consolidado_2021_2024.csv")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")

COLUNAS = ["ID", "Tipo", "Numero", "Ano", "Sessao", "Data_Sessao", "Vereador",
           "Resumo", "Setor_Diretoria", "Situacao", "Resultado_Votacao",
           "Oficio_Resposta", "Status", "Observacoes"]
ABA = "2021-2024"


def main():
    import gspread

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    client = gspread.service_account_from_dict(secrets["gcp_service_account"], scopes=SCOPES)
    planilha = client.open_by_key(secrets["sheet_id"])
    try:
        ws = planilha.worksheet(ABA)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=ABA, rows=len(pd.read_csv(CSV_PATH)) + 10, cols=len(COLUNAS))

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[COLUNAS]

    ws.clear()
    ws.update([COLUNAS] + df.values.tolist())
    print(f"{len(df)} registros (2021-2024) enviados para a aba '{ABA}'.")


if __name__ == "__main__":
    main()
