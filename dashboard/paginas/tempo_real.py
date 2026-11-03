"""Tempo real: séries diárias do Portal da Transparência de MS, coletadas com Playwright."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import ui

FONTES_DIA = ("portal_desp_orgaos", "portal_rec_orgaos")
NOTA_DIA = "uma consulta por dia (dataInicio = dataFim = o dia), somando todos os órgãos do filtro"


def _explicacao(d: pd.DataFrame, est: str) -> None:
    with st.expander("❓ Por que dados diários e como ler este gráfico", expanded=False):
        st.markdown(
            "**Por que dados diários?** A Matriz de Saldos Contábeis (MSC) e o Relatório Resumido da Execução "
            "Orçamentária (RREO) chegam semanas depois do fim do mês ou do bimestre. O Portal da Transparência registra "
            "cada ato no dia em que ele é lançado na contabilidade do Estado. É a única fonte pública que mostra a "
            "execução dentro do mês corrente.\n\n"
            "**Os dados são divulgados em dias diferentes do mês?** Não há um calendário de divulgação. O portal é "
            "atualizado todos os dias com os atos das unidades gestoras, e cada barra soma os atos com data daquele dia: "
            "data do empenho, da liquidação, do pagamento ou do registro da receita. Fins de semana e feriados quase não "
            "têm lançamentos. Lançamentos feitos com atraso entram na data do ato, por isso a coleta relê os últimos 45 "
            "dias a cada execução, e os valores dos dias mais recentes ainda podem mudar.\n\n"
            "**Para que serve?**\n"
            "- Ver em que dias o dinheiro sai: folha de pagamento, repasses e serviço da dívida concentram os pagamentos "
            "em poucos dias. Use o filtro **Órgão** para descobrir quem formou cada pico.\n"
            "- Acompanhar o caixa do mês: receita arrecadada × pagamentos no mesmo período.\n"
            "- Antecipar o que a MSC e o RREO vão mostrar quando o mês fechar.\n"
            "- Achar eventos fora do padrão: um empenho muito grande, anulações em bloco no fim do exercício, um dia "
            "sem receita.\n\n"
            "**Cuidados.** O pago do portal inclui restos a pagar de anos anteriores. A receita aqui é a da Pesquisa de "
            "Receita, por órgão arrecadador, e inclui receitas próprias de autarquias e fundos.\n\n"
            "**O que significam valores negativos?** Um valor abaixo de zero indica que, naquele dia, as anulações e "
            "estornos superaram os lançamentos novos:\n"
            "- **Anulação de empenho**: cancela total ou parcialmente um empenho, por exemplo porque o serviço custou "
            "menos que o reservado ou o contrato foi rescindido. Reduz o empenhado na data da anulação, e o saldo volta "
            "para a dotação (Lei nº 4.320/1964, art. 38; MCASP, Parte I).\n"
            "- **Estorno**: lançamento que desfaz um registro feito com erro, como uma liquidação ou um pagamento "
            "lançado em duplicidade ou na classificação errada.\n"
            "- **Na receita**: restituições e retificações reduzem o arrecadado.\n\n"
            "Como o portal soma os atos pela data, o dia do estorno ou da anulação fica negativo mesmo que o lançamento "
            "original seja de outro dia.")
        dia = d.groupby("dia")[est].sum()
        if len(dia) >= 5:
            fds = pd.to_datetime(dia.index).dayofweek >= 5
            top = dia.sort_values(ascending=False).head(3)
            lider = (d[d["dia"].isin(top.index)].sort_values(est, ascending=False).drop_duplicates("dia")
                     .set_index("dia")["orgao"])
            itens = "; ".join(f"{pd.Timestamp(k):%d/%m} ({G.brl(v)}, maior parcela: {lider.get(k, '–')})" for k, v in top.items())
            texto = (f"**No período e nos filtros escolhidos:** despesa ({est}) de {G.brl(dia[~fds].sum())} em dias úteis "
                     f"e {G.brl(dia[fds].sum())} em sábados e domingos; os três maiores dias foram {itens}.")
            st.markdown(texto.replace("$", "\\$"))


def _origem_filtros(dias: list) -> None:
    ini, fim = pd.Timestamp(dias[0]), pd.Timestamp(dias[-1])
    ui.explicar_filtros(
        "As opções vêm de campos do JSON devolvido pela API do Portal da Transparência de MS (gw.sgi.ms.gov.br), lida "
        "com um navegador automatizado (Playwright). Não vêm de planilha nem de arquivo para download.",
        ["**Coleta** (`python coletar.py --portal`): o painel abre www.transparencia.ms.gov.br e faz, para **cada dia** "
         "dos últimos 45 dias do exercício, uma consulta com dataInicio = dataFim = o dia: `despesapordataorgaos` "
         "(despesa) e `pesquisadereceitas` (receita).",
         "**Campos usados**: `orgao`, `codigo` (unidade gestora), `empenhado`, `liquidado` e `pago` na despesa; "
         "`orgao` e `arrecadado` na receita.",
         "**Histórico**: cada coleta atualiza os dias já gravados e acrescenta os novos em "
         "`dados/dashboard/portal_despesa_diaria_orgao.parquet` e `portal_receita_diaria_orgao.parquet`.",
         f"**Montagem das opções**: a página usa todos os dias gravados (hoje, {len(dias)} dias, de {ini:%d/%m/%Y} a "
         f"{fim:%d/%m/%Y})."],
        [("Período", "Dias com dados de despesa no histórico. O controle começa nos últimos 30 dias."),
         ("Estágio", "Fixo. Escolhe qual campo do JSON de despesa é somado: `pago`, `liquidado` ou `empenhado`."),
         ("Órgão", "Valores distintos do campo `orgao` da despesa, em todos os dias gravados, em ordem alfabética. "
                   "O mesmo filtro é aplicado à receita.")],
        ["**Órgão na receita**: a receita é registrada pelo órgão **arrecadador**, e o nome pode não coincidir com o da "
         "despesa. Um órgão escolhido pode ter despesa e nenhuma receita.",
         "**Dias recentes**: os valores ainda podem mudar, porque lançamentos atrasados entram na data do ato e a coleta "
         "relê os últimos 45 dias.",
         "**Despesa mensal por órgão** (fim da página): segue só o filtro Estágio. Usa uma consulta por mês "
         "(`portal_despesa_mensal_orgao.parquet`) e mostra os últimos 12 meses de todos os órgãos.",
         "**Grafia do portal**: os nomes dos órgãos seguem a grafia do portal, sem correção pelo painel."],
        fontes=("portal_desp_orgaos", "portal_rec_orgaos"), nota="campos do JSON listados acima, em todos os dias gravados")


def render():
    S = ui.sigla
    st.title("Tempo real – Portal da Transparência")
    meta = ui.portal.meta()
    st.caption(f"O portal da {S('CGE-MS')} (www.transparencia.ms.gov.br) declara atualização diária \"em decorrência dos "
               f"atos praticados pelas Unidades Gestoras\" ({S('LRF')}, arts. 48, §1º, II, e 48-A). O painel faz as "
               f"mesmas consultas das telas Despesas e Receitas com um navegador automatizado (Playwright), lê o "
               f"{S('JSON')} devolvido pela {S('API')} do portal em gw.sgi.ms.gov.br e guarda o histórico localmente.",
               unsafe_allow_html=True)
    ui.base_legal(["despesa_estagios", "receita_estagios"], ["art48", "art48a"])

    c = st.columns([3, 1])
    c[0].info(f"Última coleta: **{meta.get('coletado_em', 'nunca').replace('T', ' ')}** · dados até "
              f"**{meta.get('data_referencia', '—')}**", icon="⏱️")
    if c[1].button("Coletar agora", type="primary", key="tr_coletar"):
        with st.spinner("Abrindo o portal com Playwright e coletando (≈2–4 min)…"):
            rc, log = ui.executar_coleta(["--portal"])
        st.cache_data.clear()
        (st.success if rc == 0 else st.error)("Coleta concluída." if rc == 0 else "Falha na coleta.")
        with st.expander("Log"):
            st.code(log)

    dd = ui.parquet("portal_despesa_diaria_orgao.parquet")
    rd = ui.parquet("portal_receita_diaria_orgao.parquet")
    if dd.empty:
        ui.sem_dados("tempo real", "python coletar.py --portal")
        return

    dias = sorted(dd["dia"].unique())
    _origem_filtros(dias)
    f = st.columns([2, 1.5, 2])
    ini, fim = f[0].select_slider("Período", options=dias, value=(dias[max(0, len(dias) - 30)], dias[-1]),
                                  format_func=lambda d: pd.Timestamp(d).strftime("%d/%m"), key="rt_periodo")
    est = f[1].radio("Estágio", ["pago", "liquidado", "empenhado"], horizontal=True, key="rt_est")
    orgaos = ui.filtro_multiplo(f[2], "Órgão", dd["orgao"], "rt_org")
    d = ui.aplicar_filtro(dd[(dd["dia"] >= ini) & (dd["dia"] <= fim)], "orgao", orgaos)
    r = ui.aplicar_filtro(rd[(rd["dia"] >= ini) & (rd["dia"] <= fim)], "orgao", orgaos) if not rd.empty else rd

    per = f"{pd.Timestamp(ini):%d/%m/%Y} a {pd.Timestamp(fim):%d/%m/%Y}"
    fd = ui.ajuda_fontes("portal_desp_orgaos")
    fr = ui.ajuda_fontes("portal_rec_orgaos")
    k = st.columns(4)
    k[0].metric(f"Despesa {est} no período", G.brl(d[est].sum()),
                help=f"Soma da despesa {est} de {per}, todos os órgãos do filtro. {NOTA_DIA.capitalize()}.\n\n{fd}")
    dia_max = d.groupby("dia")[est].sum()
    if not dia_max.empty:
        k[1].metric(f"Maior dia ({pd.Timestamp(dia_max.idxmax()):%d/%m})", G.brl(dia_max.max()),
                    help=f"Dia de maior despesa {est} entre {per}.\n\n{fd}")
    if not r.empty:
        k[2].metric("Receita arrecadada no período", G.brl(r["arrecadado"].sum()),
                    help=f"Pesquisa de Receita por órgão arrecadador, de {per}; inclui receitas próprias de autarquias "
                         f"e fundos.\n\n{fr}")
        k[3].metric("Saldo do período (receita − despesa)", G.brl(r["arrecadado"].sum() - d[est].sum()),
                    help=f"Receita arrecadada menos despesa {est} no mesmo período e filtro. Não é o resultado "
                         f"orçamentário oficial, que vem do RREO.\n\n{fr}\n\n---\n\n{fd}")

    st.subheader("Movimento diário", help=ui.ajuda_fontes(*FONTES_DIA))
    _explicacao(d, est)
    serie = d.groupby("dia", as_index=False)[["empenhado", "liquidado", "pago"]].sum()
    if not r.empty:
        serie = serie.merge(r.groupby("dia", as_index=False)["arrecadado"].sum(), on="dia", how="outer").fillna(0)
    longo = serie.melt("dia", [c for c in ("arrecadado", "empenhado", "liquidado", "pago") if c in serie], var_name="série", value_name="R$")
    longo["série"] = longo["série"].map({"arrecadado": "Receita arrecadada", "empenhado": "Empenhado", "liquidado": "Liquidado", "pago": "Pago"})
    ui.grafico(G.barras(longo, "dia", "R$", "série", "Movimento diário (dias úteis concentram os lançamentos)", empilhar=False,
                        ordem={"série": ["Receita arrecadada", "Empenhado", "Liquidado", "Pago"]},
                        cores={"Receita arrecadada": G.CORES[5], "Empenhado": G.CORES[0], "Liquidado": G.CORES[1], "Pago": G.CORES[2]}),
               "rt_diario", *FONTES_DIA,
               nota=f"{NOTA_DIA}. Valores negativos: anulações e estornos superaram os lançamentos do dia (veja a explicação acima)")

    c1, c2 = st.columns(2)
    og = d.groupby("orgao", as_index=False)[est].sum().sort_values(est, ascending=False)
    ui.grafico(G.barras(og.head(15), "orgao", est, horizontal=True, altura=520, titulo=f"Órgãos – despesa ({est}) no período"),
               "rt_org_bar", "portal_desp_orgaos", onde=c1, nota=per)
    if not r.empty:
        ro = r.groupby("orgao", as_index=False)["arrecadado"].sum().sort_values("arrecadado", ascending=False)
        ui.grafico(G.barras(ro.head(15), "orgao", "arrecadado", horizontal=True, altura=520,
                            titulo="Órgãos arrecadadores – receita no período"), "rt_rec", "portal_rec_orgaos", onde=c2, nota=per)

    st.subheader("Despesa mensal por órgão nos últimos 12 meses (mês corrente parcial)",
                 help=ui.ajuda_fontes("portal_desp_orgaos"))
    dm = ui.parquet("portal_despesa_mensal_orgao.parquet")
    if dm.empty:
        return
    dm = dm.assign(data=pd.to_datetime(dict(year=dm["ano"], month=dm["mes"], day=1)))
    meses = sorted(dm["data"].unique())[-12:]
    x = dm[dm["data"].isin(meses)].copy()
    top = G.top_n_outros(x, "orgao", est, 7).groupby(["data", "orgao"], as_index=False)[est].sum().sort_values("data")
    ordem = top.groupby("orgao")[est].sum().sort_values(ascending=False).index.tolist()
    ordem = [o for o in ordem if o != "Outros"] + (["Outros"] if "Outros" in ordem else [])
    ini_m, fim_m = pd.Timestamp(meses[0]), pd.Timestamp(meses[-1])
    nota_m = (f"{ini_m:%m/%Y} a {fim_m:%m/%Y}, uma consulta por mês (dataInicio = dia 1, dataFim = último dia do mês "
              f"ou a data da coleta, no mês corrente)")
    ui.grafico(G.barras(top, "data", est, "orgao", f"Despesa ({est}) por mês e órgão – últimos 12 meses",
                        ordem={"orgao": ordem}, cores=G.mapa_cores(ordem)), "rt_mensal", "portal_desp_orgaos", nota=nota_m)
    tab = x.pivot_table(index="orgao", columns="data", values=est, aggfunc="sum").fillna(0)
    tab.columns = [f"{pd.Timestamp(c):%m/%Y}" for c in tab.columns]
    tab["Total"] = tab.sum(axis=1)
    tab = tab.reset_index().rename(columns={"orgao": "Órgão"})
    ui.tabela(tab, "rt_tab", moeda=[c for c in tab.columns if c != "Órgão"], ordenar_padrao="Total",
              fontes=["portal_desp_orgaos"], nota=f"despesa {est}; " + nota_m)
