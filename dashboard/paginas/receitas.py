"""Receitas: natureza da receita (MCASP), tributos estaduais, deduções e tempo real."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import referencias as R
from ms_fiscal import transformacoes as T
from ms_fiscal import ui

FONTES_MSC = ("siconfi_msc",)
NOTA_MSC = ("contas 6.2.1.2 (receita realizada) e 6.2.1.3 (deduções), por natureza da receita; nomes das naturezas "
            "da árvore da receita do portal (receitaconsolidadas)")
AGRUPAMENTOS = ["Tributo / origem (painel)", *R.NIVEIS_RECEITA.keys(), "Fonte de recursos", "Poder / órgão", "Tipo (bruta × deduções)"]


def _dimensao(df: pd.DataFrame, escolha: str) -> pd.Series:
    if escolha == "Tributo / origem (painel)":
        return df["tributo"]
    if escolha in R.NIVEIS_RECEITA:
        return T.adicionar_niveis_receita(df, escolha)
    return {"Fonte de recursos": df["fonte"], "Poder / órgão": df["poder"], "Tipo (bruta × deduções)": df["tipo"]}[escolha]


def _medida(d: pd.DataFrame, medida: str) -> pd.DataFrame:
    if medida == "Bruta registrada":
        return d[~d["deducao"]]
    if medida == "Bruta (exceto renúncia)":
        return d[~d["deducao"] | d["renuncia"]]
    if medida == "Deduções":
        return d[d["deducao"]].assign(valor=lambda x: -x["valor"])
    return d


def _origem_filtros() -> None:
    ui.explicar_filtros(
        "Os filtros do topo vêm de campos da Matriz de Saldos Contábeis (MSC), lida na API do Siconfi, ou são listas "
        "fixas e classificações do painel. Os filtros da aba Tempo real (portal) vêm da API do Portal da Transparência.",
        ui.passos_msc("`conta_contabil` (receita realizada 6.2.1.2 e deduções 6.2.1.3.x), `natureza_receita` "
                      "(8 dígitos do MCASP), `poder_orgao` e `fonte_recursos`",
                      "o nome de cada natureza vem da árvore da receita do Portal da Transparência (API "
                      "`receitaconsolidadas`, em gw.sgi.ms.gov.br), que usa os mesmos códigos. Quando falta, o painel "
                      "usa a tabela do MCASP (categoria e origem) ou o nome do nível acima, com \"(detalhe <código>)\"."),
        [("Exercícios", "Anos dos arquivos MSC carregados."),
         ("Meses", "Lista fixa, de janeiro a dezembro."),
         ("Medida", "Lista fixa. **Líquida** = receita realizada + deduções (que são negativas); **Bruta registrada** "
                    "= só a conta 6.2.1.2; **Bruta (exceto renúncia)** = bruta sem a renúncia de ICMS, que desde 2026 "
                    "é registrada como receita e dedução ao mesmo tempo; **Deduções** = contas 6.2.1.3.x, com sinal "
                    "positivo."),
         ("Agrupar por", "Lista fixa. Não filtra: define as séries do gráfico. As opções são o tributo/origem do "
                         "painel, os 7 níveis da natureza da receita (categoria = 1º dígito; origem = 2; espécie = 3; "
                         "desdobramentos = 4, 6 e 7; tipo = 8), a fonte de recursos, o Poder e o tipo de conta (bruta "
                         "× cada dedução)."),
         ("Intraorçamentárias", "Liga ou desliga as naturezas que começam com 7 ou 8: receitas de operações entre "
                                "órgãos do próprio Estado. Fica desligado por padrão, como no RREO."),
         ("Poder / órgão", "Campo `poder_orgao` (5 dígitos) + nome da tabela do painel."),
         ("Tributo / origem", "**Calculado pelo painel**, não existe na MSC. O código de `natureza_receita` é comparado "
                              "a uma lista de prefixos em `ms_fiscal/referencias.py` (ex.: 1114501 = ICMS, 111251 = "
                              "IPVA, 171150 = FPE); vale o primeiro que casar. O resto vira \"Demais receitas "
                              "correntes\" ou \"Demais receitas\"."),
         ("Séries no gráfico", "Número de 3 a 8: as maiores séries aparecem separadas e as demais somam em \"Outros\"."),
         ("Tributo ou transferência (aba ICMS, IPVA…)", "Lista fixa com as 10 principais receitas."),
         ("Nível de detalhe (aba Tabela)", "Os 7 níveis da natureza da receita."),
         ("Buscar natureza (aba Tabela)", "Texto livre, procurado no nome da natureza."),
         ("Profundidade da árvore (aba Tempo real)", "Níveis da árvore devolvida pela API `receitaconsolidadas`, "
                                                     "contados a partir da raiz."),
         ("Buscar na árvore (aba Tempo real)", "Texto livre, procurado no nome da receita na árvore do portal.")],
        ["**Aba ICMS, IPVA…**: respeita Meses e Medida, mas mostra todos os exercícios carregados para comparar anos.",
         "**Aba Tempo real (portal)**: não usa os filtros do topo. Mostra o exercício corrente acumulado até a coleta.",
         "**Opções independentes**: as opções não mudam com os outros filtros. Uma escolha pode não retornar dados."],
        fontes=("siconfi_msc", "portal_rec_consolidada"),
        nota="campos da MSC; nomes das naturezas e aba Tempo real pelo portal")


def render():
    st.title("Receitas")
    S = ui.sigla
    st.caption(f"Receita orçamentária realizada, classificada por natureza conforme o {S('MCASP')} (Parte I – {S('PCO')}). "
               f"Série mensal da Matriz de Saldos Contábeis ({S('MSC')}) do {S('Siconfi')} e acompanhamento diário pelo "
               "Portal da Transparência.", unsafe_allow_html=True)
    ui.base_legal(["receita_natureza", "receita_deducoes", "receita_estagios"], ["art11", "art12", "art14", "art2iv", "art48a"])

    rec = ui.receitas_msc()
    if rec.empty:
        ui.sem_dados("MSC", "python coletar.py --siconfi")
        return
    rec = ui.ajustar(rec, ["valor"])
    _origem_filtros()

    # ------------------------------------------------------------ filtros (uma linha)
    f = st.columns([1.3, 1.3, 1.6, 1.4, 1.3])
    anos = sorted(rec["ano"].unique())
    sel_anos = f[0].multiselect("Exercícios", anos, default=anos[-2:], key="rc_anos")
    m_ini, m_fim = f[1].select_slider("Meses", options=list(range(1, 13)), value=(1, 12),
                                      format_func=lambda m: G.MESES[m - 1], key="rc_meses")
    medida = f[2].selectbox("Medida", ["Líquida", "Bruta (exceto renúncia)", "Bruta registrada", "Deduções"], key="rc_medida",
                            help="Líquida = bruta − deduções (FUNDEB, cota-parte dos municípios, renúncia, restituições). "
                                 "Desde 2026 a renúncia de ICMS é registrada como receita bruta e dedução ao mesmo tempo; "
                                 "'Bruta (exceto renúncia)' mantém a comparação com anos anteriores.")
    agrup = f[3].selectbox("Agrupar por", AGRUPAMENTOS, key="rc_agrup")
    intra = f[4].toggle("Intraorçamentárias", value=False, key="rc_intra")
    f2 = st.columns([2, 2, 1])
    poderes = ui.filtro_multiplo(f2[0], "Poder / órgão", rec["poder"], "rc_poder")
    tributos = ui.filtro_multiplo(f2[1], "Tributo / origem", rec["tributo"], "rc_trib")
    top = f2[2].number_input("Séries no gráfico", 3, 8, 7, key="rc_top")

    d = rec[rec["ano"].isin(sel_anos) & rec["mes"].between(m_ini, m_fim)]
    if not intra:
        d = d[~d["intra"]]
    d = ui.aplicar_filtro(ui.aplicar_filtro(d, "poder", poderes), "tributo", tributos)
    d = _medida(d, medida)
    if d.empty:
        st.warning("Nenhum dado para os filtros escolhidos.")
        return
    d = d.assign(grupo=_dimensao(d, agrup))
    per = ui.periodo(d)
    st.caption(f"Período nos gráficos e tabelas: **{per}**. Os totais que não são mensais somam todos esses meses.")

    abas = st.tabs(["📈 Evolução mensal", "🧩 Composição", "🏷️ ICMS, IPVA, ITCD, FPE…", "➖ Deduções",
                    "⏱️ Tempo real (portal)", "📋 Tabela"])

    with abas[0]:
        ult12 = sorted(d["data"].unique())[-12:]
        g = d[d["data"].isin(ult12)].groupby(["data", "grupo"], as_index=False)["valor"].sum()
        g = G.top_n_outros(g, "grupo", "valor", int(top)).groupby(["data", "grupo"], as_index=False)["valor"].sum()
        ordem = g.groupby("grupo")["valor"].sum().sort_values(ascending=False).index.tolist()
        ordem = [o for o in ordem if o != "Outros"] + (["Outros"] if "Outros" in ordem else [])
        ui.grafico(G.barras(g, "data", "valor", "grupo", f"Receita {medida.lower()} mensal por {agrup.lower()} – últimos 12 meses",
                            ordem={"grupo": ordem}, cores=G.mapa_cores(ordem)), "rc_evol", *FONTES_MSC,
                   nota=f"{pd.Timestamp(ult12[0]):%m/%Y} a {pd.Timestamp(ult12[-1]):%m/%Y}: os 12 últimos meses disponíveis "
                        f"nos filtros escolhidos; {NOTA_MSC}")
        # comparação acumulada ano a ano
        a = d.groupby(["ano", "mes"], as_index=False)["valor"].sum().sort_values(["ano", "mes"])
        a["acumulado"] = a.groupby("ano")["valor"].cumsum()
        a["mês"] = a["mes"].map(lambda m: G.MESES[m - 1])
        a["ano"] = a["ano"].astype(str)
        inicio = G.MESES[m_ini - 1]
        fig = G.linhas(a, "mês", "acumulado", "ano",
                       f"Receita acumulada no ano, de {inicio} até cada mês – comparação entre exercícios")
        fig.update_yaxes(title=f"Acumulado desde {inicio}")
        ui.grafico(fig, "rc_acum", *FONTES_MSC,
                   nota=f"cada ponto é o total acumulado no exercício, de {inicio} até o mês indicado (não o valor do mês); "
                        + NOTA_MSC)

    with abas[1]:
        niv = d.copy()
        for n in ("Categoria econômica", "Origem", "Espécie", "Desdobramento (1)"):
            niv[n] = T.adicionar_niveis_receita(niv, n)
        pos = niv.groupby(["Categoria econômica", "Origem", "Espécie", "Desdobramento (1)"], as_index=False)["valor"].sum()
        ui.grafico(G.treemap(pos, ["Categoria econômica", "Origem", "Espécie", "Desdobramento (1)"], "valor",
                             "Composição da receita por natureza (clique para aprofundar)", altura=620,
                             raiz=f"Receita {medida.lower()} total",
                             pct_de=f"da receita {medida.lower()} total (valores positivos) de {per}"),
                   "rc_tree", *FONTES_MSC,
                   nota=f"o % de cada área é sobre a soma das naturezas com valor positivo no período e nos filtros "
                        f"escolhidos; {per}; {NOTA_MSC}")
        st.caption("Níveis da natureza (MCASP): categoria econômica › origem › espécie › desdobramento. "
                   "Valores negativos (deduções líquidas) não aparecem no mapa.")

    with abas[2]:
        chave = ["ICMS", "IPVA", "ITCD", "IRRF", "FPE", "Transferências do FUNDEB", "IPI-Exportação",
                 "Adicional ICMS – FECOMP", "Taxas", "Contribuições previdenciárias (RPPS/SPSM)"]
        base = rec[rec["mes"].between(m_ini, m_fim) & rec["tributo"].isin(chave)]
        base = _medida(base, medida)
        trib = st.selectbox("Tributo ou transferência", chave, key="rc_trib_sel")
        x = base[base["tributo"] == trib].groupby(["ano", "mes"], as_index=False)["valor"].sum()
        x["mês"] = x["mes"].map(lambda m: G.MESES[m - 1])
        x["ano"] = x["ano"].astype(str)
        desc = next((t[2] for t in R.TRIBUTOS_CHAVE if t[0] == trib), "")
        st.markdown(f"**{trib}** — {desc}")
        c1, c2 = st.columns([3, 2])
        ui.grafico(G.linhas(x, "mês", "valor", "ano", f"{trib}: arrecadação mensal ({medida.lower()}) por exercício"),
                   "rc_trib_l", *FONTES_MSC, onde=c1, nota=NOTA_MSC)
        tab = x.pivot_table(index="ano", values="valor", aggfunc="sum").reset_index().rename(columns={"valor": f"Total {G.MESES[m_ini-1]}–{G.MESES[m_fim-1]}"})
        tab["Variação % sobre o ano anterior"] = tab.iloc[:, 1].pct_change() * 100
        cobre = x.groupby("ano")["mes"].agg(lambda s: f"{G.MESES[s.min() - 1]} a {G.MESES[s.max() - 1]}")
        tab["Meses com dados"] = tab["ano"].map(cobre)
        with c2:
            ui.tabela(tab, "rc_trib_tab", moeda=[tab.columns[1]], pct=["Variação % sobre o ano anterior"], ordenar_padrao="ano",
                      fontes=FONTES_MSC, nota="cada linha soma os meses filtrados do seu exercício (coluna 'Meses com "
                                              "dados'); se o último exercício tem menos meses, a variação compara "
                                              "períodos diferentes – ajuste o filtro Meses; " + NOTA_MSC)
        comp = base[base["ano"].isin(sel_anos)].groupby(["tributo", "ano"], as_index=False)["valor"].sum()
        comp["ano"] = comp["ano"].astype(str)
        ui.grafico(G.barras(comp, "tributo", "valor", "ano", "Principais receitas – comparação entre exercícios",
                            empilhar=False), "rc_trib_b", *FONTES_MSC,
                   nota=f"cada barra soma os meses filtrados do seu exercício "
                        f"({ui.periodo(base[base['ano'].isin(sel_anos)], somados=False)}); {NOTA_MSC}")
        st.caption("ICMS, IPVA e ITCD são impostos estaduais (CF, art. 155); FPE, IPI-Exportação e IRRF são "
                   "participações em receitas da União (CF, arts. 157 e 159).")

    with abas[3]:
        dd = rec[rec["ano"].isin(sel_anos) & rec["mes"].between(m_ini, m_fim)]
        if not intra:
            dd = dd[~dd["intra"]]
        pv = dd.groupby(["tributo", "tipo"], as_index=False)["valor"].sum()
        pv = pv[pv["tributo"].isin(["ICMS", "IPVA", "FPE", "IPI-Exportação", "ITCD", "Adicional ICMS – FECOMP", "CIDE-Combustíveis"])]
        per_ded = ui.periodo(dd)
        st.plotly_chart(G.barras(pv, "tributo", "valor", "tipo", f"Receita bruta e deduções por tributo – {per_ded} (deduções em negativo)",
                                 cores={"Receita bruta realizada": G.CORES[0], "Dedução – FUNDEB": G.CORES[1],
                                        "Dedução – transferências a municípios": G.CORES[2], "Dedução – renúncia": G.CORES[3],
                                        "Dedução – outras": G.OUTROS}), key="rc_ded")
        ui.fonte(*FONTES_MSC, nota="contas 6.2.1.2 (receita realizada) e 6.2.1.3.1.01 a 6.2.1.3.9 (deduções)")
        larga = pv.pivot_table(index="tributo", columns="tipo", values="valor", aggfunc="sum").fillna(0)
        if "Receita bruta realizada" in larga:
            for c in [c for c in larga.columns if c.startswith("Dedução")]:
                larga[f"% {c} sobre a receita bruta do tributo"] = -larga[c] / larga["Receita bruta realizada"] * 100
        larga = larga.reset_index()
        ui.tabela(larga, "rc_ded_tab", moeda=[c for c in larga.columns if not c.startswith("%") and c != "tributo"],
                  pct=[c for c in larga.columns if c.startswith("%")], fontes=FONTES_MSC, nota=f"{per_ded}; {NOTA_MSC}")
        st.caption("Referências: 25% do ICMS e 50% do IPVA pertencem aos municípios (CF, art. 158, III e IV); 20% de "
                   "ICMS, IPVA, ITCD, FPE e IPI-Exportação formam o FUNDEB (CF, art. 212-A).")

    with abas[4]:
        _tempo_real()

    with abas[5]:
        niv = st.selectbox("Nível de detalhe", list(R.NIVEIS_RECEITA), index=4, key="rc_tab_niv")
        t = d.assign(natureza=T.adicionar_niveis_receita(d, niv))
        t = t.groupby(["ano", "natureza", "tributo"], as_index=False)["valor"].sum()
        larga = t.pivot_table(index=["natureza", "tributo"], columns="ano", values="valor", aggfunc="sum").fillna(0)
        larga.columns = [str(c) for c in larga.columns]
        if len(larga.columns) >= 2:
            a, b = larga.columns[-2], larga.columns[-1]
            larga[f"Variação % {b}/{a}"] = (larga[b] / larga[a].where(larga[a] != 0) - 1) * 100
        larga = larga.reset_index()
        busca = st.text_input("Buscar natureza", key="rc_busca", placeholder="ex.: ICMS, combustíveis, FPE, dívida ativa")
        if busca:
            larga = larga[larga["natureza"].str.contains(busca, case=False, na=False)]
        ui.tabela(larga, "rc_tab", moeda=[c for c in larga.columns if c.isdigit()],
                  pct=[c for c in larga.columns if c.startswith("Variação")], fontes=FONTES_MSC,
                  nota=f"cada coluna de ano soma os meses filtrados daquele exercício ({ui.periodo(d, somados=False)}); "
                       f"se os exercícios cobrem meses diferentes, a variação compara períodos diferentes; {NOTA_MSC}")


def _tempo_real():
    arv = ui.glob("portal_receita_arvore_2*.parquet")
    mens = ui.parquet("portal_receita_mensal.parquet")
    meta = ui.portal.meta()
    if arv.empty:
        ui.sem_dados("receitas do portal", "python coletar.py --portal")
        return
    st.caption(f"Portal da Transparência › Receitas, atualizado diariamente · coleta de {meta.get('coletado_em', '?').replace('T', ' ')}.")
    if not mens.empty:
        ano = int(mens["ano"].max())
        m = mens[mens["ano"] == ano].groupby(["mes", "receita"], as_index=False)["arrecadado"].sum()
        m["mês"] = m["mes"].map(lambda x: G.MESES[x - 1])
        m = G.top_n_outros(m, "receita", "arrecadado", 7).groupby(["mes", "mês", "receita"], as_index=False)["arrecadado"].sum()
        ordem = m.groupby("receita")["arrecadado"].sum().sort_values(ascending=False).index.tolist()
        ordem = [o for o in ordem if o != "Outros"] + (["Outros"] if "Outros" in ordem else [])
        ui.grafico(G.barras(m.sort_values("mes"), "mês", "arrecadado", "receita",
                            f"Receita arrecadada por mês em {ano} (o último mês é parcial)", ordem={"receita": ordem},
                            cores=G.mapa_cores(ordem)), "rc_rt_mes", "portal_rec_simplificada",
                   nota="uma consulta por mês (mesInicio = mesTermino); valores líquidos das deduções")
    ano = int(arv["ano"].max())
    a = arv[arv["ano"] == ano]
    prof = st.slider("Profundidade da árvore", 1, int(a["nivel"].max()), 3, key="rc_rt_prof")
    sub = a[a["nivel"] <= prof]
    ui.grafico(_sunburst_arvore(sub), "rc_rt_sun", "portal_rec_consolidada", nota=f"exercício {ano}, acumulado até a coleta")
    tab = a[a["nivel"] <= prof][["codigo", "receita", "nivel", "previsto", "arrecadado"]].copy()
    tab["% arrecadado/previsto no ano"] = tab["arrecadado"] / tab["previsto"].where(tab["previsto"] != 0) * 100
    busca = st.text_input("Buscar na árvore da receita", key="rc_rt_busca", placeholder="ex.: Combustíveis, Simples Nacional, FUNDEB")
    if busca:
        tab = a[a["receita"].str.contains(busca, case=False, na=False)][["codigo", "receita", "nivel", "previsto", "arrecadado"]]
    ui.tabela(tab, "rc_rt_tab", moeda=["previsto", "arrecadado"], pct=["% arrecadado/previsto no ano"], ordenar_padrao="codigo",
              fontes=["portal_rec_consolidada"],
              nota=f"exercício {ano}: previsto = previsão da LOA para o ano inteiro; arrecadado = de 1º/jan até a coleta")
    st.caption("A árvore traz a receita prevista na LOA e a arrecadada no ano até a data da coleta, com as deduções "
               "(FUNDEB, municípios, restituições e renúncia) como itens próprios, conforme o MCASP.")


def _sunburst_arvore(df: pd.DataFrame):
    import plotly.graph_objects as go
    d = df[df["arrecadado"] > 0]
    fig = go.Figure(go.Sunburst(ids=d["codigo"], parents=d["pai"].where(d["pai"].isin(d["codigo"]), ""),
                                labels=d["receita"].str.slice(0, 40), values=d["arrecadado"], branchvalues="remainder",
                                hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>", maxdepth=3))
    fig.update_layout(colorway=G.CORES)
    return G._layout(fig, "Receita arrecadada no ano, por natureza (portal)", 620, legenda=False)
