"""
Cruza os dados extraídos das transcrições (data/indicacoes.csv,
data/requerimentos.csv) com os dados oficiais baixados do site da Câmara
(data/oficial_indicacoes.csv, data/oficial_requerimentos.csv — gerados por
scrape_site_camara.py) e produz um relatório JSON de divergências e lacunas,
consumido depois pelo gerador do documento de revisão.

Uso: python cruzar_com_site.py
"""
import csv
import json
import os
import re

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")


def carregar_csv(nome):
    caminho = os.path.join(DATA_DIR, nome)
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def normalizar_nomes(texto):
    """'Fulano (Autor), Beltrano (Autor)' ou 'Fulano, Beltrano' -> ['Fulano', 'Beltrano']"""
    if not texto:
        return []
    partes = re.split(r",\s*", texto)
    nomes = []
    for p in partes:
        p = re.sub(r"\s*\(Autor\)\s*", "", p).strip()
        if p:
            nomes.append(p)
    return nomes


def ultima_data_coberta(registros_projeto):
    datas = [r["Data_Sessao"] for r in registros_projeto if r.get("Data_Sessao")]
    return max(datas) if datas else None


def data_br_para_iso(data_br):
    # "04/08/2025" -> "2025-08-04"
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", data_br or "")
    if not m:
        return None
    d, mth, y = m.groups()
    return f"{y}-{mth}-{d}"


def cruzar(nome_categoria, campo_numero, arquivo_projeto, arquivo_oficial):
    projeto = carregar_csv(arquivo_projeto)
    oficial = carregar_csv(arquivo_oficial)

    ultima_data = ultima_data_coberta(projeto)
    print(f"[{nome_categoria}] última sessão coberta pelas transcrições: {ultima_data}")

    idx_projeto = {}
    for r in projeto:
        chave = (r["Ano"], r[campo_numero].lstrip("0") or "0")
        idx_projeto.setdefault(chave, []).append(r)

    idx_oficial = {}
    for r in oficial:
        chave = (r["Ano"], r["Numero"].lstrip("0") or "0")
        idx_oficial[chave] = r

    divergencias = []
    faltando_no_projeto_dentro_periodo = []
    faltando_no_projeto_fora_periodo = []
    so_no_projeto = []

    for chave, r_of in idx_oficial.items():
        if not chave[1] or chave[1] == "0":
            continue
        data_of_iso = data_br_para_iso(r_of["Data"])
        if chave not in idx_projeto:
            item = {
                "ano": chave[0], "numero": chave[1], "data": r_of["Data"],
                "situacao": r_of["Situacao"], "autores": r_of["Autores"],
                "ementa": r_of["Ementa"],
            }
            if ultima_data and data_of_iso and data_of_iso <= ultima_data:
                faltando_no_projeto_dentro_periodo.append(item)
            else:
                faltando_no_projeto_fora_periodo.append(item)
            continue

        for r_proj in idx_projeto[chave]:
            nomes_oficial = set(n.lower() for n in normalizar_nomes(r_of["Autores"]))
            nomes_projeto = set(n.strip().lower() for n in (r_proj.get("Vereador") or "").split(",") if n.strip())
            autores_batem = bool(nomes_oficial & nomes_projeto) or not nomes_oficial or not nomes_projeto
            if not autores_batem:
                divergencias.append({
                    "ano": chave[0], "numero": chave[1],
                    "tipo": "Autoria diferente",
                    "id_projeto": r_proj.get("ID"),
                    "vereador_projeto": r_proj.get("Vereador"),
                    "autores_oficial": r_of["Autores"],
                    "resumo_projeto": r_proj.get("Resumo", "")[:200],
                    "ementa_oficial": r_of["Ementa"][:200],
                    "data_oficial": r_of["Data"],
                    "data_sessao_projeto": r_proj.get("Data_Sessao"),
                })

    for chave, lista in idx_projeto.items():
        if not chave[1] or chave[1] == "0":
            continue
        if chave not in idx_oficial:
            for r_proj in lista:
                so_no_projeto.append({
                    "ano": chave[0], "numero": chave[1],
                    "id_projeto": r_proj.get("ID"),
                    "vereador_projeto": r_proj.get("Vereador"),
                    "resumo_projeto": r_proj.get("Resumo", "")[:250],
                    "data_sessao_projeto": r_proj.get("Data_Sessao"),
                    "observacoes_projeto": r_proj.get("Observacoes", ""),
                })

    faltando_no_projeto_dentro_periodo.sort(key=lambda x: (x["ano"], int(x["numero"])))
    faltando_no_projeto_fora_periodo.sort(key=lambda x: (x["ano"], int(x["numero"])))
    so_no_projeto.sort(key=lambda x: (x["ano"], int(x["numero"]) if x["numero"].isdigit() else 0))

    resultado = {
        "categoria": nome_categoria,
        "total_projeto": len(projeto),
        "total_oficial": len(oficial),
        "ultima_data_coberta": ultima_data,
        "divergencias_autoria": divergencias,
        "faltando_no_projeto_dentro_periodo": faltando_no_projeto_dentro_periodo,
        "faltando_no_projeto_fora_periodo": faltando_no_projeto_fora_periodo,
        "so_no_projeto_sem_correspondencia_oficial": so_no_projeto,
    }

    print(f"  Total projeto: {len(projeto)} | Total oficial: {len(oficial)}")
    print(f"  Divergências de autoria: {len(divergencias)}")
    print(f"  Faltando no projeto (dentro do período coberto): {len(faltando_no_projeto_dentro_periodo)}")
    print(f"  Faltando no projeto (fora do período coberto / sessão futura): {len(faltando_no_projeto_fora_periodo)}")
    print(f"  Só no projeto, sem correspondência oficial: {len(so_no_projeto)}")
    print()
    return resultado


def main():
    resultado_ind = cruzar("Indicações", "Numero_Indicacao", "indicacoes.csv", "oficial_indicacoes.csv")
    resultado_req = cruzar("Requerimentos", "Numero_Requerimento", "requerimentos.csv", "oficial_requerimentos.csv")

    saida = {"indicacoes": resultado_ind, "requerimentos": resultado_req}
    caminho_saida = os.path.join(DATA_DIR, "cruzamento_site_oficial.json")
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    print(f"Relatório salvo em: {caminho_saida}")


if __name__ == "__main__":
    main()
