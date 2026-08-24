import hmac
import time

import plotly.express as px
import streamlit as st

from sheets_utils import carregar_dataframe, salvar_dataframe, COLUNAS_REQ, ABA_REQ, COLUNAS_DEN, ABA_DEN

MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_SEGUNDOS = 60

STATUS_OPCOES = ["Atendida", "Não Atendida", "Em Andamento", "Pendente de Análise"]
STATUS_CORES = {
    "Atendida": "#16A34A",
    "Não Atendida": "#DC2626",
    "Em Andamento": "#D97706",
    "Pendente de Análise": "#4B5563",
}
SETOR_OPCOES = [
    "Obras e Serviços Públicos", "Trânsito e Mobilidade", "Saúde", "Educação",
    "Meio Ambiente", "Esporte e Lazer", "Administração e Finanças",
    "Agricultura e Meio Rural", "A Classificar",
]

STATUS_RESP_OPCOES = ["Respondido", "Não Respondido", "Parcialmente Respondido", "Pendente"]
STATUS_RESP_CORES = {
    "Respondido": "#16A34A",
    "Não Respondido": "#DC2626",
    "Parcialmente Respondido": "#D97706",
    "Pendente": "#4B5563",
}
RESULTADO_VOTACAO_OPCOES = ["Aprovado", "Rejeitado", "Retirado"]

STATUS_ACOMP_OPCOES = ["Pendente de Verificação", "Em Apuração", "Resolvida/Providenciada", "Sem Encaminhamento"]
STATUS_ACOMP_CORES = {
    "Pendente de Verificação": "#4B5563",
    "Em Apuração": "#D97706",
    "Resolvida/Providenciada": "#16A34A",
    "Sem Encaminhamento": "#6B7280",
}

st.set_page_config(page_title="Painel Legislativo - Junqueirópolis", layout="wide")


def explode_vereador(df: "pd.DataFrame") -> "pd.DataFrame":
    exp = df.assign(Vereador=df["Vereador"].str.split(",")).explode("Vereador")
    exp["Vereador"] = exp["Vereador"].str.strip()
    return exp[exp["Vereador"] != ""]


def filtrar_por_busca(df: "pd.DataFrame", termo: str, colunas: list) -> "pd.DataFrame":
    """Filtra as linhas cujo termo apareça em qualquer uma das colunas indicadas
    (busca por substring, sem diferenciar maiúsculas/minúsculas)."""
    termo = (termo or "").strip().lower()
    if not termo:
        return df
    blob = df[colunas].astype(str).agg(" ".join, axis=1).str.lower()
    return df[blob.str.contains(termo, regex=False, na=False)]


if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False
if "login_tentativas" not in st.session_state:
    st.session_state.login_tentativas = 0
if "login_bloqueado_ate" not in st.session_state:
    st.session_state.login_bloqueado_ate = 0.0

st.title("📋 Painel Legislativo — Câmara de Junqueirópolis")
st.caption("Acompanhamento de indicações e requerimentos apresentados pelos vereadores, e das respostas do Executivo")

with st.sidebar:
    if st.session_state.modo_edicao:
        with st.popover("🔓 Edição"):
            st.success("Edição liberada.")
            if st.button("Sair do modo edição"):
                st.session_state.modo_edicao = False
                st.rerun()
    else:
        with st.popover("🔒 Edição"):
            segundos_restantes = st.session_state.login_bloqueado_ate - time.time()
            if segundos_restantes > 0:
                st.error(f"Muitas tentativas incorretas. Tente novamente em {int(segundos_restantes) + 1}s.")
            else:
                with st.form("form_login", border=False):
                    senha = st.text_input("Senha", type="password")
                    entrar = st.form_submit_button("Entrar")
                if entrar:
                    if senha and hmac.compare_digest(senha, st.secrets.get("senha_admin", "")):
                        st.session_state.modo_edicao = True
                        st.session_state.login_tentativas = 0
                        st.rerun()
                    else:
                        st.session_state.login_tentativas += 1
                        if st.session_state.login_tentativas >= MAX_TENTATIVAS_LOGIN:
                            st.session_state.login_bloqueado_ate = time.time() + BLOQUEIO_SEGUNDOS
                            st.session_state.login_tentativas = 0
                            st.rerun()
                        else:
                            st.error("Senha incorreta.")

aba_indicacoes, aba_requerimentos, aba_diversos = st.tabs(["📋 Indicações", "📑 Requerimentos", "🗂️ Diversos"])


# ----------------------------------------------------------------------------
# ABA: INDICAÇÕES
# ----------------------------------------------------------------------------
with aba_indicacoes:
    if "df_ind" not in st.session_state:
        st.session_state.df_ind = carregar_dataframe()
    df = st.session_state.df_ind

    with st.container(border=True):
        busca_ind = st.text_input("🔍 Buscar por qualquer termo (rua, bairro, vereador, assunto...)", key="ind_busca")
        col1, col2, col3, col4 = st.columns(4)
        anos = sorted(df["Ano"].unique())
        vereadores = sorted({v.strip() for lista in df["Vereador"] for v in lista.split(",") if v.strip()})
        setores = sorted(df["Setor"].unique())

        f_ano = col1.multiselect("Ano", anos, key="ind_ano")
        f_vereador = col2.multiselect("Vereador", vereadores, key="ind_vereador")
        f_setor = col3.multiselect("Setor", setores, key="ind_setor")
        f_status = col4.multiselect("Status de Atendimento", STATUS_OPCOES, key="ind_status")

    filtrado = filtrar_por_busca(df, busca_ind, ["Numero_Indicacao", "Sessao", "Vereador", "Resumo", "Setor", "Observacoes"])
    if f_ano:
        filtrado = filtrado[filtrado["Ano"].isin(f_ano)]
    if f_vereador:
        filtrado = filtrado[filtrado["Vereador"].apply(lambda v: any(nome in v for nome in f_vereador))]
    if f_setor:
        filtrado = filtrado[filtrado["Setor"].isin(f_setor)]
    if f_status:
        filtrado = filtrado[filtrado["Status_Atendimento"].isin(f_status)]

    total = len(filtrado)
    atendidas = (filtrado["Status_Atendimento"] == "Atendida").sum()
    andamento = (filtrado["Status_Atendimento"] == "Em Andamento").sum()
    pendentes_naoatend = filtrado["Status_Atendimento"].isin(["Não Atendida", "Pendente de Análise"]).sum()
    taxa = (atendidas / total * 100) if total else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Indicações", total)
    k2.metric("Taxa de Atendimento", f"{taxa:.1f}%")
    k3.metric("Em Andamento", andamento)
    k4.metric("Não Atendidas / Pendentes", pendentes_naoatend)

    st.divider()

    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Volume por Setor")
        if total:
            contagem_setor = filtrado["Setor"].value_counts().reset_index()
            contagem_setor.columns = ["Setor", "Total"]
            fig = px.bar(contagem_setor.sort_values("Total"), x="Total", y="Setor", orientation="h")
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    with g2:
        st.subheader("Distribuição por Status")
        if total:
            contagem_status = filtrado["Status_Atendimento"].value_counts().reset_index()
            contagem_status.columns = ["Status", "Total"]
            fig = px.pie(contagem_status, names="Status", values="Total", hole=0.55,
                         color="Status", color_discrete_map=STATUS_CORES)
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    st.subheader("Resolutividade por Vereador")
    if total:
        linhas_expandidas = explode_vereador(filtrado)
        resumo_vereador = (
            linhas_expandidas.groupby(["Vereador", "Status_Atendimento"])
            .size()
            .reset_index(name="Total")
        )
        fig = px.bar(
            resumo_vereador, x="Vereador", y="Total", color="Status_Atendimento",
            color_discrete_map=STATUS_CORES, barmode="stack",
        )
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", legend_title="Status")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para os filtros selecionados.")

    st.divider()
    st.subheader("Detalhamento das Indicações")

    colunas_exibicao = ["ID", "Numero_Indicacao", "Ano", "Sessao", "Data_Sessao", "Vereador",
                         "Resumo", "Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]

    if st.session_state.modo_edicao:
        st.caption("Edite diretamente na tabela os campos Setor, Ofício de Resposta, Status e Observações. As alterações são salvas ao clicar em 'Salvar alterações'.")
        with st.form("form_edicao_ind"):
            editado = st.data_editor(
                filtrado[colunas_exibicao],
                key="editor_indicacoes",
                use_container_width=True,
                hide_index=True,
                disabled=["ID", "Numero_Indicacao", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo"],
                column_config={
                    "Setor": st.column_config.SelectboxColumn("Setor", options=SETOR_OPCOES),
                    "Status_Atendimento": st.column_config.SelectboxColumn("Status", options=STATUS_OPCOES),
                    "Oficio_Resposta": st.column_config.TextColumn("Ofício de Resposta"),
                    "Observacoes": st.column_config.TextColumn("Observações", width="large"),
                    "Resumo": st.column_config.TextColumn("Resumo", width="large"),
                },
            )
            salvar = st.form_submit_button("💾 Salvar alterações", type="primary")

        if salvar:
            df_atualizado = st.session_state.df_ind.set_index("ID")
            editado_indexado = editado.set_index("ID")
            for col in ["Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]:
                df_atualizado.loc[editado_indexado.index, col] = editado_indexado[col]
            st.session_state.df_ind = df_atualizado.reset_index()
            salvar_dataframe(st.session_state.df_ind)
            st.success(f"{len(editado_indexado)} indicações atualizadas e salvas na planilha Google Sheets.")
            st.rerun()
    else:
        st.caption("Modo somente leitura. Use \"🔒 Edição\" na barra lateral com a senha de edição para alterar Setor, Ofício, Status ou Observações.")
        st.dataframe(filtrado[colunas_exibicao], use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# ABA: REQUERIMENTOS
# ----------------------------------------------------------------------------
with aba_requerimentos:
    if "df_req" not in st.session_state:
        st.session_state.df_req = carregar_dataframe(aba=ABA_REQ, colunas=COLUNAS_REQ)
    dfr = st.session_state.df_req

    with st.container(border=True):
        busca_req = st.text_input("🔍 Buscar por qualquer termo (rua, bairro, vereador, assunto...)", key="req_busca")
        col1, col2, col3, col4 = st.columns(4)
        anos_r = sorted(dfr["Ano"].unique())
        vereadores_r = sorted({v.strip() for lista in dfr["Vereador"] for v in lista.split(",") if v.strip()})
        diretorias_r = sorted({d for d in dfr["Diretoria_Destino"].unique() if d})

        f_ano_r = col1.multiselect("Ano", anos_r, key="req_ano")
        f_vereador_r = col2.multiselect("Vereador", vereadores_r, key="req_vereador")
        f_diretoria_r = col3.multiselect("Diretoria", diretorias_r, key="req_diretoria")
        f_status_r = col4.multiselect("Status de Resposta", STATUS_RESP_OPCOES, key="req_status")

    filtrado_r = filtrar_por_busca(dfr, busca_req, ["Numero_Requerimento", "Sessao", "Vereador", "Resumo", "Diretoria_Destino", "Observacoes"])
    if f_ano_r:
        filtrado_r = filtrado_r[filtrado_r["Ano"].isin(f_ano_r)]
    if f_vereador_r:
        filtrado_r = filtrado_r[filtrado_r["Vereador"].apply(lambda v: any(nome in v for nome in f_vereador_r))]
    if f_diretoria_r:
        filtrado_r = filtrado_r[filtrado_r["Diretoria_Destino"].isin(f_diretoria_r)]
    if f_status_r:
        filtrado_r = filtrado_r[filtrado_r["Status_Resposta"].isin(f_status_r)]

    total_r = len(filtrado_r)
    respondidos = (filtrado_r["Status_Resposta"] == "Respondido").sum()
    parciais = (filtrado_r["Status_Resposta"] == "Parcialmente Respondido").sum()
    nao_respondidos = filtrado_r["Status_Resposta"].isin(["Não Respondido", "Pendente"]).sum()
    taxa_r = (respondidos / total_r * 100) if total_r else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Requerimentos", total_r)
    k2.metric("Taxa de Resposta", f"{taxa_r:.1f}%")
    k3.metric("Parcialmente Respondidos", parciais)
    k4.metric("Não Respondidos / Pendentes", nao_respondidos)

    st.divider()

    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Volume por Diretoria")
        if total_r:
            contagem_dir = filtrado_r["Diretoria_Destino"].value_counts().reset_index()
            contagem_dir.columns = ["Diretoria", "Total"]
            fig = px.bar(contagem_dir.sort_values("Total"), x="Total", y="Diretoria", orientation="h")
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    with g2:
        st.subheader("Distribuição por Status de Resposta")
        if total_r:
            contagem_status_r = filtrado_r["Status_Resposta"].value_counts().reset_index()
            contagem_status_r.columns = ["Status", "Total"]
            fig = px.pie(contagem_status_r, names="Status", values="Total", hole=0.55,
                         color="Status", color_discrete_map=STATUS_RESP_CORES)
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    st.subheader("Requerimentos por Vereador")
    if total_r:
        linhas_expandidas_r = explode_vereador(filtrado_r)
        resumo_vereador_r = (
            linhas_expandidas_r.groupby(["Vereador", "Status_Resposta"])
            .size()
            .reset_index(name="Total")
        )
        fig = px.bar(
            resumo_vereador_r, x="Vereador", y="Total", color="Status_Resposta",
            color_discrete_map=STATUS_RESP_CORES, barmode="stack",
        )
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", legend_title="Status")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para os filtros selecionados.")

    st.divider()
    st.subheader("Detalhamento dos Requerimentos")

    colunas_exibicao_r = ["ID", "Numero_Requerimento", "Ano", "Sessao", "Data_Sessao", "Vereador",
                           "Resumo", "Diretoria_Destino", "Resultado_Votacao", "Oficio_Resposta",
                           "Status_Resposta", "Observacoes"]

    if st.session_state.modo_edicao:
        st.caption("Edite diretamente na tabela os campos Diretoria, Resultado da Votação, Ofício de Resposta, Status e Observações. As alterações são salvas ao clicar em 'Salvar alterações'.")
        with st.form("form_edicao_req"):
            editado_r = st.data_editor(
                filtrado_r[colunas_exibicao_r],
                key="editor_requerimentos",
                use_container_width=True,
                hide_index=True,
                disabled=["ID", "Numero_Requerimento", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo"],
                column_config={
                    "Diretoria_Destino": st.column_config.TextColumn("Diretoria"),
                    "Resultado_Votacao": st.column_config.SelectboxColumn("Resultado da Votação", options=RESULTADO_VOTACAO_OPCOES),
                    "Oficio_Resposta": st.column_config.TextColumn("Ofício de Resposta"),
                    "Status_Resposta": st.column_config.SelectboxColumn("Status", options=STATUS_RESP_OPCOES),
                    "Observacoes": st.column_config.TextColumn("Observações", width="large"),
                    "Resumo": st.column_config.TextColumn("Resumo", width="large"),
                },
            )
            salvar_r = st.form_submit_button("💾 Salvar alterações", type="primary")

        if salvar_r:
            df_atualizado_r = st.session_state.df_req.set_index("ID")
            editado_r_indexado = editado_r.set_index("ID")
            for col in ["Diretoria_Destino", "Resultado_Votacao", "Oficio_Resposta", "Status_Resposta", "Observacoes"]:
                df_atualizado_r.loc[editado_r_indexado.index, col] = editado_r_indexado[col]
            st.session_state.df_req = df_atualizado_r.reset_index()
            salvar_dataframe(st.session_state.df_req, aba=ABA_REQ, colunas=COLUNAS_REQ)
            st.success(f"{len(editado_r_indexado)} requerimentos atualizados e salvos na planilha Google Sheets.")
            st.rerun()
    else:
        st.caption("Modo somente leitura. Use \"🔒 Edição\" na barra lateral com a senha de edição para alterar Diretoria, Resultado, Ofício, Status ou Observações.")
        st.dataframe(filtrado_r[colunas_exibicao_r], use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# ABA: DIVERSOS (denúncias)
# ----------------------------------------------------------------------------
with aba_diversos:
    st.caption("Menções a denúncias feitas, recebidas ou sofridas pelos vereadores durante as sessões — sem número formal nem votação, ao contrário de Indicações e Requerimentos.")

    if "df_den" not in st.session_state:
        st.session_state.df_den = carregar_dataframe(aba=ABA_DEN, colunas=COLUNAS_DEN)
    dfd = st.session_state.df_den

    with st.container(border=True):
        busca_d = st.text_input("🔍 Buscar por qualquer termo (vereador, assunto, destinatário...)", key="den_busca")
        col1, col2, col3, col4 = st.columns(4)
        anos_d = sorted(dfd["Ano"].unique())
        vereadores_d = sorted({v.strip() for lista in dfd["Vereador"] for v in lista.split(",") if v.strip()})
        direcionadas_d = sorted({d for d in dfd["Direcionada_A"].unique() if d})

        f_ano_d = col1.multiselect("Ano", anos_d, key="den_ano")
        f_vereador_d = col2.multiselect("Vereador", vereadores_d, key="den_vereador")
        f_direcionada_d = col3.multiselect("Direcionada a", direcionadas_d, key="den_direcionada")
        f_status_d = col4.multiselect("Status de Acompanhamento", STATUS_ACOMP_OPCOES, key="den_status")

    filtrado_d = filtrar_por_busca(dfd, busca_d, ["Sessao", "Vereador", "Resumo", "Direcionada_A", "Tipo", "Observacoes"])
    if f_ano_d:
        filtrado_d = filtrado_d[filtrado_d["Ano"].isin(f_ano_d)]
    if f_vereador_d:
        filtrado_d = filtrado_d[filtrado_d["Vereador"].apply(lambda v: any(nome in v for nome in f_vereador_d))]
    if f_direcionada_d:
        filtrado_d = filtrado_d[filtrado_d["Direcionada_A"].isin(f_direcionada_d)]
    if f_status_d:
        filtrado_d = filtrado_d[filtrado_d["Status_Acompanhamento"].isin(f_status_d)]

    total_d = len(filtrado_d)
    resolvidas_d = (filtrado_d["Status_Acompanhamento"] == "Resolvida/Providenciada").sum()
    apuracao_d = (filtrado_d["Status_Acompanhamento"] == "Em Apuração").sum()
    pendentes_d = filtrado_d["Status_Acompanhamento"].isin(["Pendente de Verificação"]).sum()
    taxa_d = (resolvidas_d / total_d * 100) if total_d else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Registros", total_d)
    k2.metric("Taxa de Resolução", f"{taxa_d:.1f}%")
    k3.metric("Em Apuração", apuracao_d)
    k4.metric("Pendentes de Verificação", pendentes_d)

    st.divider()

    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Volume por Destinatário")
        if total_d:
            contagem_dir_d = filtrado_d["Direcionada_A"].value_counts().reset_index()
            contagem_dir_d.columns = ["Direcionada a", "Total"]
            fig = px.bar(contagem_dir_d.sort_values("Total"), x="Total", y="Direcionada a", orientation="h")
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    with g2:
        st.subheader("Distribuição por Status")
        if total_d:
            contagem_status_d = filtrado_d["Status_Acompanhamento"].value_counts().reset_index()
            contagem_status_d.columns = ["Status", "Total"]
            fig = px.pie(contagem_status_d, names="Status", values="Total", hole=0.55,
                         color="Status", color_discrete_map=STATUS_ACOMP_CORES)
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para os filtros selecionados.")

    st.divider()
    st.subheader("Detalhamento")

    colunas_exibicao_d = ["ID", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo",
                           "Direcionada_A", "Tipo", "Status_Acompanhamento", "Observacoes"]

    if st.session_state.modo_edicao:
        st.caption("Edite diretamente na tabela os campos Direcionada a, Status de Acompanhamento e Observações. As alterações são salvas ao clicar em 'Salvar alterações'.")
        with st.form("form_edicao_den"):
            editado_d = st.data_editor(
                filtrado_d[colunas_exibicao_d],
                key="editor_diversos",
                use_container_width=True,
                hide_index=True,
                disabled=["ID", "Ano", "Sessao", "Data_Sessao", "Vereador", "Resumo", "Tipo"],
                column_config={
                    "Direcionada_A": st.column_config.TextColumn("Direcionada a"),
                    "Status_Acompanhamento": st.column_config.SelectboxColumn("Status", options=STATUS_ACOMP_OPCOES),
                    "Observacoes": st.column_config.TextColumn("Observações", width="large"),
                    "Resumo": st.column_config.TextColumn("Resumo", width="large"),
                },
            )
            salvar_d = st.form_submit_button("💾 Salvar alterações", type="primary")

        if salvar_d:
            df_atualizado_d = st.session_state.df_den.set_index("ID")
            editado_d_indexado = editado_d.set_index("ID")
            for col in ["Direcionada_A", "Status_Acompanhamento", "Observacoes"]:
                df_atualizado_d.loc[editado_d_indexado.index, col] = editado_d_indexado[col]
            st.session_state.df_den = df_atualizado_d.reset_index()
            salvar_dataframe(st.session_state.df_den, aba=ABA_DEN, colunas=COLUNAS_DEN)
            st.success(f"{len(editado_d_indexado)} registros atualizados e salvos na planilha Google Sheets.")
            st.rerun()
    else:
        st.caption("Modo somente leitura. Use \"🔒 Edição\" na barra lateral com a senha de edição para alterar Direcionada a, Status ou Observações.")
        st.dataframe(filtrado_d[colunas_exibicao_d], use_container_width=True, hide_index=True)
