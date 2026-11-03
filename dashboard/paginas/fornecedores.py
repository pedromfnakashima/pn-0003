"""Órgãos e fornecedores: despesa por credor (dados abertos SEFAZ-MS) e mês corrente (portal)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import ui

ESTAGIOS = {"Pago": "pago", "Liquidado": "liquidado", "Empenhado": "empenhado"}
PF = "Pessoas físicas (nomes omitidos)"


def _anonimizar(df: pd.DataFrame, mostrar_pf: bool) -> pd.DataFrame:
    if mostrar_pf:
        return df
    df = df.copy()
    pf = df["tipo_credor"].astype(str) == "Pessoa física"
    df["credor"] = df["credor"].astype(str).where(~pf, PF)
    df["cpf_cnpj"] = df["cpf_cnpj"].astype(str).where(~pf, "***")
    return df


def _origem_filtros(df: pd.DataFrame) -> None:
    meses = df[["ano", "mes"]].drop_duplicates().sort_values(["ano", "mes"])
    ini, fim = meses.iloc[0], meses.iloc[-1]
    periodo = f"{int(ini['mes']):02d}/{int(ini['ano'])} a {int(fim['mes']):02d}/{int(fim['ano'])}"
    with st.expander("ℹ️ De onde vêm as opções dos filtros", expanded=False):
        st.markdown(f"""
**Fonte.** Todas as opções vêm de colunas de um arquivo CSV de dados abertos, não de planilha, de lista fixa ou de
endpoint de API. Alguns filtros são valores fixos ou classificações calculadas pelo painel (ver tabela).

**Do arquivo ao filtro**
1. **Coleta** (`python coletar.py --credores`): baixa um arquivo por mês, `despesas-MM_AAAA.csv`, do conjunto
   [Despesas por Credor – Mensal](https://www.dados.ms.gov.br/dataset/despesas-por-credor-mensal) (SEFAZ-MS), no
   portal de dados abertos dados.ms.gov.br (CKAN).
2. **Conteúdo do CSV**: uma linha por empenho e credor, separada por `;`, com as colunas `Orgão`, `Natureza de Despesa`,
   `Programa`, `Função`, `Sub-Função`, `Ação`, `Categoria`, `Grupo de Despesa`, `Modalidade`, `Elemento de Despesa`,
   `Cpf/Cnpj`, `Credor`, `Documento`, `Tipo de Licitação`, `Empenhado`, `Liquidado`, `Pago`.
3. **Limpeza**: o painel corrige espaços, aspas e registros quebrados, completa nomes cortados e grava cada mês em
   `dados/dashboard/credor_AAAA_MM.parquet`.
4. **Montagem das opções**: a página junta todos os meses carregados ({len(meses)} meses, de {periodo}). Cada filtro
   de múltipla escolha lista os **valores distintos** da coluna, em ordem alfabética.

**Filtro por filtro**

| Filtro | Origem das opções |
|---|---|
| Exercícios | Coluna `ano`. O ano não está no CSV: vem do nome do arquivo (`despesas-09_2026.csv` → 2026). |
| Meses | Lista fixa, de janeiro a dezembro. |
| Valor | Fixo. Escolhe qual coluna do CSV é somada: `Pago`, `Liquidado` ou `Empenhado`. |
| Só fornecedores | **Calculado pelo painel**: credor do tipo empresa ou entidade privada **e** elemento de bens, serviços ou obras (material de consumo, serviços de terceiros PJ, obras, equipamentos, TI, locação de mão de obra…). |
| Mostrar nomes de PF | Só muda a exibição. Por padrão, os nomes de pessoas físicas ficam agregados. |
| Órgão | Coluna `Orgão` do CSV. |
| Função | Coluna `Função` do CSV. Quando vem vazia, aparece como "(não informada)". |
| Elemento de despesa | Coluna `Elemento de Despesa` do CSV. |
| Modalidade de aplicação | Coluna `Modalidade` do CSV. |
| Tipo de licitação | Coluna `Tipo de Licitação` do CSV. Quando vem vazia, aparece como "(não informado)". |
| Tipo de credor | **Calculado pelo painel**, não existe no CSV. Usa o formato do `Cpf/Cnpj` (CPF mascarado, CNPJ, estrangeiro, rubricas "PF/PJ") e palavras do nome do credor (PREFEITURA, BANCO, FUNDO…). É aproximado. |
| Credor ou CNPJ contém | Texto livre, procurado nas colunas `Credor` e `Cpf/Cnpj`. |

**Cuidados**
- **Grafia da fonte**: as opções seguem a grafia da SEFAZ, com maiúsculas e minúsculas misturadas e acentos faltando.
  O painel corrige erros de digitação conhecidos e une nomes de elementos alterados em 2026, como "Pensões" e
  "Pensões do RPPS e do Militar".
- **Nomes cortados**: a fonte corta os textos em 80 caracteres. Quando o nome oficial é conhecido (MCASP), o painel o
  completa; nos demais casos, acrescenta "…".
- **Opções independentes**: as opções não mudam com os outros filtros. Uma escolha (por exemplo, um órgão sem
  movimento no exercício selecionado) pode não retornar dados.
- **Sem códigos**: o CSV traz só os nomes de função, elemento e modalidade, porque a coluna `Natureza de Despesa` vem
  vazia. Por isso as opções não podem ser conferidas automaticamente contra as tabelas do MCASP.
- **Meses de 05 a 08/2025**: foram publicados com campos entre aspas duplicadas e quebras de linha fora das aspas, o
  que deslocava as colunas. O painel recompõe esses registros e recusa, na coleta, meses que continuem com colunas
  deslocadas.
""")
        ui.fonte("ckan_credores", nota="valores distintos das colunas listadas acima, em todos os meses carregados")


def render():
    st.title("Órgãos e fornecedores")
    st.caption("Pagamentos por órgão e por credor, com classificação funcional e por natureza (elemento e modalidade), "
               "a partir do conjunto Despesas por Credor – Mensal (SEFAZ-MS) e, para o mês corrente, do Portal da Transparência.")
    ui.base_legal(["despesa_institucional", "despesa_natureza", "despesa_estagios"], ["art48", "art48a"],
                  extra=["Modalidades de licitação: Lei nº 14.133/2021 (pregão, concorrência, dispensa, inexigibilidade etc.).",
                         "Classificação do credor (empresa, ente público, financeira, pessoa física) feita pelo painel a partir "
                         "do CPF/CNPJ e do nome: é aproximada e serve para filtrar."])
    df = ui.credores()
    if df.empty:
        ui.sem_dados("despesas por credor", "python coletar.py --credores")
        return
    df = ui.ajustar(df, ["empenhado", "liquidado", "pago"])
    _origem_filtros(df)

    f = st.columns([1.2, 1.3, 1.3, 1.2, 1.2])
    anos = sorted(df["ano"].unique())
    sel_anos = f[0].multiselect("Exercícios", anos, default=anos[-1:], key="fn_anos")
    m_ini, m_fim = f[1].select_slider("Meses", list(range(1, 13)), value=(1, 12), format_func=lambda m: G.MESES[m - 1], key="fn_meses")
    est_nome = f[2].radio("Valor", list(ESTAGIOS), horizontal=True, key="fn_est",
                          help="O arquivo mensal registra o movimento do mês em cada estágio; 'Pago' corresponde ao pagamento efetivo.")
    so_forn = f[3].toggle("Só fornecedores", value=True, key="fn_forn",
                          help="Empresas e entidades privadas em elementos de bens, serviços e obras (material de consumo, "
                               "serviços de terceiros PJ, obras, equipamentos, TI, locação de mão de obra, contratos de gestão…).")
    mostrar_pf = f[4].toggle("Mostrar nomes de PF", value=False, key="fn_pf",
                             help="Por padrão, pessoas físicas aparecem agregadas (proteção de dados pessoais).")
    f2 = st.columns(4)
    orgaos = ui.filtro_multiplo(f2[0], "Órgão", df["orgao"], "fn_org")
    funcoes = ui.filtro_multiplo(f2[1], "Função", df["funcao"], "fn_fun")
    elementos = ui.filtro_multiplo(f2[2], "Elemento de despesa", df["elemento"], "fn_el")
    tipos = ui.filtro_multiplo(f2[3], "Tipo de credor", df["tipo_credor"], "fn_tipo")
    f3 = st.columns([2, 2, 1])
    modal = ui.filtro_multiplo(f3[0], "Modalidade de aplicação", df["modalidade"], "fn_mod")
    licit = ui.filtro_multiplo(f3[1], "Tipo de licitação", df["licitacao"].astype(str).replace("", "(não informado)"), "fn_lic")
    busca = f3[2].text_input("Credor ou CNPJ contém", key="fn_busca")

    est = ESTAGIOS[est_nome]
    d = df[df["ano"].isin(sel_anos) & df["mes"].between(m_ini, m_fim)]
    if so_forn:
        d = d[d["fornecedor"]]
    for col, sel in (("orgao", orgaos), ("funcao", funcoes), ("elemento", elementos), ("tipo_credor", tipos), ("modalidade", modal)):
        d = ui.aplicar_filtro(d, col, sel)
    if licit:
        d = d[d["licitacao"].astype(str).replace("", "(não informado)").isin(licit)]
    if busca:
        d = d[d["credor"].astype(str).str.contains(busca, case=False, na=False) | d["cpf_cnpj"].astype(str).str.contains(busca, regex=False)]
    if d.empty:
        st.warning("Nenhum dado para os filtros escolhidos.")
        return
    d = _anonimizar(d, mostrar_pf)

    tot = d[est].sum()
    per = ui.periodo(d)
    nota_ck = f"arquivos mensais despesas-MM_AAAA.csv; soma de {per}"
    st.caption(f"Período: **{per}**. Totais, rankings e percentuais somam esses meses; \"% do total\" é a parte no "
               f"total {est_nome.lower()} do recorte filtrado ({G.brl(tot)}).".replace("$", "\\$"))
    c = st.columns(4)
    fc = ui.ajuda_fontes("ckan_credores")
    c[0].metric(f"Total {est_nome.lower()} no período", G.brl(tot), help=f"{per}.\n\n{fc}")
    c[1].metric("Credores distintos", f"{d['cpf_cnpj'].nunique():,}".replace(",", "."), help=fc)
    c[2].metric("Órgãos", d["orgao"].nunique(), help=fc)
    c[3].metric("Empenhos (linhas)", f"{len(d):,}".replace(",", "."), help=fc)

    abas = st.tabs(["🏛️ Órgãos", "🏢 Ranking de credores", "🔎 Ficha do credor", "🧾 Elemento e licitação", "📆 Mês corrente (portal)"])

    with abas[0]:
        o = d.groupby("orgao", as_index=False, observed=True)[["empenhado", "liquidado", "pago"]].sum()
        o = o.sort_values(est, ascending=False)
        n = st.slider("Órgãos no gráfico", 5, 40, 15, key="fn_org_n")
        ui.grafico(G.barras(o.head(n), "orgao", est, horizontal=True, altura=max(380, 26 * n),
                                 titulo=f"Despesa ({est_nome.lower()}) por órgão"), "fn_org_bar", "ckan_credores",
                   nota=nota_ck)
        om = d.groupby(["ano", "mes", "orgao"], as_index=False, observed=True)[est].sum()
        om["data"] = pd.to_datetime(dict(year=om["ano"], month=om["mes"], day=1))
        om = G.top_n_outros(om, "orgao", est, 7).groupby(["data", "orgao"], as_index=False)[est].sum()
        ui.grafico(G.barras(om, "data", est, "orgao", "Evolução mensal – maiores órgãos"), "fn_org_mes", "ckan_credores",
                   nota=nota_ck)
        o["% do total"] = o[est] / tot * 100 if tot else 0
        ui.tabela(o, "fn_org_tab", 
                  fontes=["ckan_credores"], nota=nota_ck,
                  moeda=["empenhado", "liquidado", "pago"], pct=["% do total"], ordenar_padrao=est)

    with abas[1]:
        chave = st.radio("Agrupar credor por", ["CNPJ/CPF", "Raiz do CNPJ (empresa)", "Nome"], horizontal=True, key="fn_chave",
                         help="A raiz do CNPJ (8 primeiros dígitos) une matriz e filiais da mesma empresa.")
        k = {"CNPJ/CPF": "cpf_cnpj", "Raiz do CNPJ (empresa)": "cnpj_raiz", "Nome": "credor"}[chave]
        dd = d.copy()
        if k == "cnpj_raiz":
            dd["cnpj_raiz"] = dd["cnpj_raiz"].where(dd["cnpj_raiz"] != "", dd["cpf_cnpj"])
        r = dd.groupby(k, as_index=False).agg(credor=("credor", "first"), tipo=("tipo_credor", "first"),
                                              orgaos=("orgao", "nunique"), empenhos=("empenho", "nunique"),
                                              empenhado=("empenhado", "sum"), liquidado=("liquidado", "sum"), pago=("pago", "sum"))
        r = r.sort_values(est, ascending=False)
        r["% do total"] = r[est] / tot * 100 if tot else 0
        r["% acumulado"] = r["% do total"].cumsum()
        c1, c2, c3, c4 = st.columns(4)
        for col, nn in zip((c1, c2, c3), (5, 10, 100)):
            col.metric(f"Participação dos {nn} maiores", G.pct(r[est].head(nn).sum() / tot * 100 if tot else 0))
        hhi = ((r[est].clip(lower=0) / r[est].clip(lower=0).sum()) ** 2).sum() * 10_000 if tot else 0
        c4.metric("Índice HHI", f"{hhi:,.0f}".replace(",", "."),
                  help="Herfindahl-Hirschman: < 1.500 baixa concentração; > 2.500 alta.\n\n" + fc)
        g1, g2 = st.columns([3, 2])
        fig, _ = G.pareto(r.assign(rot=r["credor"].astype(str).str.slice(0, 45)), "rot", est, "30 maiores credores", n=30)
        ui.grafico(fig, "fn_pareto", "ckan_credores", onde=g1,
                   nota=nota_ck)
        curva = r.head(200).reset_index(drop=True).assign(posição=lambda z: z.index + 1)
        fc = G.linhas(curva, "posição", "% acumulado", titulo="Curva de concentração (200 maiores)", marcadores=False, moeda=False)
        fc.update_yaxes(ticksuffix="%", range=[0, 100])
        fc.update_xaxes(title="nº de credores, do maior para o menor")
        ui.grafico(fc, "fn_curva", "ckan_credores", onde=g2,
                   nota=nota_ck)
        ui.tabela(r, "fn_rank", 
                  fontes=["ckan_credores"], nota=nota_ck,
                  moeda=["empenhado", "liquidado", "pago"], pct=["% do total", "% acumulado"], ordenar_padrao=est)

    with abas[2]:
        opcoes = (d.groupby(["cpf_cnpj", "credor"], as_index=False)[est].sum().sort_values(est, ascending=False))
        opcoes = opcoes[opcoes["credor"] != PF]
        if opcoes.empty:
            st.caption("Nenhum credor identificável nos filtros.")
        else:
            rot = (opcoes["credor"].astype(str) + " · " + opcoes["cpf_cnpj"].astype(str)).tolist()
            esc = st.selectbox("Credor", rot, key="fn_ficha")
            doc = esc.rsplit(" · ", 1)[1]
            x = df[(df["cpf_cnpj"] == doc)]
            x = x[x["ano"].isin(sel_anos)]
            xm = x.groupby(["ano", "mes"], as_index=False)[["empenhado", "liquidado", "pago"]].sum()
            xm["data"] = pd.to_datetime(dict(year=xm["ano"], month=xm["mes"], day=1))
            xl = xm.melt(["data"], ["empenhado", "liquidado", "pago"], var_name="estágio", value_name="R$")
            c1, c2 = st.columns([3, 2])
            ui.grafico(G.barras(xl, "data", "R$", "estágio", "Movimento mensal do credor", empilhar=False,
                                     cores=G.ESTAGIOS), "fn_ficha_m", "ckan_credores", onde=c1,
                   nota=f"arquivos mensais despesas-MM_AAAA.csv, todos os meses de {ui.periodo(x)}: a ficha ignora o filtro Meses")
            xo = x.groupby(["orgao", "elemento"], as_index=False, observed=True)[est].sum().sort_values(est, ascending=False)
            ui.grafico(G.barras(xo.head(12).assign(rot=lambda z: z["orgao"].astype(str).str.slice(0, 35)), "rot", est, "elemento",
                                     horizontal=True, titulo="Por órgão e elemento"), "fn_ficha_o", "ckan_credores", onde=c2,
                   nota=f"arquivos mensais despesas-MM_AAAA.csv, todos os meses de {ui.periodo(x)}: a ficha ignora o filtro Meses")
            emp = x[["ano", "mes", "orgao", "funcao", "acao", "elemento", "licitacao", "empenho", "empenhado", "liquidado", "pago"]]
            ui.tabela(emp, "fn_ficha_tab", 
                      fontes=["ckan_credores"], nota=f"arquivos mensais despesas-MM_AAAA.csv, todos os meses de {ui.periodo(x)}: a ficha ignora o filtro Meses",
                      moeda=["empenhado", "liquidado", "pago"], ordenar_padrao=est)

    with abas[3]:
        c1, c2 = st.columns(2)
        el = d.groupby("elemento", as_index=False, observed=True)[est].sum().sort_values(est, ascending=False).head(15)
        ui.grafico(G.barras(el, "elemento", est, horizontal=True, titulo="Por elemento de despesa"),
                   "fn_el_bar", "ckan_credores", onde=c1,
                   nota=nota_ck)
        li = d.assign(licitacao=d["licitacao"].astype(str).replace("", "(não informado)")).groupby("licitacao", as_index=False)[est].sum()
        li = li.sort_values(est, ascending=False)
        ui.grafico(G.barras(li, "licitacao", est, horizontal=True, titulo="Por tipo de licitação"),
                   "fn_lic_bar", "ckan_credores", onde=c2,
                   nota=nota_ck)
        fx = d.groupby(["funcao", "elemento"], as_index=False, observed=True)[est].sum()
        ui.grafico(G.treemap(fx, ["funcao", "elemento"], est, "Função › elemento"), "fn_fx", "ckan_credores",
                   nota=nota_ck)

    with abas[4]:
        _mes_corrente(mostrar_pf, busca)


def _mes_corrente(mostrar_pf: bool, busca: str):
    pc = ui.glob("portal_credores_*.parquet")
    if pc.empty:
        ui.sem_dados("credores do portal", "python coletar.py --portal")
        return
    meses = sorted({(int(a), int(m)) for a, m in pc[["ano", "mes"]].itertuples(index=False)}, reverse=True)
    a, m = st.selectbox("Mês", meses, format_func=lambda x: f"{G.MESES[x[1] - 1]}/{x[0]}", key="fn_pc_mes")
    x = pc[(pc["ano"] == a) & (pc["mes"] == m)].copy()
    from ms_fiscal.dados_abertos import tipo_credor
    x["tipo_credor"] = [tipo_credor(dd, n) for dd, n in zip(x["cpf_cnpj"], x["credor"].str.upper())]
    x = _anonimizar(x, mostrar_pf)
    if busca:
        x = x[x["credor"].str.contains(busca, case=False, na=False) | x["cpf_cnpj"].str.contains(busca, regex=False)]
    tipos = st.multiselect("Tipo de credor", sorted(x["tipo_credor"].unique()), default=["Empresa ou entidade privada"], key="fn_pc_tipo")
    if tipos:
        x = x[x["tipo_credor"].isin(tipos)]
    x = x.groupby(["cpf_cnpj", "credor", "tipo_credor"], as_index=False)[["empenhado", "liquidado", "pago"]].sum()
    st.caption(f"Movimento de 01/{m:02d}/{a} até {pd.Timestamp(pc.loc[(pc['ano'] == a) & (pc['mes'] == m), 'ate'].max()):%d/%m/%Y} "
               "(Portal da Transparência › Despesas › por credor; inclui todos os elementos de despesa).")
    ui.grafico(G.barras(x.sort_values("pago", ascending=False).head(20).assign(rot=lambda z: z["credor"].str.slice(0, 45)),
                             "rot", "pago", horizontal=True, titulo="Maiores pagamentos no mês", altura=560),
                                        "fn_pc_bar", "portal_desp_credores",
                   nota="mês selecionado, de dia 1 até a data da coleta")
    ui.tabela(x, "fn_pc_tab", 
              fontes=["portal_desp_credores"], nota="mês selecionado, de dia 1 até a data da coleta",
              moeda=["empenhado", "liquidado", "pago"], ordenar_padrao="pago")
