"""
Envia o conteúdo de data/diversos.csv para a aba "diversos" da
planilha Google Sheets configurada em .streamlit/secrets.toml.
"""
import os

import pandas as pd
import tomllib

from sheets_utils import COLUNAS_DEN, ABA_DEN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "diversos.csv")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")


def main():
    import gspread

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    client = gspread.service_account_from_dict(secrets["gcp_service_account"])
    planilha = client.open_by_key(secrets["sheet_id"])
    try:
        ws = planilha.worksheet(ABA_DEN)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=ABA_DEN, rows=1000, cols=len(COLUNAS_DEN))

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[COLUNAS_DEN]

    ws.clear()
    ws.update([COLUNAS_DEN] + df.values.tolist())
    print(f"{len(df)} denúncias enviadas para a planilha.")


if __name__ == "__main__":
    main()
