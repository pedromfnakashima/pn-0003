"""Catálogo das fontes primárias: página, formato, endpoint, parâmetros e arquivos de cada base usada no painel.

Cada gráfico e tabela cita uma ou mais chaves deste catálogo (ui.fonte, ui.grafico, ui.tabela). A legenda mostra
o resumo e a tooltip mostra o detalhe completo.
"""
from __future__ import annotations

from .config import BCB_IPCA, CKAN_API, IBGE_AGREGADOS, PORTAL_GW, PORTAL_URL, SICONFI_API, SICONFI_DOCS

_DESP = f"{PORTAL_GW}/d0146/transpdespesas/v1"
_REC = f"{PORTAL_GW}/d0145/transpreceitas/v1"
_FORMATO_PORTAL = ("JSON devolvido pela API do portal. Os números não estão no HTML: a página (aplicação AngularJS) "
                   "chama a API com um token emitido ao navegador, e o painel faz as mesmas chamadas com Playwright. "
                   "A API aceita o parâmetro exportarcsv; o painel usa exportarcsv=false e lê o JSON.")
_FORMATO_SICONFI = f"JSON da API de dados abertos do Tesouro (Oracle REST Data Services, paginada por offset). Documentação: {SICONFI_DOCS}"
_PAGINA_SICONFI = "https://siconfi.tesouro.gov.br/"

FONTES: dict[str, dict] = {
    # ------------------------------------------------------------ Portal da Transparência de MS (diário)
    "portal_desp_orgaos": dict(
        nome="Portal da Transparência de MS › Despesas › por órgão", resp="CGE-MS",
        dominio="www.transparencia.ms.gov.br", pagina=PORTAL_URL + "#/Despesa", formato=_FORMATO_PORTAL,
        endpoint=f"GET {_DESP}/despesapordataorgaos",
        parametros="anoconsulta, dataInicio e dataFim (AAAA-MM-DD), pageno, pagesize, credor, unidadeGestora, exportarcsv=false",
        local="portal_despesa_diaria_orgao.parquet (um dia por consulta); portal_despesa_mensal_orgao.parquet (um mês por consulta)",
        periodicidade="diária"),
    "portal_desp_credores": dict(
        nome="Portal da Transparência de MS › Despesas › por credor", resp="CGE-MS",
        dominio="www.transparencia.ms.gov.br", pagina=PORTAL_URL + "#/Despesa", formato=_FORMATO_PORTAL,
        endpoint=f"GET {_DESP}/despesapordatacredores",
        parametros="anoconsulta, dataInicio e dataFim (AAAA-MM-DD), pageno, pagesize=500, exportarcsv=false",
        local="portal_credores_AAAA_MM.parquet", periodicidade="diária"),
    "portal_rec_orgaos": dict(
        nome="Portal da Transparência de MS › Receitas › Pesquisa de Receita (por órgão arrecadador)", resp="CGE-MS / SEFAZ-MS",
        dominio="www.transparencia.ms.gov.br", pagina=PORTAL_URL, formato=_FORMATO_PORTAL,
        endpoint=f"GET {_REC}/pesquisadereceitas",
        parametros="exercicio, dataInicio e dataTermino (AAAA-MM-DD), exportarcsv=false",
        local="portal_receita_diaria_orgao.parquet", periodicidade="diária"),
    "portal_rec_simplificada": dict(
        nome="Portal da Transparência de MS › Receitas › Receita Simplificada", resp="CGE-MS / SEFAZ-MS",
        dominio="www.transparencia.ms.gov.br", pagina=PORTAL_URL, formato=_FORMATO_PORTAL,
        endpoint=f"GET {_REC}/receitasimplificadas",
        parametros="exercicio, mesInicio, mesTermino, exportarcsv=false",
        local="portal_receita_mensal.parquet", periodicidade="diária (acumulado do mês)"),
    "portal_rec_consolidada": dict(
        nome="Portal da Transparência de MS › Receitas › Receita Consolidada (árvore da natureza)", resp="CGE-MS / SEFAZ-MS",
        dominio="www.transparencia.ms.gov.br", pagina=PORTAL_URL, formato=_FORMATO_PORTAL,
        endpoint=f"GET {_REC}/receitaconsolidadas",
        parametros="exercicio, elementId=0, obterSubNiveis=true, descricao, exportarcsv=false",
        local="portal_receita_arvore_AAAA.parquet; portal_receita_arvore_historico.parquet",
        periodicidade="diária (acumulado do ano)"),
    # ------------------------------------------------------------ Siconfi / Tesouro Nacional
    "siconfi_msc": dict(
        nome="Siconfi › Matriz de Saldos Contábeis (MSC), classe 6 – execução do orçamento", resp="STN (dados enviados pelo Estado)",
        dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI, formato=_FORMATO_SICONFI,
        endpoint=f"GET {SICONFI_API}/msc_orcamentaria",
        parametros="id_ente=50, an_referencia, me_referencia, co_tipo_matriz=MSCC, classe_conta=6, id_tv=period_change, offset",
        local="msc6_AAAA_MM.parquet", periodicidade="mensal"),
    "siconfi_rreo": dict(
        nome="Siconfi › Relatório Resumido da Execução Orçamentária (RREO)", resp="STN (relatório homologado pelo Estado)",
        dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI, formato=_FORMATO_SICONFI,
        endpoint=f"GET {SICONFI_API}/rreo",
        parametros="id_ente=50, an_exercicio, nr_periodo (bimestre), co_tipo_demonstrativo=RREO, co_esfera=E, offset",
        local="rreo_AAAA_B.parquet", periodicidade="bimestral"),
    "siconfi_rgf": dict(
        nome="Siconfi › Relatório de Gestão Fiscal (RGF), por Poder", resp="STN (relatórios homologados por cada Poder)",
        dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI, formato=_FORMATO_SICONFI,
        endpoint=f"GET {SICONFI_API}/rgf",
        parametros="id_ente=50, an_exercicio, in_periodicidade=Q, nr_periodo (quadrimestre), co_tipo_demonstrativo=RGF, "
                   "co_esfera=E, co_poder (E, L, J, M, D), offset",
        local="rgf_AAAA_Q_PODER.parquet", periodicidade="quadrimestral"),
    "siconfi_extrato": dict(
        nome="Siconfi › Extrato de entregas", resp="STN", dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI,
        formato=_FORMATO_SICONFI, endpoint=f"GET {SICONFI_API}/extrato_entregas", parametros="id_ente=50, an_referencia",
        local="siconfi_extrato.parquet", periodicidade="a cada entrega"),
    "siconfi_rgf_uf": dict(
        nome="Siconfi › RGF de todos os Estados e do Distrito Federal, por Poder", resp="STN (relatórios homologados por cada Poder)",
        dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI, formato=_FORMATO_SICONFI,
        endpoint=f"GET {SICONFI_API}/rgf (um ente e um Poder por chamada)",
        parametros="id_ente = código IBGE da UF, co_poder (E, L, J, M, D), an_exercicio, in_periodicidade=Q, "
                   "nr_periodo (quadrimestre), co_tipo_demonstrativo=RGF, co_esfera=E, offset",
        local="rgf_estados/rgf_uf_AAAA_Q.parquet (um por quadrimestre, todas as UFs e Poderes)",
        periodicidade="quadrimestral"),
    # ------------------------------------------------------------ dados abertos de MS (CKAN)
    "ckan_credores": dict(
        nome="Dados Abertos MS › Despesas por Credor – Mensal", resp="SEFAZ-MS", dominio="www.dados.ms.gov.br",
        pagina="https://www.dados.ms.gov.br/dataset/despesas-por-credor-mensal",
        formato="Arquivos CSV para download (separador ';', UTF-8; alguns meses em Windows-1252), um por mês. "
                "A lista de arquivos vem da API do CKAN.",
        endpoint=f"GET {CKAN_API}/package_show?id=despesas-por-credor-mensal (lista os arquivos); depois o download de cada CSV",
        arquivo="despesas-MM_AAAA.csv (ex.: despesas-09_2026.csv)", local="credor_AAAA_MM.parquet", periodicidade="mensal"),
    "ckan_repasses": dict(
        nome="Dados Abertos MS › Repasses dos Municípios", resp="SEFAZ-MS", dominio="www.dados.ms.gov.br",
        pagina="https://www.dados.ms.gov.br/dataset/repasses-dos-municipios",
        formato="CSV gerado pelo datastore do CKAN, um por mês (download sem extensão no nome).",
        endpoint=f"GET {CKAN_API}/package_show?id=repasses-dos-municipios (lista os arquivos); "
                 "depois GET https://www.dados.ms.gov.br/datastore/dump/repasses-dos-municipios-MM_AAAA",
        arquivo="repasses-dos-municipios-MM_AAAA (CSV)", local="repasses_municipios.parquet", periodicidade="mensal"),
    # ------------------------------------------------------------ IPCA
    "bcb_ipca": dict(
        nome="IPCA mensal – IBGE, tabela 1737 (variação mensal e número-índice, base dez/1993 = 100)",
        resp="IBGE", dominio="servicodados.ibge.gov.br", pagina="https://sidra.ibge.gov.br/tabela/1737",
        formato="JSON da API de agregados do IBGE (v3). Se ela falhar, o painel usa o SIDRA (apisidra.ibge.gov.br) "
                f"e, por último, a série 433 do SGS do Banco Central ({BCB_IPCA}).",
        endpoint=f"GET {IBGE_AGREGADOS}/1737 (…/1737/periodos/all/variaveis/63|2266?localidades=N1[all])",
        parametros="variável 63 = IPCA, variação mensal (%); 2266 = número-índice; N1 = Brasil",
        local="ipca.parquet (coluna 'fonte' registra a API usada)", periodicidade="mensal"),
    # ------------------------------------------------------------ Siconfi – todas as UFs
    "siconfi_rreo_uf": dict(
        nome="Siconfi › RREO de todos os Estados e do Distrito Federal", resp="STN (relatórios homologados pelas UFs)",
        dominio="apidatalake.tesouro.gov.br", pagina=_PAGINA_SICONFI, formato=_FORMATO_SICONFI,
        endpoint=f"GET {SICONFI_API}/rreo (um ente por chamada) e GET {SICONFI_API}/entes",
        parametros="id_ente = código IBGE da UF (11 a 53), an_exercicio, nr_periodo (bimestre), "
                   "co_tipo_demonstrativo=RREO, co_esfera=E, offset",
        local="rreo_estados/rreo_uf_AAAA_B.parquet (um por bimestre, todas as UFs); rreo_estados/entes.parquet",
        periodicidade="bimestral"),
}


def _endpoint_curto(f: dict) -> str:
    ep = f.get("endpoint", "").split("?")[0].split(";")[0].split(" (")[0]
    return ep.replace("GET ", "").rstrip("/").rsplit("/", 1)[-1]


def resumo(chave: str) -> str:
    """Uma linha: base, domínio e endpoint ou arquivo (markdown)."""
    f = FONTES[chave]
    if f.get("arquivo"):
        onde = f"arquivo `{f['arquivo'].split(' (')[0]}`"
    else:
        onde = f"API `/{_endpoint_curto(f)}`"
    return f"{f['nome']} ({f['dominio']}) · {onde}"


def detalhe(chave: str) -> str:
    """Bloco markdown completo, usado nas tooltips."""
    f = FONTES[chave]
    linhas = [f"**{f['nome']}** — {f['resp']}", "",
              f"- Página: {f['pagina']}",
              f"- Formato: {f['formato']}",
              f"- Endpoint: `{f['endpoint']}`"]
    if f.get("parametros"):
        linhas.append(f"- Parâmetros: {f['parametros']}")
    if f.get("arquivo"):
        linhas.append(f"- Arquivo de origem: `{f['arquivo']}`")
    linhas += [f"- Periodicidade da fonte: {f['periodicidade']}",
               f"- Cópia local (Parquet): `dados/dashboard/{f['local']}`"]
    return "\n".join(linhas)
