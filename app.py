import plotly.express as px
import streamlit as st

from sheets_utils import carregar_dataframe, salvar_dataframe

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

st.set_page_config(page_title="Indicações Legislativas - Junqueirópolis", layout="wide")


if "df" not in st.session_state:
    st.session_state.df = carregar_dataframe()

df = st.session_state.df

st.title("📋 Painel de Indicações Legislativas")
st.caption("Câmara Municipal de Junqueirópolis/SP — acompanhamento de indicações e respostas do Executivo")

if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False

with st.sidebar:
    st.subheader("🔒 Modo edição")
    if st.session_state.modo_edicao:
        st.success("Edição liberada.")
        if st.button("Sair do modo edição"):
            st.session_state.modo_edicao = False
            st.rerun()
    else:
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == st.secrets.get("senha_admin", ""):
                st.session_state.modo_edicao = True
                st.rerun()
            else:
                st.error("Senha incorreta.")

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    anos = sorted(df["Ano"].unique())
    vereadores = sorted({v.strip() for lista in df["Vereador"] for v in lista.split(",") if v.strip()})
    setores = sorted(df["Setor"].unique())

    f_ano = col1.multiselect("Ano", anos)
    f_vereador = col2.multiselect("Vereador", vereadores)
    f_setor = col3.multiselect("Setor", setores)
    f_status = col4.multiselect("Status de Atendimento", STATUS_OPCOES)

filtrado = df.copy()
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
    linhas_expandidas = filtrado.assign(
        Vereador=filtrado["Vereador"].str.split(",")
    ).explode("Vereador")
    linhas_expandidas["Vereador"] = linhas_expandidas["Vereador"].str.strip()
    linhas_expandidas = linhas_expandidas[linhas_expandidas["Vereador"] != ""]

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
    with st.form("form_edicao"):
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
        df_atualizado = st.session_state.df.set_index("ID")
        editado_indexado = editado.set_index("ID")
        for col in ["Setor", "Oficio_Resposta", "Status_Atendimento", "Observacoes"]:
            df_atualizado.loc[editado_indexado.index, col] = editado_indexado[col]
        st.session_state.df = df_atualizado.reset_index()
        salvar_dataframe(st.session_state.df)
        st.success(f"{len(editado_indexado)} indicações atualizadas e salvas na planilha Google Sheets.")
        st.rerun()
else:
    st.caption("Modo somente leitura. Use \"🔒 Modo edição\" na barra lateral com a senha de edição para alterar Setor, Ofício, Status ou Observações.")
    st.dataframe(filtrado[colunas_exibicao], use_container_width=True, hide_index=True)
