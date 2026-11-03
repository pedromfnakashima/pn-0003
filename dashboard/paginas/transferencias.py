"""Transferências a municípios, fundos, consórcios e instituições privadas."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import ui


def render():
    st.title("Transferências")
    st.caption("O que o Estado entrega a municípios, fundos, consórcios e entidades: repasses constitucionais da receita "
               "(ICMS, IPVA, IPI-Exportação), transferências por modalidade de aplicação e os maiores beneficiários.")
    ui.base_legal(["transferencias", "despesa_modalidade", "receita_deducoes"], ["art25", "art2iv"],
                  extra=["CF, art. 158, III e IV: 50% do IPVA e 25% do ICMS pertencem aos municípios.",
                         "CF, art. 159, §3º: 25% da cota estadual do IPI-Exportação vai aos municípios.",
                         "FUNDERSUL: Fundo de Desenvolvimento do Sistema Rodoviário de MS (Lei estadual nº 1.963/1999); "
                         "parte é repassada aos municípios."])

    abas = st.tabs(["🏘️ Repasses constitucionais a municípios", "🔀 Por modalidade de aplicação (MSC)", "🏥 Fundo a fundo e entidades"])

    with abas[0]:
        rp = ui.parquet("repasses_municipios.parquet")
        if rp.empty:
            ui.sem_dados("repasses a municípios", "python coletar.py --repasses")
        else:
            rp = ui.ajustar(rp, ["valor"])
            ui.explicar_filtros(
                "As opções vêm de colunas de arquivos CSV de dados abertos, não de planilha nem de API.",
                ["**Coleta** (`python coletar.py --repasses`): baixa o arquivo CSV de cada mês do conjunto "
                 "[Repasses dos Municípios](https://www.dados.ms.gov.br/dataset/repasses-dos-municipios) (SEFAZ-MS), "
                 "no portal de dados abertos dados.ms.gov.br (CKAN).",
                 "**Colunas usadas**: `Tipo_Repasse`, `Municipio`, `Data_Contabilização` e `Valor_Total`.",
                 "**Limpeza**: tira o prefixo \"PREFEITURA MUNICIPAL DE \" do município e grava tudo em "
                 "`dados/dashboard/repasses_municipios.parquet`.",
                 "**Montagem das opções**: valores distintos de cada coluna em todos os meses carregados, em ordem "
                 "alfabética."],
                [("Exercícios", "Anos dos arquivos mensais carregados (o ano vem do nome do arquivo)."),
                 ("Tipo de repasse", "Coluna `Tipo_Repasse` do CSV (ICMS, IPVA, IPI-Exportação, FUNDERSUL, CIDE)."),
                 ("Município", "Coluna `Municipio` do CSV, sem o prefixo \"PREFEITURA MUNICIPAL DE \"."),
                 ("Municípios no gráfico", "Número de 10 a 79: quantos municípios, do maior ao menor, aparecem no "
                                           "gráfico de barras.")],
                ["**Lacunas da fonte**: há meses sem arquivo ou sem as linhas de ICMS; o painel lista quais logo abaixo "
                 "dos filtros.",
                 "**Grafia da fonte**: os nomes seguem a grafia da SEFAZ."],
                fontes=("ckan_repasses",), nota="colunas do CSV listadas acima, em todos os meses carregados")
            f = st.columns([1.3, 2, 2])
            anos = sorted(rp["ano"].unique())
            sel = f[0].multiselect("Exercícios", anos, default=anos[-2:], key="tr_anos")
            tipos = ui.filtro_multiplo(f[1], "Tipo de repasse", rp["tipo"], "tr_tipo")
            munis = ui.filtro_multiplo(f[2], "Município", rp["municipio"], "tr_mun")
            d = ui.aplicar_filtro(ui.aplicar_filtro(rp[rp["ano"].isin(sel)], "tipo", tipos), "municipio", munis)
            d = d.assign(data=pd.to_datetime(dict(year=d["ano"], month=d["mes"], day=1)))
            # lacunas da própria fonte: meses sem arquivo ou sem as linhas de ICMS
            todos = pd.period_range(d["data"].min(), d["data"].max(), freq="M")
            com_icms = set(rp.loc[rp["tipo"].str.contains("ICMS"), ["ano", "mes"]].itertuples(index=False, name=None))
            faltam = [f"{p.month:02d}/{p.year}" for p in todos if (p.year, p.month) not in com_icms]
            if faltam:
                st.warning("Lacunas na fonte (dados.ms.gov.br): meses sem arquivo publicado ou sem as linhas de ICMS/IPVA – "
                           + ", ".join(faltam) + ". Os totais desses meses estão subestimados.", icon="⚠️")
            per = ui.periodo(d)
            st.caption(f"Período: **{per}**. Totais, ranking e percentuais somam todos esses meses.")
            c = st.columns(3)
            frp = ui.ajuda_fontes("ckan_repasses")
            c[0].metric("Total repassado no período", G.brl(d["valor"].sum()), help=f"{per}.\n\n{frp}")
            c[1].metric("Municípios", d["municipio"].nunique(), help=frp)
            ult = d[d["data"] == d["data"].max()]
            c[2].metric(f"Último mês ({d['data'].max():%m/%Y})", G.brl(ult["valor"].sum()), help=frp)
            m = d.groupby(["data", "tipo"], as_index=False)["valor"].sum()
            ui.grafico(G.barras(m, "data", "valor", "tipo", "Repasses mensais por tipo"), "tr_mes", "ckan_repasses",
                   nota="arquivos mensais repasses-dos-municipios-MM_AAAA")
            pm = d.groupby("municipio", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
            n = st.slider("Municípios no gráfico", 10, 79, 25, key="tr_n")
            ui.grafico(G.barras(pm.head(n), "municipio", "valor", horizontal=True, altura=max(420, 22 * n),
                                     titulo="Repasses por município no período"), "tr_mun_bar", "ckan_repasses",
                   nota=f"arquivos mensais repasses-dos-municipios-MM_AAAA; soma de {per}")
            larga = d.pivot_table(index="municipio", columns="tipo", values="valor", aggfunc="sum").fillna(0)
            larga["Total"] = larga.sum(axis=1)
            larga["% do total repassado"] = larga["Total"] / larga["Total"].sum() * 100
            larga = larga.reset_index()
            ui.tabela(larga, "tr_tab", 
                      fontes=["ckan_repasses"],
                      nota=f"arquivos mensais repasses-dos-municipios-MM_AAAA; soma de {per}; '% do total repassado' = "
                           "parte do município no total repassado a todos os municípios dos filtros no período",
                      moeda=[c for c in larga.columns if c not in ("municipio", "% do total repassado")],
                      pct=["% do total repassado"], ordenar_padrao="Total")
            rec = ui.receitas_msc()
            if not rec.empty:
                ded = rec[(rec["tipo"] == "Dedução – transferências a municípios") & rec["ano"].isin(sel)]
                ded = ui.ajustar(ded, ["valor"]).groupby(["ano", "tributo"], as_index=False)["valor"].sum()
                ded["valor"] = -ded["valor"]
                ded["ano"] = ded["ano"].astype(str)
                ui.grafico(G.barras(ded, "tributo", "valor", "ano", "Conferência: dedução da receita para municípios na MSC (6.2.1.3.1.02)",
                                         empilhar=False), "tr_ded", "siconfi_msc",
                   nota="conta 6.2.1.3.1.02 (dedução: transferências a municípios); cada barra soma os meses de MSC "
                        f"carregados do exercício ({ui.periodo(rec[rec['ano'].isin(sel)], somados=False)})")
                st.caption("Na contabilidade estadual, a parcela municipal é registrada como dedução da receita (MCASP), "
                           "e não como despesa. Diferenças em relação aos repasses decorrem de datas de crédito e de "
                           "juros/multas/dívida ativa incluídos na base.")

    with abas[1]:
        desp = ui.despesas_msc()
        if desp.empty:
            ui.sem_dados("MSC", "python coletar.py --siconfi")
        else:
            desp = ui.ajustar(desp, ["empenhado", "liquidado", "pago"])
            ui.explicar_filtros(
                "As opções vêm de campos da Matriz de Saldos Contábeis (MSC), lida na API do Siconfi, agrupados pelo "
                "painel. Nenhuma vem de planilha nem de arquivo CSV.",
                ui.passos_msc("`conta_contabil` (estágio) e `natureza_despesa` (dígitos 3 e 4 = modalidade de aplicação)",
                              "o painel junta ao código da modalidade o nome do MCASP e um **destino** que reúne "
                              "modalidades parecidas (ex.: 40, 41, 42, 45 e 46 = Transferências a Municípios)."),
                [("Exercícios", "Anos dos arquivos MSC carregados."),
                 ("Estágio", "Fixo. **Empenhada** = contas 6.2.2.1.3.01 a .04; **liquidada** = .03 + .04; **paga** = .04."),
                 ("Destino", "**Agrupamento do painel** (`GRUPO_MODALIDADE` em `ms_fiscal/referencias.py`) das "
                             "modalidades presentes nos exercícios escolhidos. As aplicações diretas (90 e afins) ficam "
                             "fora, porque não são transferências.")],
                ["**Intraorçamentárias**: a modalidade 91 aparece como um destino próprio (entre órgãos e fundos do "
                 "próprio Estado). Desmarque-a para ver só o que sai do Estado.",
                 "**Sem beneficiário**: a MSC não identifica quem recebe. Os beneficiários estão na aba \"Fundo a fundo e "
                 "entidades\"."],
                fontes=("siconfi_msc",), nota="modalidade de aplicação da natureza da despesa")
            f = st.columns([1.3, 1.5, 2])
            anos = sorted(desp["ano"].unique())
            sel = f[0].multiselect("Exercícios", anos, default=anos[-2:], key="tr_m_anos")
            est = {"Empenhada": "empenhado", "Liquidada": "liquidado", "Paga": "pago"}[
                f[1].radio("Estágio", ["Empenhada", "Liquidada", "Paga"], index=1, horizontal=True, key="tr_m_est")]
            d = desp[desp["ano"].isin(sel) & (desp["grupo_modalidade"] != "Aplicações diretas")]
            grupos = ui.filtro_multiplo(f[2], "Destino", d["grupo_modalidade"], "tr_m_g")
            d = ui.aplicar_filtro(d, "grupo_modalidade", grupos)
            per_m = ui.periodo(d)
            g = d.groupby(["data", "grupo_modalidade"], as_index=False)[est].sum()
            ui.grafico(G.barras(g, "data", est, "grupo_modalidade", "Transferências mensais por destino (exclui aplicações diretas)"),
                       "tr_m_bar", "siconfi_msc",
                   nota="contas de despesa 6.2.2.1.3, por modalidade de aplicação")
            fm = d.groupby(["grupo_modalidade", "modalidade", "funcao"], as_index=False)[est].sum()
            ui.grafico(G.treemap(fm, ["grupo_modalidade", "modalidade", "funcao"], est, "Destino › modalidade › função",
                                 raiz="Transferências totais", pct_de=f"das transferências totais de {per_m}"),
                       "tr_m_tree", "siconfi_msc",
                   nota=f"contas de despesa 6.2.2.1.3, por modalidade de aplicação; soma de {per_m}; o % é sobre o total "
                        "transferido nos destinos escolhidos (sem aplicações diretas)")
            t = d.groupby(["ano", "modalidade", "funcao", "elemento"], as_index=False)[["empenhado", "liquidado", "pago"]].sum()
            ui.tabela(t, "tr_m_tab", 
                      fontes=["siconfi_msc"], nota="contas de despesa 6.2.2.1.3, por modalidade de aplicação; cada linha "
                                                   f"soma os meses do seu exercício ({ui.periodo(d, somados=False)})",
                      moeda=["empenhado", "liquidado", "pago"], ordenar_padrao=est)

    with abas[2]:
        cr = ui.credores()
        if cr.empty:
            ui.sem_dados("despesas por credor", "python coletar.py --credores")
        else:
            cr = ui.ajustar(cr, ["empenhado", "liquidado", "pago"])
            anos = sorted(cr["ano"].unique())
            ui.explicar_filtros(
                "As opções vêm de colunas de arquivos CSV de dados abertos, não de planilha nem de API.",
                ["**Coleta** (`python coletar.py --credores`): baixa um arquivo por mês, `despesas-MM_AAAA.csv`, do "
                 "conjunto [Despesas por Credor – Mensal](https://www.dados.ms.gov.br/dataset/despesas-por-credor-mensal) "
                 "(SEFAZ-MS), em dados.ms.gov.br (CKAN).",
                 "**Colunas usadas**: `Modalidade`, `Credor`, `Empenhado`, `Liquidado` e `Pago`.",
                 "**Limpeza**: a mesma da página Órgãos e fornecedores (registros quebrados, nomes cortados, grafias).",
                 "**Montagem das opções**: valores distintos da coluna `Modalidade` em todos os meses carregados."],
                [("Exercícios", "Anos dos arquivos mensais carregados (o ano vem do nome do arquivo)."),
                 ("Modalidades", "Coluna `Modalidade` do CSV, **exceto** as que contêm \"Aplica\" (aplicações "
                                 "diretas, que não são transferências). Começa com as que contêm \"Munic\". "
                                 "Sem nenhuma escolhida, valem todas as listadas.")],
                ["**Sem código**: o CSV traz só o nome da modalidade, na grafia da SEFAZ, e não o código do MCASP.",
                 "**Diferença da aba anterior**: aqui os nomes vêm do CSV; na aba \"Por modalidade\", vêm do MCASP."],
                fontes=("ckan_credores",), nota="coluna Modalidade, em todos os meses carregados")
            f = st.columns([1.3, 3])
            sel = f[0].multiselect("Exercícios", anos, default=anos[-1:], key="tr_c_anos")
            mods = [m for m in cr["modalidade"].cat.categories if "Aplica" not in m]
            esc = f[1].multiselect("Modalidades", mods, default=[m for m in mods if "Munic" in m], key="tr_c_mod")
            x = cr[cr["ano"].isin(sel) & cr["modalidade"].isin(esc or mods)]
            r = x.groupby(["credor", "modalidade"], as_index=False, observed=True)[["empenhado", "liquidado", "pago"]].sum()
            r = r.sort_values("pago", ascending=False)
            per_c = ui.periodo(x)
            ui.grafico(G.barras(r.head(25).assign(rot=lambda z: z["credor"].astype(str).str.slice(0, 45)), "rot", "pago",
                                     "modalidade", horizontal=True, altura=640, titulo="Maiores beneficiários de transferências (pago)"),
                                                "tr_c_bar", "ckan_credores",
                   nota=f"arquivos mensais despesas-MM_AAAA.csv, modalidades de transferência; soma de {per_c}")
            ui.tabela(r, "tr_c_tab", 
                      fontes=["ckan_credores"],
                      nota=f"arquivos mensais despesas-MM_AAAA.csv, modalidades de transferência; soma de {per_c}",
                      moeda=["empenhado", "liquidado", "pago"], ordenar_padrao="pago")
