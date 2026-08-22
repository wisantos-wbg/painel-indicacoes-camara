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

        # Corrige grafia da concessionária no Requerimento 052/2026
        if linha["Ano"] == "2026" and linha["Numero_Requerimento"] == "052":
            linha["Resumo"] = linha["Resumo"].replace(
                "concessionária Eletro Rede S.A.", "concessionária Elektro"
            ).replace("Eletro Rede S.A.", "Elektro")

    # Ofício 025/2025 do Prefeito Municipal, tratado na sessão como um
    # "requerimento" do Executivo (pedindo devolução dos Projetos de Lei
    # 68/2024, 74/2024 e 75/2024); rejeitado por 5 votos a 3. NÃO é o mesmo
    # que o Requerimento nº 025/2025 de vereador (Renato Vieira de Brito,
    # sessão de 26/05) — a numeração coincide por acaso porque o Executivo
    # usa sequência de ofícios, não a sequência de requerimentos da Câmara.
    # Não é requerimento de vereador, mas William pediu para incluí-lo no
    # painel indicando quem o requereu.
    if not any(l["Ano"] == "2025" and l["Numero_Requerimento"] == "025-EXEC" for l in linhas):
        linhas.append({
            "ID": "REQ-999",
            "Numero_Requerimento": "025-EXEC",
            "Ano": "2025",
            "Sessao": "1ª Sessão Ordinária da 19ª Legislatura",
            "Data_Sessao": "2025-02-03",
            "Vereador": "Prefeito Municipal (Elio Furini Neto)",
            "Resumo": "Solicita a devolução dos Projetos de Lei nº 68/2024 (denominação da rota ecológica de Junqueirópolis), nº 74/2024 (denominação da Casa do Artesanato de Junqueirópolis) e nº 75/2024 (institui o Plano Municipal da Primeira Infância), com suas respectivas mensagens.",
            "Diretoria_Destino": "",
            "Resultado_Votacao": "Rejeitado",
            "Oficio_Resposta": "Ofício 025/2025",
            "Status_Resposta": "Pendente",
            "Observacoes": "Não é um Requerimento de vereador: é o Ofício 025/2025 do Prefeito Municipal (Poder Executivo), tratado na sessão como pedido a ser votado em plenário. Numeração 025 coincide por acaso com o Requerimento de vereador 025/2025 (sequências diferentes). Caso excepcional incluído no painel a pedido do usuário. Rejeitado por 5 votos a 3 na sessão de 2025-02-03.",
        })
        alteradas += 1

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
