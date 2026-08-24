"""
Envia o conteúdo de data/indicacoes.csv (gerado por extrair_indicacoes.py)
para a planilha Google Sheets configurada em .streamlit/secrets.toml.
Rode uma vez após reprocessar extrair_indicacoes.py para publicar as
atualizações na planilha usada pelo app.py.
"""
import os

import pandas as pd
import tomllib

from sheets_utils import COLUNAS, SCOPES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "indicacoes.csv")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")


def main():
    import gspread

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    client = gspread.service_account_from_dict(secrets["gcp_service_account"], scopes=SCOPES)
    planilha = client.open_by_key(secrets["sheet_id"])
    try:
        ws = planilha.worksheet("indicacoes")
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title="indicacoes", rows=1000, cols=len(COLUNAS))

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[COLUNAS]

    ws.clear()
    ws.update([COLUNAS] + df.values.tolist())
    print(f"{len(df)} indicações enviadas para a planilha.")


if __name__ == "__main__":
    main()
