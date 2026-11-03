"""Visão geral: indicadores do exercício, situação fiscal e o que mudou hoje."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import referencias as R
from ms_fiscal import relatorios, ui


def render():
    st.title("Receitas e despesas do Estado de Mato Grosso do Sul")
    S = ui.sigla
    st.caption(f"Execução orçamentária acompanhada a partir das fontes primárias: Portal da Transparência de "
               f"{S('MS')} (diário), Matriz de Saldos Contábeis ({S('MSC')}) do {S('Siconfi')} (mensal), "
               f"{S('RREO')} (bimestral) e {S('RGF')} (quadrimestral).", unsafe_allow_html=True)
    ui.glossario()

    rec, desp = ui.receitas_msc(), ui.despesas_msc()
    meta = ui.portal.meta()

    # ---------------------------------------------------------------- tempo real
    st.subheader("Hoje, no Portal da Transparência", help=ui.ajuda_fontes("portal_desp_orgaos", "portal_rec_simplificada"))
    st.caption(f"Domínio pesquisado: **www.transparencia.ms.gov.br** (Portal da Transparência do Estado, mantido pela "
               f"{S('CGE-MS')}). Os valores não estão no HTML da página nem em arquivo para download: a página "
               f"carrega os números em {S('JSON')} de uma {S('API')} em **gw.sgi.ms.gov.br**, e o painel lê esse JSON "
               "com um navegador automatizado (Playwright). Passe o cursor no ⓘ de cada número para ver o endpoint.",
               unsafe_allow_html=True)
    dm = ui.parquet("portal_despesa_mensal_orgao.parquet")
    rm = ui.parquet("portal_receita_mensal.parquet")
    if dm.empty:
        ui.sem_dados("tempo real do portal", "python coletar.py --portal")
    else:
        ano = int(dm["ano"].max())
        d = dm[dm["ano"] == ano]
        ref = pd.to_datetime(meta.get("data_referencia")) if meta.get("data_referencia") else None
        c = st.columns(4)
        fd = "\n\n" + ui.ajuda_fontes("portal_desp_orgaos")
        ate = f" (até {ref:%d/%m})" if ref is not None else " (até a coleta)"
        ui.metrica(c[0], f"Empenhado em {ano}{ate}", d["empenhado"].sum(),
                   ajuda="Soma dos empenhos do exercício até a data da coleta, mês a mês." + fd)
        ui.metrica(c[1], f"Liquidado em {ano}{ate}", d["liquidado"].sum(), ajuda="Soma das liquidações do exercício até a data da coleta." + fd)
        ui.metrica(c[2], f"Pago em {ano}{ate}", d["pago"].sum(),
                   ajuda="Inclui pagamentos de despesas do exercício e de restos a pagar." + fd)
        if not rm.empty:
            r = rm[rm["ano"] == ano]
            ui.metrica(c[3], f"Receita arrecadada em {ano}{ate}", r["arrecadado"].sum(),
                       ajuda="Receita Simplificada do portal: valores líquidos das deduções (FUNDEB e cota-parte dos municípios).\n\n"
                             + ui.ajuda_fontes("portal_rec_simplificada"))
        st.caption(f"Dados até {ref:%d/%m/%Y} · coletados em {meta.get('coletado_em', '').replace('T', ' ')} · "
                   "detalhe na página **Tempo real**." if ref is not None else "")

    # ---------------------------------------------------------------- MSC
    st.subheader("Execução do exercício pela Matriz de Saldos Contábeis (MSC), mensal",
                 help=R.GLOSSARIO["MSC"] + "\n\n" + ui.ajuda_fontes("siconfi_msc"))
    st.caption(f"A {S('MSC')} é enviada todo mês pelo Estado ao {S('Siconfi')}, sistema da Secretaria do Tesouro "
               f"Nacional ({S('STN')}), em geral até o fim do mês seguinte. É a base mensal mais detalhada e a mesma que "
               f"origina o {S('RREO')}.", unsafe_allow_html=True)
    if rec.empty or desp.empty:
        ui.sem_dados("MSC (Siconfi)", "python coletar.py --siconfi")
        return
    rec = ui.ajustar(rec, ["valor"])
    desp = ui.ajustar(desp, ["empenhado", "liquidado", "pago"])
    ui.explicar_filtros(
        "O único filtro da página é um botão liga/desliga e atua só sobre esta seção, que usa a Matriz de Saldos "
        "Contábeis (MSC) do Siconfi.",
        ui.passos_msc("`conta_contabil`, `natureza_receita` e `natureza_despesa`", "")[:3]
        + ["**Marcação**: o botão não lista opções; o painel marca cada lançamento como intraorçamentário ou não "
           "pelo código da natureza."],
        [("Incluir operações intraorçamentárias", "Liga ou desliga as operações entre órgãos e fundos do próprio "
                                                  "Estado. Na receita, são as naturezas que começam com 7 ou 8; na "
                                                  "despesa, a modalidade 91 (dígitos 3 e 4 de `natureza_despesa`). "
                                                  "Fica desligado por padrão, como no RREO, para não contar o mesmo "
                                                  "recurso duas vezes.")],
        ["**Alcance**: o filtro não muda o bloco \"Hoje, no Portal da Transparência\" nem os limites da LRF.",
         "**Período**: o acumulado vai de janeiro ao último mês com MSC entregue e é comparado com o mesmo período do "
         "ano anterior. Não há filtro de período."],
        fontes=("siconfi_msc",), nota="natureza da receita e da despesa")
    intra = st.toggle("Incluir operações intraorçamentárias", value=False, key="vg_intra",
                      help="Operações entre órgãos e fundos do próprio Estado (natureza 7/8 da receita e modalidade 91 da despesa). "
                           "Ficam fora por padrão, como no RREO, para não contar o mesmo recurso duas vezes.")
    if not intra:
        rec, desp = rec[~rec["intra"]], desp[~desp["intra"]]
    ano = int(rec["ano"].max())
    mes = int(rec.loc[rec["ano"] == ano, "mes"].max())
    acum = lambda df, a: df[(df["ano"] == a) & (df["mes"] <= mes)]  # noqa: E731
    ra, rp = acum(rec, ano), acum(rec, ano - 1)
    da, dp = acum(desp, ano), acum(desp, ano - 1)
    st.caption(f"Acumulado de jan a {G.MESES[mes - 1]}/{ano}, comparado com o mesmo período de {ano - 1}.")
    vs = f"jan a {G.MESES[mes - 1]}/{ano - 1}"
    c = st.columns(5)
    bruta = lambda x: x.loc[~x["deducao"] | x["renuncia"], "valor"].sum()  # noqa: E731
    fm = "\n\n" + ui.ajuda_fontes("siconfi_msc")
    ui.metrica(c[0], "Receita bruta (exceto renúncia)", bruta(ra), bruta(rp),
               ajuda="Receita realizada antes das deduções, sem a renúncia de ICMS que passou a ser registrada como "
                     "receita e dedução em 2026 (MCASP: deduções da receita; LRF, art. 14). Contas 6.2.1.2 e 6.2.1.3.2." + fm, vs=vs)
    ui.metrica(c[1], "Receita líquida", ra["valor"].sum(), rp["valor"].sum(),
               ajuda="Receita realizada menos deduções (FUNDEB, transferências constitucionais a municípios, restituições). "
                     "Contas 6.2.1.2 e 6.2.1.3." + fm, vs=vs)
    ui.metrica(c[2], "Despesa empenhada", da["empenhado"].sum(), dp["empenhado"].sum(), ajuda="Contas 6.2.2.1.3.01 a 6.2.2.1.3.04." + fm, vs=vs)
    ui.metrica(c[3], "Despesa liquidada", da["liquidado"].sum(), dp["liquidado"].sum(), ajuda="Contas 6.2.2.1.3.03 e 6.2.2.1.3.04." + fm, vs=vs)
    ui.metrica(c[4], "Despesa paga", da["pago"].sum(), dp["pago"].sum(), ajuda="Conta 6.2.2.1.3.04." + fm, vs=vs)

    # série mensal receita x despesa
    r_m = rec.groupby(["ano", "mes", "data"], as_index=False)["valor"].sum().rename(columns={"valor": "Receita líquida"})
    d_m = desp.groupby(["ano", "mes", "data"], as_index=False)[["empenhado", "liquidado", "pago"]].sum()
    serie = r_m.merge(d_m, on=["ano", "mes", "data"], how="outer").sort_values("data")
    serie = serie.rename(columns={"empenhado": "Despesa empenhada", "liquidado": "Despesa liquidada", "pago": "Despesa paga"})
    longo = serie.melt(id_vars=["data"], value_vars=["Receita líquida", "Despesa empenhada", "Despesa liquidada", "Despesa paga"],
                       var_name="Série", value_name="R$")
    nota_msc = "contas 6.2.1.2, 6.2.1.3 e 6.2.2.1.3, todos os Poderes"
    col1, col2 = st.columns([3, 2])
    ui.grafico(G.linhas(longo, "data", "R$", "Série", "Receita líquida e despesa por estágio – mensal"), "vg_serie",
               "siconfi_msc", onde=col1, nota=nota_msc)
    serie["Resultado (receita − despesa liquidada)"] = serie["Receita líquida"] - serie["Despesa liquidada"]
    res = serie[serie["ano"] == ano].copy()
    ui.grafico(G.barras(res, "data", "Resultado (receita − despesa liquidada)", titulo=f"Resultado orçamentário mensal – {ano}"),
               "vg_res", "siconfi_msc", onde=col2, nota="receita líquida menos despesa liquidada do mês")

    col1, col2 = st.columns(2)
    periodo = f"jan a {G.MESES[mes - 1]}/{ano}"
    t = ra.groupby("tributo", as_index=False)["valor"].sum().sort_values("valor", ascending=False).head(12)
    ui.grafico(G.barras(t, "tributo", "valor", horizontal=True, titulo=f"Receita líquida por origem – acumulado de {periodo}"),
               "vg_trib", "siconfi_msc", "portal_rec_consolidada", onde=col1,
               nota=f"{periodo}; valores da MSC (contas 6.2.1.2 e 6.2.1.3, campo natureza_receita); só os nomes das "
                    "naturezas vêm da árvore da receita do portal")
    f = da.groupby("funcao", as_index=False)["liquidado"].sum().sort_values("liquidado", ascending=False).head(12)
    ui.grafico(G.barras(f, "funcao", "liquidado", horizontal=True, titulo=f"Despesa liquidada por função – acumulado de {periodo}"),
               "vg_func", "siconfi_msc", onde=col2,
               nota=f"{periodo}; contas 6.2.2.1.3.03 e 6.2.2.1.3.04, campo funcao; nomes das funções da Portaria MOG nº 42/1999")

    # ---------------------------------------------------------------- LRF
    st.subheader("Limites da Lei de Responsabilidade Fiscal (LRF) no último Relatório de Gestão Fiscal (RGF)",
                 help=R.GLOSSARIO["RGF"] + "\n\n" + ui.ajuda_fontes("siconfi_rgf"))
    rgf = ui.relatorio("rgf")
    if rgf.empty:
        ui.sem_dados("RGF", "python coletar.py --siconfi")
    else:
        dt = relatorios.dtp_rcl(rgf)
        cols = st.columns(5)
        for i, (poder, nome) in enumerate(R.NOMES_PODER.items()):
            x = dt[dt["co_poder"] == poder]
            if x.empty:
                continue
            ult = x[(x["exercicio"] == x["exercicio"].max())]
            ult = ult[ult["periodo"] == ult["periodo"].max()]
            v = ult["valor_pct"].sum()
            lim = R.LIMITES_PESSOAL_PODER.get(poder) if poder != "D" else None
            status = ""
            if lim:
                status = ("🔴 acima do máximo" if v > lim else "🟠 acima do prudencial" if v > .95 * lim
                          else "🟡 acima do alerta" if v > .9 * lim else "🟢 dentro dos limites")
            cols[i].metric(f"Pessoal / RCL – {nome}", G.pct(v, 2), help=f"{ult['rotulo'].iat[0]} · limite máximo: "
                           f"{G.pct(lim, 1) if lim else 'não definido no art. 20 da LRF'}.\n\nDespesa total com pessoal "
                           "(DTP) sobre a receita corrente líquida (RCL) ajustada, ambas somadas nos 12 meses encerrados no fim do "
                           "quadrimestre; linha 'DTP / RCL ajustada' do RGF, Anexo 1, "
                           f"do Poder.\n\n{ui.ajuda_fontes('siconfi_rgf')}")
            cols[i].caption(status)
        ui.fonte("siconfi_rgf", nota=f"RGF, Anexo 1 (despesa com pessoal), de cada Poder; {S('DTP')} sobre a "
                 f"{S('RCL')} ajustada, ambas dos 12 meses encerrados no fim do último quadrimestre entregue", valores=False)
        ui.base_legal(lrf=["art19", "art20", "art22", "art59", "art54"], com_glossario=False)
