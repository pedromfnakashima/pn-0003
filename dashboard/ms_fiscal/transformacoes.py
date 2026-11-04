"""Transformação da MSC e das demais bases em tabelas analíticas."""
from __future__ import annotations

import pandas as pd

from . import referencias as R


def distintos(s: pd.Series) -> list[str]:
    """Equivale a `list(s.astype(str).unique())`, na mesma ordem, sem converter cada linha em texto.

    Numa coluna categórica com centenas de milhares de linhas, a conversão custa segundos de CPU no Streamlit Cloud."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        cats = [str(c) for c in s.cat.categories] + ["nan"]  # o último recebe os ausentes (código -1)
        return list(dict.fromkeys(cats[k] for k in pd.unique(s.cat.codes.to_numpy())))
    return list(s.astype(str).unique())


def _por_valor(s: pd.Series, f) -> pd.Series:
    """Aplica `f` uma vez por valor distinto, e não linha a linha.

    No Streamlit Cloud a CPU é pequena e o laço em Python segura o GIL: enquanto ele roda, o servidor deixa de
    entregar os arquivos JavaScript da página (erro "Failed to fetch dynamically imported module")."""
    feitos = {v: f(v) for v in s.unique()}
    # .map com função (e não com o dicionário) mantém o tipo da coluna que o .map(f) original produzia
    return s.map(lambda v: feitos[v] if v in feitos else f(v))


# ------------------------------------------------------------------ rótulos de receita
_rotulos_portal: dict[str, str] = {}


def definir_rotulos_receita(rot: dict[str, str]) -> None:
    _rotulos_portal.clear()
    _rotulos_portal.update(rot)


def rotulo_receita(codigo8: str, digitos: int) -> str:
    pref = str(codigo8)[:digitos]
    cheio = pref.ljust(8, "0")
    nome = _rotulos_portal.get(cheio)
    if not nome and digitos == 1:
        nome = R.CATEGORIAS_RECEITA.get(pref)
    if not nome and digitos == 2:
        nome = R.ORIGENS_RECEITA.get(pref)
    if not nome:
        # sobe na hierarquia até achar um nome conhecido
        for d in range(digitos - 1, 0, -1):
            n2 = _rotulos_portal.get(pref[:d].ljust(8, "0"))
            if n2:
                nome = f"{n2} (detalhe {pref})"
                break
    return f"{pref} – {nome}" if nome else pref


TIPO_RECEITA = {
    "621200000": "Receita bruta realizada",
    "621310100": "Dedução – FUNDEB",
    "621310200": "Dedução – transferências a municípios",
    "621320000": "Dedução – renúncia",
    "621390000": "Dedução – outras",
}


def receitas_msc(msc: pd.DataFrame) -> pd.DataFrame:
    """Receita realizada por natureza (conta 6.2.1.2) e suas deduções (6.2.1.3.x), mensal."""
    if msc.empty:
        return pd.DataFrame()
    df = msc[msc["conta_contabil"].isin(TIPO_RECEITA)].copy()
    df["tipo"] = df["conta_contabil"].map(TIPO_RECEITA)
    df["deducao"] = df["conta_contabil"] != "621200000"
    # Renúncia (6.2.1.3.2): a partir de 2026 a SEFAZ-MS passou a registrar a renúncia de ICMS como receita bruta
    # e dedução simultâneas; a "bruta exceto renúncia" mantém a comparabilidade com anos anteriores.
    df["renuncia"] = df["conta_contabil"] == "621320000"
    df["natureza_receita"] = df["natureza_receita"].fillna("00000000").astype(str)
    df["tributo"] = _por_valor(df["natureza_receita"], R.tributo_chave)
    df["intra"] = _por_valor(df["natureza_receita"], lambda c: c[:1] in ("7", "8"))
    df["poder"] = _por_valor(df["poder_orgao"], R.rotulo_poder)
    df["fonte"] = _por_valor(df["fonte_recursos"], R.rotulo_fonte)
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))
    return df[["ano", "mes", "data", "tipo", "deducao", "renuncia", "natureza_receita", "tributo", "intra", "poder", "fonte", "valor"]]


def adicionar_niveis_receita(df: pd.DataFrame, nivel: str) -> pd.Series:
    dig = R.NIVEIS_RECEITA[nivel]
    cod = df["natureza_receita"].astype(str)
    unicos = {c: rotulo_receita(c, dig) for c in cod.unique()}
    return cod.map(unicos)


# ------------------------------------------------------------------ despesas
ESTAGIO_CONTAS = {
    "622130100": ("empenhado",),
    "622130200": ("empenhado",),
    "622130300": ("empenhado", "liquidado"),
    "622130400": ("empenhado", "liquidado", "pago"),
}


def despesas_msc(msc: pd.DataFrame) -> pd.DataFrame:
    """Despesa do exercício por estágio (empenhada, liquidada, paga), mensal.

    Movimentos das contas 6.2.2.1.3.01 a .04 (MCASP, PCASP): a despesa empenhada
    é a soma das quatro; a liquidada, das duas últimas; a paga, da última.
    """
    if msc.empty:
        return pd.DataFrame()
    df = msc[msc["conta_contabil"].isin(ESTAGIO_CONTAS)].copy()
    for est in ("empenhado", "liquidado", "pago"):
        mask = df["conta_contabil"].isin([c for c, e in ESTAGIO_CONTAS.items() if est in e])
        df[est] = df["valor"].where(mask, 0.0)
    # rótulos calculados uma vez por natureza distinta (são poucas centenas) e depois espalhados pelas linhas
    nat = df["natureza_despesa"].fillna("").astype(str)
    u = pd.Series(nat.unique())
    nd = u.str.ljust(8, "0")
    rot = pd.DataFrame({
        "categoria": nd.str[0].map(lambda c: f"{c} – {R.CATEGORIAS_DESPESA.get(c, '?')}"),
        "grupo": nd.str[1].map(lambda c: f"{c} – {R.GRUPOS_DESPESA.get(c, '?')}"),
        "modalidade": nd.str[2:4].map(lambda c: f"{c} – {R.MODALIDADES.get(c, '?')}"),
        "grupo_modalidade": nd.str[2:4].map(lambda c: R.GRUPO_MODALIDADE.get(c, "Outras")),
        "elemento": nd.str[4:6].map(lambda c: f"{c} – {R.ELEMENTOS.get(c, '?')}"),
        "natureza": nd.str[0] + "." + nd.str[1] + "." + nd.str[2:4] + "." + nd.str[4:6],
        "intra": nd.str[2:4] == "91",
    })
    pos = pd.Index(u).get_indexer(nat)
    for c in rot.columns:
        df[c] = rot[c].to_numpy()[pos]
    df["funcao"] = _por_valor(df["funcao"].fillna(""), lambda c: f"{c} – {R.FUNCOES.get(c, '?')}")
    df["subfuncao"] = _por_valor(df["subfuncao"].fillna(""), lambda c: f"{c} – {R.SUBFUNCOES.get(c, '?')}")
    df["poder"] = _por_valor(df["poder_orgao"], R.rotulo_poder)
    df["fonte"] = _por_valor(df["fonte_recursos"], R.rotulo_fonte)
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))
    cols = ["ano", "mes", "data", "poder", "funcao", "subfuncao", "categoria", "grupo", "modalidade",
            "grupo_modalidade", "elemento", "natureza", "fonte", "intra"]
    return df.groupby(cols, as_index=False, observed=True)[["empenhado", "liquidado", "pago"]].sum()


RP_CONTAS = {
    "631100000": "RPNP a liquidar", "631300000": "RPNP liquidados a pagar", "631400000": "RPNP pagos",
    "632100000": "RPP a pagar", "632200000": "RPP pagos",
}


def restos_a_pagar_msc(msc: pd.DataFrame) -> pd.DataFrame:
    if msc.empty:
        return pd.DataFrame()
    df = msc[msc["conta_contabil"].isin(RP_CONTAS)].copy()
    df["situacao"] = df["conta_contabil"].map(RP_CONTAS)
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))
    return df.groupby(["ano", "mes", "data", "situacao"], as_index=False)["valor"].sum()


# ------------------------------------------------------------------ IPCA
def deflacionar(df: pd.DataFrame, ipca: pd.DataFrame, colunas: list[str], ano="ano", mes="mes") -> pd.DataFrame:
    """Converte valores nominais em reais a preços do último mês com IPCA divulgado."""
    if ipca is None or ipca.empty:
        return df
    base = ipca["indice"].iloc[-1]
    fator = df[[ano, mes]].merge(ipca[["ano", "mes", "indice"]], left_on=[ano, mes], right_on=["ano", "mes"], how="left")["indice"]
    fator = (base / fator.fillna(base)).to_numpy()  # meses sem IPCA divulgado ficam a preços correntes
    out = df.copy()
    for c in colunas:
        out[c] = out[c] * fator
    return out
