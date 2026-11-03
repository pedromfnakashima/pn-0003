"""Despesas: estágios, classificação funcional, natureza, fontes e restos a pagar (MSC)."""
from __future__ import annotations

import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import ui

DIMENSOES = {
    "Função": "funcao", "Subfunção": "subfuncao", "Categoria econômica": "categoria", "Grupo de natureza": "grupo",
    "Modalidade de aplicação": "modalidade", "Destino (agrupamento da modalidade)": "grupo_modalidade",
    "Elemento de despesa": "elemento", "Natureza (c.g.mm.ee)": "natureza", "Fonte de recursos": "fonte",
    "Poder / órgão": "poder",
}
NOTA_MSC = ("contas 6.2.2.1.3.01 a 6.2.2.1.3.04 (empenhado: as quatro; liquidado: .03 e .04; pago: .04), "
            "com função, subfunção, natureza, fonte e Poder")
ESTAGIOS = {"Empenhada": "empenhado", "Liquidada": "liquidado", "Paga": "pago"}


def _origem_filtros() -> None:
    ui.explicar_filtros(
        "Todas as opções vêm de campos da Matriz de Saldos Contábeis (MSC), lida na API do Siconfi, ou são listas fixas "
        "do painel. Nenhuma vem de planilha nem de arquivo CSV.",
        ui.passos_msc("`conta_contabil` (estágio), `natureza_despesa` (8 dígitos: categoria, grupo, modalidade, "
                      "elemento), `funcao`, `subfuncao`, `poder_orgao` e `fonte_recursos`",
                      "o painel junta a cada código o nome oficial das tabelas do MCASP, gravadas em "
                      "`ms_fiscal/referencias.py`. Quando o código não está na tabela, aparece \"?\"."),
        [("Exercícios", "Anos dos arquivos MSC carregados."),
         ("Meses", "Lista fixa, de janeiro a dezembro."),
         ("Estágio", "Fixo. **Empenhada** = soma das contas 6.2.2.1.3.01 a .04; **liquidada** = .03 + .04; "
                     "**paga** = .04."),
         ("Agrupar por", "Lista fixa de 10 dimensões do painel. Não filtra: só define as séries e as cores dos gráficos."),
         ("Intraorçamentárias", "Liga ou desliga a modalidade 91 (dígitos 3 e 4 de `natureza_despesa`): operações "
                                "entre órgãos e fundos do próprio Estado. Fica desligado por padrão, como no RREO."),
         ("Função", "Campo `funcao` (2 dígitos) + nome da Portaria MOG nº 42/1999."),
         ("Grupo de natureza", "2º dígito de `natureza_despesa` + nome da Portaria Interministerial nº 163/2001 "
                               "(pessoal, juros, outras correntes, investimentos, inversões, amortização)."),
         ("Poder / órgão", "Campo `poder_orgao` (5 dígitos, ex.: 10111 = Poder Executivo) + nome da tabela do painel. "
                           "Código desconhecido aparece como \"Poder/órgão <código>\"."),
         ("Fonte de recursos", "Campo `fonte_recursos` + nome dos 3 últimos dígitos (Portaria STN nº 710/2021). "
                               "O 1º dígito indica recursos do exercício (1) ou de exercícios anteriores (2)."),
         ("Detalhar uma função (aba Funções)", "Funções que restam após os filtros, da maior para a menor despesa. "
                                               "Começa em Saúde (10)."),
         ("Colunas de agrupamento (aba Tabela)", "As mesmas 10 dimensões de \"Agrupar por\".")],
        ["**Poder, não secretaria**: a MSC identifica o Poder, mas não o órgão nem a unidade gestora. A despesa por "
         "secretaria está na página Órgãos e fornecedores.",
         "**Nomes oficiais**: os nomes vêm das tabelas do MCASP, não da grafia do Estado, por isso são padronizados e "
         "conferíveis pelo código.",
         "**Opções independentes**: as opções não mudam com os outros filtros. Uma escolha pode não retornar dados.",
         "**Restos a pagar**: a aba respeita apenas o filtro Exercícios (contas 6.3.1 e 6.3.2 da MSC)."],
        fontes=("siconfi_msc",), nota="campos da MSC listados acima, em todos os meses carregados")


def render():
    st.title("Despesas")
    st.caption("Despesa orçamentária do exercício por estágio (empenho, liquidação e pagamento), classificada conforme o "
               "MCASP: funcional (função e subfunção), natureza (categoria, grupo, modalidade, elemento) e fonte de recursos.")
    ui.base_legal(["despesa_estagios", "despesa_funcional", "despesa_natureza", "despesa_modalidade", "fontes", "restos_pagar"],
                  ["art9", "art18", "art48", "art52"])
    desp = ui.despesas_msc()
    if desp.empty:
        ui.sem_dados("MSC", "python coletar.py --siconfi")
        return
    desp = ui.ajustar(desp, ["empenhado", "liquidado", "pago"])
    _origem_filtros()

    f = st.columns([1.3, 1.3, 1.5, 1.5, 1.2])
    anos = sorted(desp["ano"].unique())
    sel_anos = f[0].multiselect("Exercícios", anos, default=anos[-2:], key="dp_anos")
    m_ini, m_fim = f[1].select_slider("Meses", list(range(1, 13)), value=(1, 12), format_func=lambda m: G.MESES[m - 1], key="dp_meses")
    est_nome = f[2].radio("Estágio", list(ESTAGIOS), index=1, horizontal=True, key="dp_est")
    dim_nome = f[3].selectbox("Agrupar por", list(DIMENSOES), key="dp_dim")
    intra = f[4].toggle("Intraorçamentárias", value=False, key="dp_intra")
    f2 = st.columns(4)
    funcoes = ui.filtro_multiplo(f2[0], "Função", desp["funcao"], "dp_f")
    grupos = ui.filtro_multiplo(f2[1], "Grupo de natureza", desp["grupo"], "dp_g")
    poderes = ui.filtro_multiplo(f2[2], "Poder / órgão", desp["poder"], "dp_p")
    fontes = ui.filtro_multiplo(f2[3], "Fonte de recursos", desp["fonte"], "dp_fo")

    est, dim = ESTAGIOS[est_nome], DIMENSOES[dim_nome]
    d = desp[desp["ano"].isin(sel_anos) & desp["mes"].between(m_ini, m_fim)]
    if not intra:
        d = d[~d["intra"]]
    for col, sel in (("funcao", funcoes), ("grupo", grupos), ("poder", poderes), ("fonte", fontes)):
        d = ui.aplicar_filtro(d, col, sel)
    if d.empty:
        st.warning("Nenhum dado para os filtros escolhidos.")
        return
    per = ui.periodo(d)
    nota_per = f"{per}; {NOTA_MSC}"
    nota_ano = f"cada exercício soma seus meses filtrados ({ui.periodo(d, somados=False)}); {NOTA_MSC}"
    st.caption(f"Período nos gráficos e tabelas: **{per}**. Os totais que não são mensais somam todos esses meses.")

    abas = st.tabs(["📈 Evolução e estágios", "🎯 Funções e subfunções", "🧱 Natureza da despesa", "🏦 Fontes de recursos",
                    "⏳ Restos a pagar", "📋 Tabela"])

    with abas[0]:
        g = d.groupby(["data", dim], as_index=False)[est].sum()
        g = G.top_n_outros(g, dim, est, 7).groupby(["data", dim], as_index=False)[est].sum()
        ordem = g.groupby(dim)[est].sum().sort_values(ascending=False).index.tolist()
        ordem = [o for o in ordem if o != "Outros"] + (["Outros"] if "Outros" in ordem else [])
        ui.grafico(G.barras(g, "data", est, dim, f"Despesa {est_nome.lower()} mensal por {dim_nome.lower()}",
                                 ordem={dim: ordem}, cores=G.mapa_cores(ordem)), "dp_evol", "siconfi_msc",
                   nota=NOTA_MSC)
        e = d.groupby(["ano", "mes"], as_index=False)[["empenhado", "liquidado", "pago"]].sum().sort_values(["ano", "mes"])
        for c in ("empenhado", "liquidado", "pago"):
            e[c] = e.groupby("ano")[c].cumsum()
        e["mês"] = e["mes"].map(lambda m: G.MESES[m - 1])
        e = e.melt(["ano", "mes", "mês"], ["empenhado", "liquidado", "pago"], var_name="estágio", value_name="acumulado")
        e["série"] = e["ano"].astype(str) + " · " + e["estágio"] + " acumulado"
        c1, c2 = st.columns([3, 2])
        inicio = G.MESES[m_ini - 1]
        fig = G.linhas(e, "mês", "acumulado", "série",
                       f"Estágios acumulados no ano, de {inicio} até cada mês (empenho → liquidação → pagamento)")
        fig.update_yaxes(title=f"Acumulado desde {inicio}")
        ui.grafico(fig, "dp_estag", "siconfi_msc", onde=c1,
                   nota=f"cada ponto é o total acumulado no ano, de {inicio} até o mês indicado (não o valor do mês); "
                        + NOTA_MSC)
        ult = e[e["ano"] == max(sel_anos)]
        ult = ult[ult["mes"] == ult["mes"].max()].set_index("estágio")["acumulado"]
        with c2:
            st.markdown(f"**{max(sel_anos)} – acumulado de {inicio} a "
                        f"{G.MESES[int(e[e['ano'] == max(sel_anos)]['mes'].max()) - 1]}**")
            st.markdown(" · ".join(f"**{k.capitalize()}:** {G.brl(ult.get(k, 0))}" for k in ("empenhado", "liquidado", "pago"))
                        .replace("$", "\\$"))
            if ult.get("empenhado"):
                st.progress(min(1.0, ult.get("liquidado", 0) / ult["empenhado"]),
                            text=f"Liquidado/empenhado: {G.pct(ult.get('liquidado', 0) / ult['empenhado'] * 100)}")
                st.progress(min(1.0, ult.get("pago", 0) / ult["empenhado"]),
                            text=f"Pago/empenhado: {G.pct(ult.get('pago', 0) / ult['empenhado'] * 100)}")
            st.caption("Empenho reserva a dotação; liquidação verifica o direito do credor; pagamento extingue a obrigação "
                       "(Lei 4.320/1964, arts. 58, 63 e 64). O que é empenhado e não pago até 31/12 vira restos a pagar.")

    with abas[1]:
        fs = d.groupby(["funcao", "subfuncao"], as_index=False)[est].sum()
        c1, c2 = st.columns([2, 3])
        tf = fs.groupby("funcao", as_index=False)[est].sum().sort_values(est, ascending=False)
        tot = tf[est].sum()
        tf["%"] = tf[est] / tot * 100 if tot else 0
        ui.grafico(G.barras(tf.head(15), "funcao", est, horizontal=True, titulo=f"Despesa {est_nome.lower()} por função"),
                   "dp_func", "siconfi_msc", onde=c1,
                   nota=nota_per)
        ui.grafico(G.treemap(fs, ["funcao", "subfuncao"], est, "Funções › subfunções (clique para aprofundar)",
                             raiz=f"Despesa {est_nome.lower()} total", pct_de=f"da despesa {est_nome.lower()} total de {per}"),
                   "dp_func_tree", "siconfi_msc", onde=c2,
                   nota=f"o % de cada área é sobre a despesa {est_nome.lower()} total do período e dos filtros escolhidos; "
                        + nota_per)
        sel_f = st.selectbox("Detalhar uma função", tf["funcao"].tolist(), key="dp_func_sel",
                             index=next((i for i, v in enumerate(tf["funcao"]) if v.startswith("10")), 0))
        sub = d[d["funcao"] == sel_f].groupby(["data", "subfuncao"], as_index=False)[est].sum()
        sub = G.top_n_outros(sub, "subfuncao", est, 7).groupby(["data", "subfuncao"], as_index=False)[est].sum()
        ui.grafico(G.barras(sub, "data", est, "subfuncao", f"{sel_f}: despesa {est_nome.lower()} mensal por subfunção"),
                   "dp_sub", "siconfi_msc",
                   nota=NOTA_MSC)
        st.caption("Educação (12) e Saúde (10) têm aplicação mínima constitucional apurada no RREO (CF, art. 212: 25% "
                   "da receita de impostos em MDE; LC 141/2012: 12% em ASPS) – veja a página RREO.")

    with abas[2]:
        nat = d.groupby(["categoria", "grupo", "modalidade", "elemento"], as_index=False)[est].sum()
        ui.grafico(G.treemap(nat, ["categoria", "grupo", "modalidade", "elemento"], est,
                                  "Categoria › grupo › modalidade › elemento", altura=640,
                             raiz=f"Despesa {est_nome.lower()} total", pct_de=f"da despesa {est_nome.lower()} total de {per}"),
                   "dp_nat", "siconfi_msc",
                   nota=f"o % de cada área é sobre a despesa {est_nome.lower()} total do período e dos filtros escolhidos; "
                        + nota_per)
        c1, c2 = st.columns(2)
        gg = d.groupby(["ano", "grupo"], as_index=False)[est].sum()
        gg["ano"] = gg["ano"].astype(str)
        ui.grafico(G.barras(gg, "grupo", est, "ano", "Grupo de natureza de despesa por exercício", empilhar=False),
                   "dp_grp", "siconfi_msc", onde=c1,
                   nota=nota_ano)
        el = d.groupby("elemento", as_index=False)[est].sum().sort_values(est, ascending=False).head(15)
        ui.grafico(G.barras(el, "elemento", est, horizontal=True, titulo="Principais elementos de despesa"),
                   "dp_el", "siconfi_msc", onde=c2,
                   nota=nota_per)

    with abas[3]:
        fo = d.groupby("fonte", as_index=False)[est].sum().sort_values(est, ascending=False)
        ui.grafico(G.barras(fo.head(20), "fonte", est, horizontal=True, titulo="Despesa por fonte de recursos", altura=560),
                   "dp_fonte", "siconfi_msc",
                   nota=nota_per)
        st.caption("Fontes padronizadas pela Portaria STN nº 710/2021: 1º dígito 1 = recursos do exercício, 2 = de "
                   "exercícios anteriores (superávit); os três últimos identificam a vinculação.")

    with abas[4]:
        rp = ui.rp_msc()
        if rp.empty:
            st.caption("Sem movimentos de restos a pagar na MSC.")
        else:
            rp = ui.ajustar(rp, ["valor"])
            rp = rp[rp["ano"].isin(sel_anos)]
            pagos = rp[rp["situacao"].str.contains("pagos")]
            ui.grafico(G.barras(pagos, "data", "valor", "situacao", "Restos a pagar pagos no mês (processados e não processados)"),
                       "dp_rp", "siconfi_msc",
                   nota="contas 6.3.1 (RP não processados) e 6.3.2 (RP processados)")
            st.caption("Movimentos das contas 6.3.1 (RP não processados) e 6.3.2 (RP processados) da MSC. Os saldos e "
                       "cancelamentos estão no Anexo 7 do RREO.")

    with abas[5]:
        dims = st.multiselect("Colunas de agrupamento", list(DIMENSOES), default=["Função", "Subfunção"], key="dp_tab_dims")
        cols = [DIMENSOES[x] for x in dims] or ["funcao"]
        t = d.groupby(["ano", *cols], as_index=False)[["empenhado", "liquidado", "pago"]].sum()
        t["% liquidado/empenhado"] = t["liquidado"] / t["empenhado"].where(t["empenhado"] != 0) * 100
        ui.tabela(t, "dp_tab", 
                  fontes=["siconfi_msc"], nota=nota_ano,
                  moeda=["empenhado", "liquidado", "pago"], pct=["% liquidado/empenhado"], ordenar_padrao=est)
