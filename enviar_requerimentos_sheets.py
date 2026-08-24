"""
Envia o conteúdo de data/requerimentos.csv para a aba "requerimentos" da
planilha Google Sheets configurada em .streamlit/secrets.toml.
"""
import os

import pandas as pd
import tomllib

from sheets_utils import COLUNAS_REQ, ABA_REQ, SCOPES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "requerimentos.csv")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")


def main():
    import gspread

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    client = gspread.service_account_from_dict(secrets["gcp_service_account"], scopes=SCOPES)
    planilha = client.open_by_key(secrets["sheet_id"])
    try:
        ws = planilha.worksheet(ABA_REQ)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=ABA_REQ, rows=1000, cols=len(COLUNAS_REQ))

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[COLUNAS_REQ]

    ws.clear()
    ws.update([COLUNAS_REQ] + df.values.tolist())
    print(f"{len(df)} requerimentos enviados para a planilha.")


if __name__ == "__main__":
    main()
