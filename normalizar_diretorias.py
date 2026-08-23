"""
Normaliza o campo Diretoria_Destino de data/requerimentos.csv para os 9 nomes
oficiais informados por William, corrige a grafia "Elektro" no Requerimento
052/2026 e acrescenta o Requerimento 025/2025 (apresentado pelo Prefeito,
excepcionalmente incluído no painel a pedido do usuário).

Script de uso único (não faz parte do pipeline de extração recorrente).
"""
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "requerimentos.csv")

DIRETORIAS_OFICIAIS = [
    "Diretoria Administrativa",
    "Diretoria de Agronegócio, Indústria, Comércio e Meio Ambiente e Gestão de Resíduos Sólidos",
    "Diretoria de Assistência Social",
    "Diretoria de Educação, Cultura, Esportes, Lazer e Turismo",
    "Diretoria de Fazenda, Compras, Almoxarifado e Recursos Humanos",
    "Diretoria de Planejamento, Obras, Serviços e Manutenção",
    "Diretoria de Saúde",
    "Diretoria Jurídica, Habitação e de Trânsito",
    "Diretoria de Licitações, Contratos e Convênios",
]

# Ordem importa: regras mais específicas primeiro.
REGRAS = [
    ("licita", "Diretoria de Licitações, Contratos e Convênios"),
    ("juridic", "Diretoria Jurídica, Habitação e de Trânsito"),
    ("juríd", "Diretoria Jurídica, Habitação e de Trânsito"),
    ("agronegoc", "Diretoria de Agronegócio, Indústria, Comércio e Meio Ambiente e Gestão de Resíduos Sólidos"),
    ("agronegóc", "Diretoria de Agronegócio, Indústria, Comércio e Meio Ambiente e Gestão de Resíduos Sólidos"),
    ("assist", "Diretoria de Assistência Social"),
    ("educac", "Diretoria de Educação, Cultura, Esportes, Lazer e Turismo"),
    ("educaç", "Diretoria de Educação, Cultura, Esportes, Lazer e Turismo"),
    ("fazenda", "Diretoria de Fazenda, Compras, Almoxarifado e Recursos Humanos"),
    ("planejamento", "Diretoria de Planejamento, Obras, Serviços e Manutenção"),
    ("obras", "Diretoria de Planejamento, Obras, Serviços e Manutenção"),
    ("obra,", "Diretoria de Planejamento, Obras, Serviços e Manutenção"),
    ("manuten", "Diretoria de Planejamento, Obras, Serviços e Manutenção"),
    ("saude", "Diretoria de Saúde"),
    ("saúde", "Diretoria de Saúde"),
    ("administrativ", "Diretoria Administrativa"),
]


def normalizar(valor: str) -> tuple[str, bool]:
    v = (valor or "").strip()
    if not v:
        return v, False
    if v in DIRETORIAS_OFICIAIS:
        return v, False
    lower = v.lower()
    for chave, oficial in REGRAS:
        if chave in lower:
            return oficial, (oficial != v)
    return v, False


def main():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        campos = reader.fieldnames
        linhas = list(reader)

    alteradas = 0
    for linha in linhas:
        novo, mudou = normalizar(linha["Diretoria_Destino"])
        if mudou:
            linha["Diretoria_Destino"] = novo
            alteradas += 1

        # Corrige grafia da concessionária de energia em qualquer registro
        for variante in ("Eletro Redes S.A.", "Eletro Rede S.A.", "Eletro Redes", "Eletro Rede"):
            linha["Resumo"] = linha["Resumo"].replace(variante, "Elektro")
            linha["Diretoria_Destino"] = linha["Diretoria_Destino"].replace(variante, "Elektro")
        if "Eletro Rede" in linha["Diretoria_Destino"] or linha["Diretoria_Destino"].strip() == "Concessionária Eletro Rede S.A.":
            linha["Diretoria_Destino"] = "Concessionária Elektro"

    # O Ofício 025/2025 do Executivo já vem do pipeline normal de extração
    # (raw_requerimentos_2025_lote1.json, situação "Executivo", numero=null
    # para não colidir com o Requerimento 025/2025 real de vereador) — não é
    # mais necessário injetá-lo manualmente aqui.

    linhas.sort(key=lambda l: (l["Data_Sessao"], l["Numero_Requerimento"]))
    for i, linha in enumerate(linhas, 1):
        linha["ID"] = f"REQ-{i:03d}"

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for linha in linhas:
            writer.writerow({k: linha[k] for k in campos})

    print(f"Linhas alteradas/adicionadas: {alteradas}")
    print(f"Total de requerimentos no CSV: {len(linhas)}")


if __name__ == "__main__":
    main()
