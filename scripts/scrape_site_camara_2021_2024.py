"""
Baixa a lista oficial de proposições (Indicações, Requerimentos, Diversos) do
site da Câmara de Junqueirópolis (https://www.cmjunqueiropolis.sp.gov.br/)
para cruzar com os dados extraídos das transcrições.

O site expõe uma busca filtrável em /portal/proposicoes/<pagina>/<tipo>/.../
e um botão "CSV" (csv.php) que exporta a página atual de resultados,
respeitando o filtro salvo na sessão (cookie). Este script itera as páginas
via requests, mantendo a sessão, e concatena tudo em CSVs de referência.

Uso: python scrape_site_camara.py
"""
import csv
import os
import re
import time

import requests

BASE = "https://www.cmjunqueiropolis.sp.gov.br"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# tipo: 3=Indicações, 2=Requerimentos, 20=Diversos (DVS)
# mandato 21 = De: 01/01/2021 Até: 31/12/2024 (18a Legislatura)
TIPOS = {
    "indicacoes_2021_2024": "3",
    "requerimentos_2021_2024": "2",
    "diversos_site_2021_2024": "20",
}
MANDATO = "21"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; painel-legislativo-junqueiropolis/1.0)"}


def _get_com_retry(session, url, tentativas=5, espera=3):
    ultimo_erro = None
    for i in range(tentativas):
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            ultimo_erro = e
            print(f"    (tentativa {i+1}/{tentativas} falhou: {e}; aguardando {espera}s)")
            time.sleep(espera)
    raise ultimo_erro


def buscar_total(session, tipo):
    url = f"{BASE}/portal/proposicoes/1/{tipo}/0/{MANDATO}/0/0/0/0/0/0/0/0/0/"
    r = _get_com_retry(session, url)
    m = re.search(r"(\d+)\s+proposi", r.text)
    return int(m.group(1)) if m else None


def baixar_pagina_csv(session, pagina, tipo):
    url = f"{BASE}/portal/proposicoes/{pagina}/{tipo}/0/{MANDATO}/0/0/0/0/0/0/0/0/0/"
    _get_com_retry(session, url)
    r2 = _get_com_retry(session, f"{BASE}/csv.php")
    r2.encoding = "utf-8"
    return r2.text


CAMPOS_CSV = ["Tipo", "Título", "Ementa", "Data", "Número", "Situação", "Autores"]
TIPO_PREFIXOS = ("IND - ", "REQ - ", "DVS - ")


def parse_csv_text(texto):
    """O CSV do site não tem os campos entre aspas nem escapa caracteres
    especiais dentro da Ementa, então dois problemas aparecem:
    1) um ';' literal na Ementa (ex.: listas numeradas '1) ... 2) ...') cria
       colunas extras no meio da linha;
    2) uma quebra de linha literal na Ementa parte uma linha lógica em duas
       linhas físicas (a segunda sem o prefixo de Tipo).
    Primeiro reconstrói as linhas lógicas (juntando continuações que não
    começam com um Tipo reconhecido), depois recompõe colunas extras de
    volta na Ementa antes de montar o dicionário."""
    linhas_fisicas = [l.rstrip("\r") for l in texto.split("\n") if l.strip()]
    linhas_logicas = []
    for linha in linhas_fisicas:
        if linha.startswith("Tipo;") :
            continue
        if linha.startswith(TIPO_PREFIXOS) or not linhas_logicas:
            linhas_logicas.append(linha)
        else:
            linhas_logicas[-1] = linhas_logicas[-1] + " " + linha.strip()

    linhas = []
    for linha in linhas_logicas:
        partes = linha.split(";")
        if partes and partes[-1] == "":
            partes = partes[:-1]
        if len(partes) < len(CAMPOS_CSV):
            continue
        if len(partes) > len(CAMPOS_CSV):
            n_extra = len(partes) - len(CAMPOS_CSV)
            ementa = ";".join(partes[2:3 + n_extra])
            partes = partes[:2] + [ementa] + partes[3 + n_extra:]
        linhas.append(dict(zip(CAMPOS_CSV, partes)))
    return linhas


def coletar_tipo(nome, tipo):
    session = requests.Session()
    total = buscar_total(session, tipo)
    print(f"{nome}: {total} proposições encontradas no site")

    registros = []
    vistos = set()
    pagina = 1
    paginas_vazias_seguidas = 0
    while True:
        texto = baixar_pagina_csv(session, pagina, tipo)
        linhas = parse_csv_text(texto)
        linhas = [l for l in linhas if l.get("Número")]
        if not linhas:
            paginas_vazias_seguidas += 1
            if paginas_vazias_seguidas >= 2:
                break
        else:
            paginas_vazias_seguidas = 0
        novos = 0
        for l in linhas:
            chave = l.get("Número", "")
            if chave in vistos:
                continue
            vistos.add(chave)
            registros.append(l)
            novos += 1
        print(f"  página {pagina}: {len(linhas)} linhas, {novos} novas (total acumulado: {len(registros)})")
        if novos == 0 and pagina > 1:
            break
        if total is not None and len(registros) >= total:
            break
        pagina += 1
        time.sleep(0.3)
        if pagina > 30:
            print("  aviso: parando em 30 páginas por segurança")
            break

    return registros, total


def normalizar_numero_ano(numero_str):
    m = re.match(r"(\d+)\s*/\s*(\d{4})", numero_str or "")
    if not m:
        return "", ""
    return m.group(1).zfill(3), m.group(2)


def salvar_csv(registros, caminho):
    campos = ["Numero", "Ano", "Data", "Situacao", "Autores", "Ementa", "Titulo"]
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in registros:
            numero, ano = normalizar_numero_ano(r.get("Número", ""))
            writer.writerow({
                "Numero": numero,
                "Ano": ano,
                "Data": r.get("Data", ""),
                "Situacao": r.get("Situação", ""),
                "Autores": r.get("Autores", ""),
                "Ementa": r.get("Ementa", ""),
                "Titulo": r.get("Título", ""),
            })
    print(f"Salvo: {caminho} ({len(registros)} registros)")


def main():
    for nome, tipo in TIPOS.items():
        registros, total = coletar_tipo(nome, tipo)
        caminho = os.path.join(OUT_DIR, f"oficial_{nome}.csv")
        salvar_csv(registros, caminho)
        if total is not None and len(registros) != total:
            print(f"  AVISO: coletados {len(registros)} != total anunciado pelo site {total}")
        print()


if __name__ == "__main__":
    main()
