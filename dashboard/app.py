"""Painel de acompanhamento das receitas e despesas do Estado de Mato Grosso do Sul.

Execute com:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Painel Fiscal MS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

from ms_fiscal import ui  # noqa: E402
from ms_fiscal.config import LRF_URL, MCASP_URL, SICONFI_DOCS  # noqa: E402
from paginas import (despesas, fontes, fornecedores, rgf, rreo, receitas, tempo_real,  # noqa: E402
                     transferencias, visao_geral)

paginas = {
    "Painel": [
        st.Page(visao_geral.render, title="Visão geral", icon="🏠", url_path="visao-geral", default=True),
        st.Page(tempo_real.render, title="Tempo real (portal)", icon="⏱️", url_path="tempo-real"),
    ],
    "Execução orçamentária": [
        st.Page(receitas.render, title="Receitas", icon="💰", url_path="receitas"),
        st.Page(despesas.render, title="Despesas", icon="🧾", url_path="despesas"),
        st.Page(fornecedores.render, title="Órgãos e fornecedores", icon="🏢", url_path="fornecedores"),
        st.Page(transferencias.render, title="Transferências", icon="🔁", url_path="transferencias"),
    ],
    "Relatórios da LRF": [
        st.Page(rreo.render, title="RREO (bimestral)", icon="📑", url_path="rreo"),
        st.Page(rgf.render, title="RGF (quadrimestral)", icon="⚖️", url_path="rgf"),
    ],
    "Sobre": [st.Page(fontes.render, title="Fontes e metodologia", icon="📚", url_path="fontes")],
}
nav = st.navigation(paginas)

COLETAS = [  # (rótulo, argumentos do coletar.py, duração, precisa do Playwright)
    ("IPCA (IBGE)", ["--ipca"], "≈10 s", False),
    ("Siconfi de MS: MSC, RREO e RGF", ["--siconfi"], "≈1–3 min", False),
    ("RREO de todas as UFs (Siconfi)", ["--rreo-estados"], "≈1–5 min (incremental)", False),
    ("RGF de todas as UFs (Siconfi)", ["--rgf-estados"], "≈2–5 min (incremental)", False),
    ("Dados abertos de MS: credores e repasses", ["--credores", "--repasses"], "≈1–3 min", False),
    ("Portal da Transparência (diário)", ["--portal"], "≈2–4 min", True),
]


def _coletar(rotulo: str, args: list[str], duracao: str) -> None:
    with st.spinner(f"Atualizando {rotulo} ({duracao})…"):
        rc, log = ui.executar_coleta(args)
    st.session_state["ultima_coleta"] = (rotulo, rc, log)
    st.cache_data.clear()
    st.cache_resource.clear()


with st.sidebar:
    st.markdown("### Painel Fiscal · MS")
    tem_ipca = not ui.ipca().empty
    st.toggle("Valores reais (IPCA)", key="valores_reais", disabled=not tem_ipca,
              help="Corrige os valores mensais pelo IPCA (IBGE, tabela 1737, número-índice) até o último mês "
                   "divulgado. Vale para os gráficos e tabelas com valores mensais; meses ainda sem IPCA ficam a "
                   "preços correntes." + ("" if tem_ipca else " Baixe o IPCA em 'Atualizar dados'."))
    if st.session_state.get("valores_reais"):
        st.caption(ui.legenda_valores())
    with st.expander("🔄 Atualizar dados", expanded=False):
        st.caption("Cada botão roda `coletar.py` com a fonte indicada e grava os arquivos Parquet em `dados/dashboard/`.")
        if ui.em_nuvem():
            st.caption("⚠️ No Streamlit Cloud o disco é temporário: os dados baixados valem até o app reiniciar. "
                       "Para torná-los permanentes, rode a coleta localmente e faça commit dos Parquet.")
        pw = ui.playwright_disponivel()
        for rotulo, args, duracao, precisa_pw in COLETAS:
            if st.button(rotulo, width="stretch", disabled=precisa_pw and not pw, key=f"btn_{args[0]}",
                         help=f"python coletar.py {' '.join(args)} · {duracao}" +
                              ("" if pw or not precisa_pw else " · indisponível: falta o Chromium do Playwright "
                               "(python -m playwright install chromium)")):
                _coletar(rotulo, args, duracao)
        if st.button("Todas as fontes", width="stretch", key="btn_tudo",
                     help="python coletar.py --tudo (o portal só se o Playwright estiver disponível)"):
            args = ["--tudo"] if pw else ["--ipca", "--siconfi", "--rreo-estados", "--rgf-estados", "--credores", "--repasses"]
            _coletar("todas as fontes", args, "vários minutos")
        if "ultima_coleta" in st.session_state:
            rotulo, rc, log = st.session_state["ultima_coleta"]
            (st.success if rc == 0 else st.error)(f"{rotulo}: " + ("concluído." if rc == 0 else "falhou (veja o log)."))
            with st.popover("Log da última coleta", width="stretch"):
                st.code(log[-3000:])
    st.markdown(
        f"<small>Referências: [MCASP]({MCASP_URL}) · [LRF]({LRF_URL}) · [API Siconfi]({SICONFI_DOCS})</small>",
        unsafe_allow_html=True)

nav.run()
