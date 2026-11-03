"""Coleta no Portal de Dados Abertos de MS (CKAN, dados.ms.gov.br) e no BCB.

Conjuntos usados:
- despesas-por-credor-mensal (SEFAZ): uma linha por empenho e credor, com órgão,
  classificação funcional-programática, natureza (categoria, grupo, modalidade,
  elemento), tipo de licitação e valores empenhado/liquidado/pago. MENSAL.
- repasses-dos-municipios (SEFAZ): ICMS, IPVA, IPI-Exportação e FUNDERSUL
  entregues a cada município (CF, arts. 158 e 159). MENSAL.
- IPCA (IBGE, tabela 1737: API de agregados v3 ou SIDRA; reserva: SGS/BCB 433), para valores reais.
"""
from __future__ import annotations

import io
import logging
import re
import time
from datetime import date

import pandas as pd
import requests

from .config import BCB_IPCA, CKAN_API, IBGE_AGREGADOS, IBGE_SIDRA, USER_AGENT, caminho

log = logging.getLogger(__name__)
_s = requests.Session()
_s.headers["User-Agent"] = USER_AGENT


def _get(url: str, **kw) -> requests.Response:
    for t in range(4):
        try:
            r = _s.get(url, timeout=300, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if t == 3:
                raise
            log.warning("%s falhou (%s); repetindo", url, e)
            time.sleep(5 * (t + 1))
    raise RuntimeError(url)


def recursos(dataset: str) -> pd.DataFrame:
    """Lista os arquivos (recursos) de um conjunto, com o mês de referência extraído do nome."""
    js = _get(f"{CKAN_API}/package_show", params={"id": dataset}).json()["result"]
    linhas = []
    for r in js["resources"]:
        m = re.search(r"(\d{2})/(\d{4})", r.get("name", ""))
        if m:
            linhas.append({"ano": int(m.group(2)), "mes": int(m.group(1)), "nome": r["name"], "url": r["url"],
                           "atualizado": r.get("last_modified") or r.get("created")})
    return pd.DataFrame(linhas).sort_values(["ano", "mes"]).reset_index(drop=True)


def _num(s: pd.Series) -> pd.Series:
    """Converte números nos formatos '1.234,56', '1234.56' e '15000 00' (dumps antigos)."""
    s = s.astype(str).str.strip().str.replace('"', "", regex=False)
    tem_virgula = s.str.contains(",", regex=False)
    s = s.where(~tem_virgula, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    s = s.str.replace(r"\s+(\d{2})$", r".\1", regex=True).str.replace(" ", "", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    try:
        txt = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:  # alguns meses (ex.: 08/2025) foram publicados em Windows-1252
        txt = conteudo.decode("cp1252", errors="replace")
    sep = ";" if txt.split("\n", 1)[0].count(";") > 2 else ","
    # Em 05 a 08/2025 a SEFAZ publicou cada campo com aspas duplicadas ("""valor"""). Quando o valor tinha quebras
    # de linha (ex.: nome da ação), elas saíram fora das aspas: """texto"⏎""⏎"""" – o registro era cortado ao
    # meio e as colunas seguintes deslocadas (órgão = 'Despesas Correntes"', elemento = '-0,01' etc.).
    # O arquivo de 08/2025 foi regravado a partir dessa versão: cada registro quebrado virou duas linhas completas
    # (veja _juntar_registros_cortados).
    dobrado = f'{sep}"""' in txt[:20000]
    if dobrado:
        txt = re.sub(r'"(?:\r?\n"")*\r?\n""""', '"""', txt)
    df = pd.read_csv(io.StringIO(txt), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    if dobrado:
        df = df.apply(lambda s: s.str.replace(r'^"(.*)"$', r"\1", regex=True))
    df = _juntar_registros_cortados(df)
    return df.drop(columns=[c for c in ("_id",) if c in df.columns])


def _juntar_registros_cortados(df: pd.DataFrame) -> pd.DataFrame:
    """Reúne registros partidos em duas linhas (08/2025): a 1ª tem órgão…ação e o resto vazio; a 2ª começa com
    'resto da ação;Categoria"' seguido das demais colunas. Linhas totalmente vazias são descartadas."""
    if "Ação" not in df.columns:
        return df
    df = df[df.ne("").any(axis=1)].reset_index(drop=True)
    i_acao = df.columns.get_loc("Ação")
    cont = df.iloc[:, 0].str.contains(";", regex=False) & df.iloc[:, 0].str.endswith('"')
    if not cont.any():
        return df
    ant = cont.shift(-1, fill_value=False)  # linha cortada que precede cada continuação
    cortada = df.iloc[:, i_acao + 1:].eq("").all(axis=1)
    if not (cortada[ant]).all():
        raise ValueError(f"{(~cortada[ant]).sum()} continuações sem a linha cortada correspondente")
    a, b = df[ant].reset_index(drop=True), df[cont].reset_index(drop=True)
    resto, categoria = b.iloc[:, 0].str.rsplit(";", n=1).str[0], b.iloc[:, 0].str.rsplit(";", n=1).str[1]
    juntos = a.copy()
    juntos.iloc[:, i_acao] = (a.iloc[:, i_acao] + " " + resto.str.strip('"')).str.strip()
    juntos.iloc[:, i_acao + 1] = categoria.str.rstrip('"')
    n = len(df.columns) - i_acao - 2
    juntos.iloc[:, i_acao + 2:] = b.iloc[:, 1:1 + n].to_numpy()
    log.info("%d registros partidos em duas linhas foram reunidos", len(juntos))
    return pd.concat([df[~ant & ~cont], juntos], ignore_index=True)


# ----------------------------------------------------------- despesas por credor
_RENOMEAR = {
    "Orgão": "orgao", "Natureza de Despesa": "natureza", "Programa": "programa", "Função": "funcao",
    "Sub-Função": "subfuncao", "Ação": "acao", "Categoria": "categoria", "Grupo de Despesa": "grupo",
    "Modalidade": "modalidade", "Elemento de Despesa": "elemento", "Cpf/Cnpj": "cpf_cnpj", "Credor": "credor",
    "Documento": "empenho", "Tipo de Licitação": "licitacao", "Empenhado": "empenhado", "Liquidado": "liquidado",
    "Pago": "pago",
}

_PUBLICO = re.compile(
    r"PREFEITURA|MUNIC[IÍ]PIO|FUNDO |FUNDO$|SECRETARIA|TRIBUNAL|ASSEMBL|MINIST[EÉ]RIO|INSTITUTO NACIONAL|"
    r"INSS|RECEITA FEDERAL|UNI[AÃ]O|GOVERNO|ESTADO D|AG[EÊ]NCIA|DEPARTAMENTO|UNIVERSIDADE|C[AÂ]MARA MUNICIPAL|"
    r"DEFENSORIA|PROCURADORIA|FUNDA[CÇ][AÃ]O (ESTADUAL|NACIONAL|UNIVERSIDADE)|CONSELHO|CONS[OÓ]RCIO|"
    r"COMPANHIA DE SANEAMENTO|SANESUL|AGEPREV|DETRAN|POL[IÍ]CIA|CORPO DE BOMBEIROS|EMPRESA BRASILEIRA",
    re.I)
_FINANCEIRA = re.compile(r"BANCO|CAIXA ECON|BANRISUL|SICREDI|SICOOB|BRADESCO|ITA[UÚ]|SANTANDER|COOPERATIVA DE CR", re.I)
_RUBRICA = re.compile(r"^(VENCIMENTOS|IRRF|PASEP|DI[AÁ]RIAS|BOLSA|PENS[AÃ]O ALIMENT|CONSIGNA|FOLHA|INSS )", re.I)

# Elementos típicos de fornecimento de bens, serviços e obras (comparação sem acentos e caixa)
_ELEMENTO_FORNECEDOR = re.compile(
    r"material de consumo|terceiros ?- ?pessoa juridica|obras e instalacoes|equipamentos e material permanente|"
    r"locacao de mao|consultoria|tecnologia da informacao|distribuicao gratuita|passagens|terceirizacao|"
    r"arrendamento|aquisicao de imoveis|contrato de gestao|parceria publico")


def _sem_acento(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def tipo_credor(doc: str, nome: str) -> str:
    d = (doc or "").strip()
    n = (nome or "").strip()
    if d.startswith("***") or re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", d):
        return "Pessoa física"
    if d.upper().startswith("EX"):
        return "Empresa ou entidade estrangeira"
    if d.upper().startswith(("PF", "PJ")) or _RUBRICA.search(n):
        return "Rubrica agregada (folha/retenções)"
    if re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", d):
        if _FINANCEIRA.search(n):
            return "Instituição financeira"
        if _PUBLICO.search(n):
            return "Ente ou entidade pública"
        return "Empresa ou entidade privada"
    return "Outro / não identificado"


def tratar_despesas(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    df = df.rename(columns=_RENOMEAR)
    # registro deslocado: valor em coluna de texto ou coluna de valor vazia
    deslocado = df["elemento"].str.fullmatch(r"\s*-?[\d.]+,\d+\s*") | df["pago"].str.strip().eq("")
    if deslocado.any():
        raise ValueError(f"Despesas por credor {mes:02d}/{ano}: {deslocado.sum()} registros com colunas deslocadas")
    for c in ("empenhado", "liquidado", "pago"):
        df[c] = _num(df[c])
    texto = [c for c in df.columns if c not in ("empenhado", "liquidado", "pago")]
    for c in texto:
        df[c] = df[c].astype(str).map(lambda x: " ".join(x.split()))
    df["credor"] = df["credor"].str.upper()
    df["tipo_credor"] = [tipo_credor(d, n) for d, n in zip(df["cpf_cnpj"], df["credor"])]
    df["cnpj_raiz"] = df["cpf_cnpj"].where(df["tipo_credor"].str.contains("Empresa|Ente|financeira"), "").str[:10]
    elem_forn = {e: bool(_ELEMENTO_FORNECEDOR.search(_sem_acento(e))) for e in df["elemento"].unique()}
    df["fornecedor"] = df["elemento"].map(elem_forn).astype(bool) & df["tipo_credor"].isin(
        ["Empresa ou entidade privada", "Empresa ou entidade estrangeira"])
    df.insert(0, "mes", mes)
    df.insert(0, "ano", ano)
    cat = ["orgao", "programa", "funcao", "subfuncao", "acao", "categoria", "grupo", "modalidade", "elemento",
           "licitacao", "tipo_credor"]
    for c in cat:
        df[c] = df[c].astype("category")
    return df.drop(columns=[c for c in ("natureza",) if c in df.columns])


def atualizar_despesas_credor(desde: tuple[int, int] = (2025, 1), forcar_ultimos: int = 1) -> None:
    rec = recursos("despesas-por-credor-mensal")
    rec = rec[(rec["ano"] * 100 + rec["mes"]) >= desde[0] * 100 + desde[1]]
    ultimos = set(map(tuple, rec[["ano", "mes"]].tail(forcar_ultimos).values.tolist()))
    for r in rec.itertuples():
        arq = caminho(f"credor_{r.ano}_{r.mes:02d}.parquet")
        if arq.exists() and (r.ano, r.mes) not in ultimos:
            continue
        log.info("Despesas por credor %02d/%s …", r.mes, r.ano)
        df = tratar_despesas(_ler_csv(_get(r.url).content), r.ano, r.mes)
        df.to_parquet(arq, index=False)


def carregar_despesas_credor(anos: list[int] | None = None) -> pd.DataFrame:
    arqs = sorted(caminho("").glob("credor_*.parquet"))
    if anos:
        arqs = [a for a in arqs if int(a.stem.split("_")[1]) in anos]
    if not arqs:
        return pd.DataFrame()
    partes = [pd.read_parquet(a) for a in arqs]
    # unifica as categorias antes do concat: sem isso o pandas volta a 'object' e o pico de memória quase dobra
    for c in partes[0].columns:
        if all(isinstance(p[c].dtype, pd.CategoricalDtype) for p in partes if c in p):
            cats = pd.api.types.union_categoricals([p[c] for p in partes if c in p]).categories
            for p in partes:
                if c in p:
                    p[c] = p[c].astype(pd.CategoricalDtype(cats))
    df = pd.concat(partes, ignore_index=True)
    del partes
    df = normalizar_rotulos(df, ["orgao", "funcao", "subfuncao", "grupo", "modalidade", "elemento", "licitacao",
                                 "tipo_credor", "categoria", "programa", "acao"])
    return corrigir_rotulos_credor(df)


# O arquivo da SEFAZ corta os textos em largura fixa (80 caracteres; 110 na ação), tem erros de digitação e muda o
# nome de alguns elementos ao longo do tempo. Nomes completos conforme o MCASP (Portaria Interministerial 163/2001).
_ROTULOS_CREDOR = {
    "orgao": {
        "FUNDO DO SISTEMA DE PROTEÇÃO SOCIAL DOS MILITARES DO ESTADO DE MATO GROSSO DO S":
            "FUNDO DO SISTEMA DE PROTEÇÃO SOCIAL DOS MILITARES DO ESTADO DE MATO GROSSO DO SUL",
        "SECRETARIA DE ESTADO DE MEIO AMBIENTE, DESENVOLVIMENTO, CIÊNCIA, TECNOLOGIA E I":
            "SECRETARIA DE ESTADO DE MEIO AMBIENTE, DESENVOLVIMENTO, CIÊNCIA, TECNOLOGIA E INOVAÇÃO",
    },
    "funcao": {"SEGURANÇA PUBLICA": "SEGURANÇA PÚBLICA"},
    "modalidade": {
        "Aplicação Direta Decorrente de Operações entre Órgãos, Fundos e Entidades Integr":
            "Aplicação Direta Decorrente de Operações entre Órgãos, Fundos e Entidades Integrantes dos Orçamentos "
            "Fiscal e da Seguridade Social",
        "Tranferências à União": "Transferências à União",
        "Transferencia ao Exterior": "Transferências ao Exterior",
    },
    "elemento": {
        "Aporte de Recursos pelo Parceiro Público em Favor do Parceiro Privado Decorrente":
            "Aporte de Recursos pelo Parceiro Público em Favor do Parceiro Privado Decorrente de Contrato de PPP",
        "Transferências para Contrato de Rateio-Consórcios referente a Despesas de Pessoa":
            "Transferências para Contrato de Rateio-Consórcios referente a Despesas de Pessoal",
        "Despesas Decorrentes da Participação em Fundos, Organismos, ou Entidades Asseme":
            "Despesas Decorrentes da Participação em Fundos, Organismos, ou Entidades Assemelhadas, Nacionais e "
            "Internacionais",
        # mesmo elemento, nome alterado pela própria fonte em 2026
        "Aposentadorias, Reserva Remunerada e Reformas": "Aposentadorias do RPPS, Reserva Remunerada e Reformas dos Militares",
        "APOSENTADORIAS DO RPPS, RESERVA REMUNERADA E REFORMAS DOS MILITARES":
            "Aposentadorias do RPPS, Reserva Remunerada e Reformas dos Militares",
        "Pensões": "Pensões do RPPS e do Militar",
        "PENSÕES DO RPPS E DO MILITAR": "Pensões do RPPS e do Militar",
        "Outros Benefícios Assistenciais do Servidor ou do militar": "Outros Benefícios Assistenciais do Servidor e do Militar",
        "Outros Benefícios Assistenciais do Servidor e do militar": "Outros Benefícios Assistenciais do Servidor e do Militar",
    },
}
_LARGURA_FONTE = {"orgao": 79, "programa": 79, "modalidade": 79, "elemento": 79, "acao": 110}
_VAZIO = {"funcao": "(não informada)", "subfuncao": "(não informada)", "programa": "(não informado)",
          "acao": "(não informada)"}


def corrigir_rotulos_credor(df: pd.DataFrame) -> pd.DataFrame:
    """Completa nomes cortados, corrige grafias e unifica renomeações; marca com '…' os textos ainda cortados e
    rotula os campos vazios."""
    for c in set(_ROTULOS_CREDOR) | set(_LARGURA_FONTE) | set(_VAZIO):
        if c not in df:
            continue
        valores = pd.Series(df[c].astype(str).unique())
        novo = valores.map(lambda v: _ROTULOS_CREDOR.get(c, {}).get(v, v))
        corte = novo.eq(valores) & novo.str.len().ge(_LARGURA_FONTE.get(c, 10**6))
        novo = novo.where(~corte, novo + "…")
        if c in _VAZIO:
            novo = novo.where(novo.str.strip().ne(""), _VAZIO[c])
        df[c] = df[c].astype(str).map(dict(zip(valores, novo))).astype("category")
    return df


# ----------------------------------------------------------- repasses a municípios
def atualizar_repasses(desde: tuple[int, int] = (2024, 1), forcar_ultimos: int = 1) -> pd.DataFrame:
    rec = recursos("repasses-dos-municipios")
    rec = rec[(rec["ano"] * 100 + rec["mes"]) >= desde[0] * 100 + desde[1]]
    arq = caminho("repasses_municipios.parquet")
    antigo = pd.read_parquet(arq) if arq.exists() else pd.DataFrame(columns=["ano", "mes"])
    ja = set(map(tuple, antigo[["ano", "mes"]].drop_duplicates().values.tolist()))
    ultimos = set(map(tuple, rec[["ano", "mes"]].tail(forcar_ultimos).values.tolist()))
    novos = []
    for r in rec.itertuples():
        if (r.ano, r.mes) in ja and (r.ano, r.mes) not in ultimos:
            continue
        log.info("Repasses a municípios %02d/%s", r.mes, r.ano)
        df = _ler_csv(_get(r.url).content)
        df = df.rename(columns={"Tipo_Repasse": "tipo", "Data_Contabilização": "data", "Municipio": "municipio",
                                "Valor_Total": "valor"})
        df["valor"] = _num(df["valor"])
        df["municipio"] = df["municipio"].str.replace("PREFEITURA MUNICIPAL DE ", "", regex=False).str.strip()
        df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        df["ano"], df["mes"] = r.ano, r.mes
        novos.append(df[["ano", "mes", "data", "tipo", "municipio", "valor"]])
    if novos:
        base = antigo[~antigo.set_index(["ano", "mes"]).index.isin([(n["ano"].iat[0], n["mes"].iat[0]) for n in novos])]
        antigo = pd.concat([base, *novos], ignore_index=True)
        antigo.to_parquet(arq, index=False)
    return antigo


# ----------------------------------------------------------- IPCA
def _ipca_ibge_agregados(desde: int) -> pd.DataFrame:
    """API de agregados do IBGE (v3), tabela 1737: variáveis 63 (variação mensal, %) e 2266 (número-índice)."""
    # "all" evita o erro 400 que a API devolve quando o intervalo inclui meses ainda não divulgados
    js = _get(f"{IBGE_AGREGADOS}/1737/periodos/all/variaveis/63|2266", params={"localidades": "N1[all]"}).json()
    ser = {v["id"]: v["resultados"][0]["series"][0]["serie"] for v in js}
    df = pd.DataFrame({"ipca": pd.Series(ser["63"]), "indice": pd.Series(ser["2266"])})
    df = df.rename_axis("periodo").reset_index()
    return df[df["periodo"].astype(int) >= desde]


def _ipca_sidra(desde: int) -> pd.DataFrame:
    """SIDRA (apisidra.ibge.gov.br), mesma tabela 1737."""
    js = _get(f"{IBGE_SIDRA}/t/1737/n1/all/v/63,2266/p/{desde}-{date.today().year + 1}12", params={"formato": "json"}).json()
    d = pd.DataFrame(js[1:])
    d = d.pivot_table(index="D3C", columns="D2C", values="V", aggfunc="first")
    return d.rename(columns={"63": "ipca", "2266": "indice"}).rename_axis("periodo").reset_index()


def _ipca_bcb(desde: int) -> pd.DataFrame:
    """Reserva: série 433 do SGS/BCB (variação mensal do IPCA, replicada do IBGE); o índice é encadeado aqui."""
    js = _get(BCB_IPCA, params={"formato": "json", "dataInicial": f"01/01/{desde // 100}"}).json()
    d = pd.DataFrame(js)
    d["periodo"] = pd.to_datetime(d["data"], dayfirst=True).dt.strftime("%Y%m")
    d["ipca"] = pd.to_numeric(d["valor"])
    d["indice"] = (1 + d["ipca"] / 100).cumprod()
    return d[["periodo", "ipca", "indice"]]


def atualizar_ipca(desde: int = 201501) -> pd.DataFrame:
    """IPCA mensal (IBGE). Tenta a API de agregados do IBGE, depois o SIDRA e, por último, o BCB.

    Grava `ipca.parquet` com ano, mes, ipca (variação mensal, %), indice (número-índice) e fonte.
    """
    df, erros = None, []
    for nome, f in (("IBGE – API de agregados v3", _ipca_ibge_agregados), ("IBGE – SIDRA", _ipca_sidra),
                    ("BCB – SGS 433", _ipca_bcb)):
        try:
            d = f(desde)
            d["ipca"], d["indice"] = pd.to_numeric(d["ipca"], errors="coerce"), pd.to_numeric(d["indice"], errors="coerce")
            d = d.dropna(subset=["indice"])
            if len(d) >= 12:
                df = d.assign(fonte=nome)
                break
            erros.append(f"{nome}: resposta vazia")
        except Exception as e:  # noqa: BLE001 – uma fonte fora do ar não deve impedir as demais
            log.warning("IPCA via %s falhou: %s", nome, e)
            erros.append(f"{nome}: {e}")
    if df is None:
        raise RuntimeError("IPCA indisponível: " + "; ".join(erros))
    df["ano"], df["mes"] = df["periodo"].str[:4].astype(int), df["periodo"].str[4:6].astype(int)
    df = df.sort_values(["ano", "mes"])[["ano", "mes", "ipca", "indice", "fonte"]].reset_index(drop=True)
    df.to_parquet(caminho("ipca.parquet"), index=False)
    log.info("IPCA: %d meses (%s), último %02d/%d", len(df), df["fonte"].iat[0], df["mes"].iat[-1], df["ano"].iat[-1])
    return df


def normalizar_rotulos(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Unifica grafias que diferem só em caixa, acentos ou espaços ("…do militar" × "…do Militar")."""
    for c in colunas:
        if c not in df:
            continue
        valores = pd.Series(df[c].astype(str).unique())
        chave = valores.map(lambda v: re.sub(r"[^a-z0-9]", "", _sem_acento(v)))
        canon = valores.groupby(chave).transform("first")
        df[c] = df[c].astype(str).map(dict(zip(valores, canon))).astype("category")
    return df
