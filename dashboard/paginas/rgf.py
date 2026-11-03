"""RGF – Relatório de Gestão Fiscal (LRF, arts. 54 e 55), quadrimestral, por Poder."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import referencias as R
from ms_fiscal import relatorios as REL
from ms_fiscal import ui
from paginas import rgf_anexos, rgf_resumo

ANEXOS = {
    "RGF-Anexo 01": "Despesa com pessoal",
    "RGF-Anexo 02": "Dívida consolidada líquida",
    "RGF-Anexo 03": "Garantias e contragarantias",
    "RGF-Anexo 04": "Operações de crédito",
    "RGF-Anexo 05": "Disponibilidade de caixa e restos a pagar (3º quadrimestre)",
    "RGF-Anexo 06": "Demonstrativo simplificado",
}
PESSOAL = {
    "DespesaComPessoalAtivoBruta": "Pessoal ativo",
    "DespesaComPessoalInativoEPensionistasBruta": "Inativos e pensionistas",
    "DespesaComPessoalDecorrenteDeTerceirizacaoPorSubstituicaoBruta": "Terceirização substitutiva (art. 18, §1º)",
}


COLETA = ("**Coleta** (`python coletar.py --siconfi`): para cada quadrimestre entregue e para cada um dos 5 Poderes e "
          "órgãos autônomos, o painel consulta a API `/rgf` em apidatalake.tesouro.gov.br (an_exercicio, nr_periodo = "
          "quadrimestre, in_periodicidade=Q, co_poder = E, L, J, M ou D, co_esfera=E, id_ente=50) e grava a resposta "
          "JSON em `dados/dashboard/rgf_AAAA_Q_P.parquet`.")
PODERES_TXT = ("Lista fixa dos 5 valores do parâmetro `co_poder` da API: Executivo (E), Legislativo (L), Judiciário (J), "
               "Ministério Público (M) e Defensoria Pública (D). Os nomes são do painel.")


def render():
    st.title("RGF – Relatório de Gestão Fiscal")
    st.caption("Emitido por quadrimestre por cada Poder e órgão autônomo. Verifica os limites da LRF e das resoluções do Senado.")
    ui.base_legal(lrf=["art54", "art18", "art19", "art20", "art22", "art23", "art59", "art29", "art32", "art40", "art42"],
                  extra=["Res. do Senado nº 40/2001: dívida consolidada líquida dos Estados ≤ 2 vezes a RCL.",
                         "Res. do Senado nº 43/2001: operações de crédito ≤ 16% da RCL no ano; garantias ≤ 22% da RCL.",
                         "Estrutura e conceitos: Manual de Demonstrativos Fiscais (MDF) da STN, Parte III – RGF."])
    df = ui.relatorio("rgf")
    if df.empty:
        ui.sem_dados("RGF", "python coletar.py --siconfi")
        return

    abas = st.tabs(["🧭 Resumo", "🎯 Previsões", "📚 Anexos", "legado_Despesa com pessoal",
                    "legado_Dívida, garantias e crédito", "legado_Anexo completo"])

    with abas[0]:
        rgf_resumo.render()

    with abas[1]:
        st.info("Em construção.")

    with abas[2]:
        rgf_anexos.render()

    with abas[3]:
        ui.explicar_filtros(
            "A única opção desta aba é o Poder, que corresponde a um parâmetro da API do Siconfi (endpoint `/rgf`).",
            [COLETA,
             "**Campos usados**: `anexo`, `cod_conta`, `coluna`, `exercicio`, `periodo` e `valor` do Anexo 1 "
             "(despesa com pessoal)."],
            [("Poder / órgão", PODERES_TXT + " O Legislativo soma a Assembleia Legislativa e o Tribunal de Contas.")],
            ["**Limites**: as linhas de alerta, prudencial e máximo são do painel (LRF, arts. 20, 22 e 59), não do JSON.",
             "**Defensoria**: o RGF da Defensoria não traz o percentual sobre a RCL, por isso o gráfico fica vazio.",
             "**Dívida, garantias e crédito**: a outra aba não tem filtros e mostra só o Poder Executivo."],
            fontes=("siconfi_rgf",), nota="parâmetro co_poder e Anexo 1")
        dt = REL.dtp_rcl(df)
        poder = st.radio("Poder / órgão", list(R.NOMES_PODER), format_func=R.NOMES_PODER.get, horizontal=True, key="rg_poder")
        x = dt[dt["co_poder"] == poder].groupby(["exercicio", "periodo", "rotulo"], as_index=False)[["valor_pct", "valor_valor"]].sum()
        lim = R.LIMITES_PESSOAL_PODER.get(poder) if poder != "D" else None
        limites = {"Alerta (90%)": lim * .9, "Prudencial (95%)": lim * .95, "Máximo": lim} if lim else {}
        if x.empty:
            st.caption("Sem percentual sobre a RCL para este Poder/órgão: o RGF da Defensoria Pública de MS publica a "
                       "despesa com pessoal, mas não a apura como % da RCL (a LRF não fixa limite próprio no art. 20).")
        else:
            c1, c2 = st.columns([3, 1])
            ui.grafico(G.indicador_limite(x, "rotulo", "valor_pct", limites,
                                               f"Despesa total com pessoal / RCL ajustada – {R.NOMES_PODER[poder]}"),
                                                          "rg_dtp", "siconfi_rgf", onde=c1,
                   nota="RGF, Anexo 1 (despesa com pessoal) do Poder escolhido, linha 'DTP / RCL ajustada': em cada "
                        "quadrimestre, DTP e RCL ajustada são somadas nos 12 meses encerrados no fim do quadrimestre")
            u = x.iloc[-1]
            c2.metric(f"DTP / RCL – {u['rotulo']}", G.pct(u["valor_pct"], 2),
                      help="Último quadrimestre entregue; DTP e RCL ajustada dos 12 meses encerrados no fim dele.")
            c2.metric("DTP (12 meses até o fim do quadrimestre)", G.brl(u["valor_valor"]))
            if lim:
                folga = lim - u["valor_pct"]
                c2.metric("Folga até o limite máximo", f"{folga:,.2f}".replace(".", ",") + " p.p.", help="Pontos percentuais da RCL ajustada.")
                c2.caption("Limites: LRF, art. 20, II (máximo), art. 22 (prudencial: vedações) e art. 59, §1º, II (alerta).")
            else:
                c2.caption("A LRF não fixa limite próprio para a Defensoria no art. 20; o relatório é publicado para transparência.")
            if poder == "L":
                st.caption("Legislativo = Assembleia Legislativa + Tribunal de Contas (soma dos dois relatórios).")
        # composição mensal (12 meses móveis) do Executivo
        partes = []
        sub = df[df["co_poder"] == poder]
        for cod, nome in PESSOAL.items():
            s = REL.mensal_mr(sub, "RGF-Anexo 01", cod, 4)
            if not s.empty:
                partes.append(s.assign(componente=nome))
        if partes:
            comp = pd.concat(partes)
            comp = ui.ajustar(comp.assign(ano=comp["data"].dt.year, mes=comp["data"].dt.month), ["valor"])
            ui.grafico(G.barras(comp, "data", "valor", "componente", f"Despesa bruta com pessoal por mês – {R.NOMES_PODER[poder]}"),
                       "rg_comp", "siconfi_rgf",
                   nota="RGF, Anexo 1 do Poder escolhido, colunas mensais MR-11 a MR (despesa bruta com pessoal liquidada no mês)")
            st.caption("O RGF mede a despesa bruta com pessoal (com encargos patronais e 13º), diferente da folha líquida publicada "
                       "no portal. Para o limite, deduzem-se as despesas do art. 19, §1º (indenizações, decisões judiciais de "
                       "períodos anteriores, inativos custeados com recursos vinculados).")
        tab = dt.pivot_table(index="rotulo", columns="co_poder", values="valor_pct", aggfunc="sum").rename(columns=R.NOMES_PODER)
        st.markdown("**% da RCL por Poder e quadrimestre**")
        ui.tabela(tab.reset_index(), "rg_dtp_tab", 
                  fontes=["siconfi_rgf"], nota="RGF, Anexo 1 de cada Poder, linha 'DTP / RCL ajustada' (12 meses "
                                               "encerrados no fim de cada quadrimestre)",
                  pct=list(tab.columns), ordenar_padrao="rotulo")

    with abas[4]:
        e = df[df["co_poder"] == "E"]
        a2 = REL.coluna_quadrimestre_atual(e[e["anexo"] == "RGF-Anexo 02"])
        dcl = a2[a2["cod_conta"] == "PercentualDaDCLSobreARCL"].groupby(["exercicio", "periodo"], as_index=False)["valor"].sum()
        dcl["rotulo"] = REL.rotulo_periodo(dcl, "rgf")
        c1, c2 = st.columns(2)
        if not dcl.empty:
            ui.grafico(G.indicador_limite(dcl, "rotulo", "valor", {"Alerta (90%)": 180.0, "Limite (Res. SF 40/2001)": 200.0},
                                               "Dívida consolidada líquida / RCL ajustada"), "rg_dcl", "siconfi_rgf", onde=c1,
                   nota="RGF do Poder Executivo, Anexo 2 (dívida consolidada líquida), linha '% da DCL sobre a RCL ajustada': "
                        "saldo da DCL no fim de cada quadrimestre sobre a RCL ajustada dos 12 meses encerrados nele")
        val = a2[a2["cod_conta"].isin(["DividaConsolidada", "DeducoesDaDividaConsolidada", "DividaConsolidadaLiquida"])]
        if not val.empty:
            val = val.assign(rotulo=REL.rotulo_periodo(val, "rgf"))
            ui.grafico(G.linhas(val.drop_duplicates(["rotulo", "cod_conta"]), "rotulo", "valor", "conta",
                                     "Dívida consolidada, deduções e DCL – saldo no fim de cada quadrimestre"), "rg_dc", "siconfi_rgf", onde=c2,
                   nota="RGF do Poder Executivo, Anexo 2: dívida consolidada, deduções e DCL, coluna 'Até o Nº "
                        "quadrimestre' (saldo no fim do quadrimestre, não fluxo do período)")
        a4 = e[(e["anexo"] == "RGF-Anexo 04") & (e["coluna"] == "% SOBRE A RCL AJUSTADA")]
        oc = a4[a4["cod_conta"].str.startswith("TotalConsideradoParaFinsDaApuracao")].groupby(["exercicio", "periodo"], as_index=False)["valor"].sum()
        if not oc.empty:
            oc["rotulo"] = REL.rotulo_periodo(oc, "rgf")
            ui.grafico(G.indicador_limite(oc, "rotulo", "valor", {"Alerta (90%)": 14.4, "Limite (Res. SF 43/2001)": 16.0},
                                               "Operações de crédito acumuladas no exercício (jan até o fim do quadrimestre) / RCL ajustada"),
                                                          "rg_oc", "siconfi_rgf", onde=c1,
                   nota="RGF do Poder Executivo, Anexo 4 (operações de crédito), coluna '% sobre a RCL ajustada': "
                        "operações contratadas de janeiro até o fim do quadrimestre sobre a RCL ajustada dos 12 meses "
                        "encerrados nele; o limite de 16% vale para o exercício inteiro")
        a6 = e[(e["anexo"] == "RGF-Anexo 06") & (e["coluna"] == "% SOBRE A RCL AJUSTADA")]
        gar = a6[a6["conta"].str.contains("Garantias", case=False)].groupby(["exercicio", "periodo"], as_index=False)["valor"].sum()
        if not gar.empty:
            gar["rotulo"] = REL.rotulo_periodo(gar, "rgf")
            ui.grafico(G.indicador_limite(gar, "rotulo", "valor", {"Alerta (90%)": 19.8, "Limite (Res. SF 43/2001)": 22.0},
                                               "Garantias concedidas (saldo no fim do quadrimestre) / RCL ajustada"), "rg_gar", "siconfi_rgf", onde=c2,
                   nota="RGF do Poder Executivo, Anexo 6 (demonstrativo simplificado), saldo das garantias no fim de "
                        "cada quadrimestre em % da RCL ajustada dos 12 meses encerrados nele")

    with abas[5]:
        ui.explicar_filtros(
            "As opções vêm de parâmetros e campos do JSON devolvido pela API do Siconfi (endpoint `/rgf`). Não vêm de "
            "planilha nem de arquivo CSV.",
            [COLETA,
             "**Campos usados**: `exercicio`, `periodo`, `anexo`, `instituicao`, `cod_conta`, `conta`, `coluna` e `valor`.",
             "**Montagem das opções**: os filtros são encadeados: o Poder define os exercícios, o exercício define os "
             "quadrimestres, e o quadrimestre define os anexos entregues."],
            [("Poder", PODERES_TXT),
             ("Exercício", "Campo `exercicio` do Poder escolhido, do mais recente ao mais antigo."),
             ("Quadrimestre", "Campo `periodo` do exercício escolhido, do mais recente ao mais antigo."),
             ("Anexo", "Anexos entregues no quadrimestre (campo `anexo`), entre os 6 que o painel descreve."),
             ("Instituição", "Campo `instituicao`. Só aparece quando o Poder tem mais de uma, como o Legislativo "
                             "(Assembleia Legislativa e Tribunal de Contas).")],
            ["**Anexo 5**: disponibilidade de caixa e restos a pagar só é publicado no 3º quadrimestre.",
             "**Ordem original**: a tabela começa na ordem do demonstrativo."],
            fontes=("siconfi_rgf",), nota="campos do JSON listados acima")
        c = st.columns([1.2, 1, 1, 3])
        poder = c[0].selectbox("Poder", list(R.NOMES_PODER), format_func=R.NOMES_PODER.get, key="rg_t_p")
        sub = df[df["co_poder"] == poder]
        anos = sorted(sub["exercicio"].unique(), reverse=True)
        ano = c[1].selectbox("Exercício", anos, key="rg_t_a")
        qs = sorted(sub.loc[sub["exercicio"] == ano, "periodo"].unique(), reverse=True)
        q = c[2].selectbox("Quadrimestre", qs, key="rg_t_q")
        disp = [a for a in ANEXOS if a in set(sub.loc[(sub["exercicio"] == ano) & (sub["periodo"] == q), "anexo"])]
        anexo = c[3].selectbox("Anexo", disp, format_func=lambda a: f"{a} – {ANEXOS[a]}", key="rg_t_x")
        insts = sorted(sub["instituicao"].unique())
        inst = st.selectbox("Instituição", insts, key="rg_t_i") if len(insts) > 1 else None
        t = REL.tabela_anexo(sub, anexo, ano, q, inst)
        num = [x for x in t.columns if x not in ("Quadro", "Código", "Conta")]
        ui.tabela(t, "rg_t_tab", 
                  fontes=["siconfi_rgf"], nota="RGF do Poder, exercício, quadrimestre e anexo escolhidos, na ordem das linhas do relatório",
                  moeda=num, ordenar_padrao="(ordem original)")
