"""Gráficos interativos (Plotly) com paleta categórica validada para daltonismo."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Paleta categórica de referência (ordem fixa; validada para CVD em modo claro e escuro)
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
OUTROS = "#9a9893"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
STATUS = {"bom": "#0ca30c", "alerta": "#fab219", "serio": "#ec835a", "critico": "#d03b3b"}
ESTAGIOS = {"empenhado": CORES[0], "liquidado": CORES[1], "pago": CORES[2]}

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def brl(v: float, casas: int = 1) -> str:
    """Formata em reais com sufixo (mil, mi, bi) no padrão brasileiro."""
    if v is None or pd.isna(v):
        return "–"
    a = abs(v)
    for lim, suf in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if a >= lim:
            s = f"{v / lim:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {s} {suf}"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float, casas: int = 1) -> str:
    return "–" if v is None or pd.isna(v) else f"{v:,.{casas}f}%".replace(".", ",")


def _layout(fig: go.Figure, titulo: str | None = None, altura: int = 420, legenda: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=15)) if titulo else None,
        height=altura, margin=dict(l=8, r=8, t=48 if titulo else 16, b=16),
        colorway=CORES, hovermode="x unified" if legenda else "closest",
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="left", x=0, title=None),
        separators=",.", font=dict(family="Inter, system-ui, sans-serif", size=12),
        hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=True, zerolinecolor="rgba(128,128,128,0.4)", title=None)
    return fig


def _passo_bonito(bruto: float) -> float:
    import math
    if bruto <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * e:
            return m * e
    return 10 * e


def eixo_moeda(fig: go.Figure, eixo: str = "y", n: int = 5) -> go.Figure:
    """Rótulos do eixo de valores em reais com sufixo brasileiro (R$ 5 bi, R$ 800 mi)."""
    import numpy as np
    pos: dict = {}
    neg: dict = {}
    vals: list[float] = []
    outro = "x" if eixo == "y" else "y"
    empilha = fig.layout.barmode in ("relative", "stack")
    for tr in fig.data:
        v = getattr(tr, eixo, None)
        if v is None or tr.type not in ("bar", "scatter"):
            continue
        v = pd.to_numeric(pd.Series(np.asarray(v, dtype=object)), errors="coerce").fillna(0).to_numpy()
        vals.extend(v.tolist())
        if empilha and tr.type == "bar":
            k = getattr(tr, outro, None)
            k = list(k) if k is not None else list(range(len(v)))
            for kk, vv in zip(k, v):
                d = pos if vv >= 0 else neg
                d[kk] = d.get(kk, 0) + vv
    if not vals:
        return fig
    lo = min([0, *vals, *neg.values()])
    hi = max([0, *vals, *pos.values()])
    if hi == lo:
        return fig
    passo = _passo_bonito((hi - lo) / n)
    ticks = np.arange(np.floor(lo / passo) * passo, np.ceil(hi / passo) * passo + passo / 2, passo)
    texto = [brl(t, 0 if _inteiro_no_sufixo(t) else 1) if t != 0 else "0" for t in ticks]
    (fig.update_yaxes if eixo == "y" else fig.update_xaxes)(tickvals=ticks.tolist(), ticktext=texto)
    return fig


def _inteiro_no_sufixo(v: float) -> bool:
    a = abs(v)
    for lim in (1e9, 1e6, 1e3):
        if a >= lim:
            return abs(v / lim - round(v / lim)) < 1e-9
    return True


def mapa_cores(categorias: list[str], max_series: int = 8) -> dict[str, str]:
    """Cor fixa por entidade (não por ranking); excedentes viram 'Outros' em cinza."""
    m = {c: CORES[i] for i, c in enumerate(categorias[:max_series])}
    m["Outros"] = OUTROS
    return m


def top_n_outros(df: pd.DataFrame, col: str, valor: str, n: int = 7) -> pd.DataFrame:
    tot = df.groupby(col, observed=True)[valor].sum().sort_values(ascending=False)
    manter = set(tot.head(n).index)
    out = df.copy()
    out[col] = out[col].astype(str).where(out[col].isin(manter), "Outros")
    return out


def _ordem_e_cores(df, cor, valor, ordem, cores):
    """Ordena as séries pelo total ("Outros" por último, em cinza) e fixa a cor de cada uma."""
    if not cor or cor not in df:
        return ordem, cores
    if cor == "ano":  # exercícios em ordem cronológica, cor fixa por ano
        seq = sorted(df[cor].astype(str).unique())
        return {cor: seq}, cores or {a: CORES[i % len(CORES)] for i, a in enumerate(seq)}
    if ordem is None or (isinstance(ordem, dict) and cor not in ordem):
        tot = df.groupby(cor, observed=True)[valor].sum().abs().sort_values(ascending=False).index.astype(str).tolist()
        seq = [o for o in tot if o != "Outros"] + (["Outros"] if "Outros" in tot else [])
        ordem = {**(ordem or {}), cor: seq} if isinstance(ordem, dict) or ordem is None else ordem
    seq = ordem[cor] if isinstance(ordem, dict) else ordem
    if cores is None and len(seq) <= len(CORES) + 1:
        cores = mapa_cores([s for s in seq if s != "Outros"])
    return ordem, cores


def _formato_data(serie: pd.Series) -> str | None:
    """Formato d3 do eixo de datas: mês/ano para séries mensais, dia/mês/ano para séries diárias."""
    if not pd.api.types.is_datetime64_any_dtype(serie):
        return None
    datas = pd.to_datetime(serie.dropna())
    return "%m/%Y" if not datas.empty and (datas.dt.day == 1).all() else "%d/%m/%Y"


def _eixo_data(fig: go.Figure, fmt: str | None, serie: pd.Series | None = None) -> go.Figure:
    if not fmt:
        return fig
    if fmt == "%m/%Y":  # um rótulo por mês (ou a cada 2, 3, 6 meses em séries longas), sem repetir
        datas = pd.to_datetime(serie.dropna()) if serie is not None else pd.Series(dtype="datetime64[ns]")
        n = datas.dt.to_period("M").nunique() if not datas.empty else 12
        passo = 1 if n <= 14 else 2 if n <= 26 else 3 if n <= 40 else 6
        fig.update_xaxes(hoverformat=fmt, tickformat=fmt if n <= 14 else "%m/%y", dtick=f"M{passo}", tickangle=0,
                         tick0=datas.min() if not datas.empty else None)
    else:
        fig.update_xaxes(hoverformat=fmt, tickformat="%d/%m")
    return fig


def _x_hover(x: str, fmt: str | None) -> str:  # x = variável do hovertemplate ("x" ou "y")
    return f"%{{{x}|{fmt}}}" if fmt else f"%{{{x}}}"


def _total_no_hover(fig: go.Figure, df: pd.DataFrame, x: str, y: str, fmt: str | None) -> go.Figure:
    """Linha 'Total' no topo do hover unificado das barras empilhadas (traço invisível, primeiro na ordem)."""
    tot = df.groupby(x, observed=True, sort=False)[y].sum().reset_index()
    fig.add_scatter(x=tot[x], y=tot[y], mode="markers", marker=dict(size=1, opacity=0), showlegend=False,
                    name="Total", hovertemplate="<b>Total: R$ %{y:,.2f}</b><extra></extra>")
    fig.data = (fig.data[-1], *fig.data[:-1])
    fig.update_layout(legend_traceorder="normal")
    return fig


def linhas(df, x, y, cor=None, titulo=None, altura=420, ordem=None, cores=None, marcadores=True, moeda=True):
    ordem = {cor: ordem} if isinstance(ordem, list) else ordem
    if cor and cor in df and df[cor].nunique() <= 9:
        ordem, cores = _ordem_e_cores(df, cor, y, ordem, cores)
    fig = px.line(df, x=x, y=y, color=cor, markers=marcadores, category_orders=ordem, color_discrete_map=cores,
                  color_discrete_sequence=CORES)
    fig.update_traces(line=dict(width=2), marker=dict(size=8), hovertemplate="R$ %{y:,.2f}" if moeda else "%{y:,.2f}")
    fig = _eixo_data(_layout(fig, titulo, altura), _formato_data(df[x]), df[x])
    return eixo_moeda(fig) if moeda else fig


def barras(df, x, y, cor=None, titulo=None, altura=420, horizontal=False, empilhar=True, ordem=None, cores=None, texto=None,
           moeda=True, total=None):
    """Barras; com `cor` e empilhadas na vertical, o hover unificado mostra o período, o total e cada componente."""
    if horizontal:  # rótulos de categoria longos são encurtados para não serem cortados
        df = df.copy()
        df[x] = df[x].astype(str).str.strip().map(lambda s: s if len(s) <= 50 else s[:48] + "…")
    if cor:
        ordem, cores = _ordem_e_cores(df, cor, y, ordem, cores)
    fig = px.bar(df, x=y if horizontal else x, y=x if horizontal else y, color=cor, orientation="h" if horizontal else "v",
                 barmode="relative" if empilhar else "group", category_orders=ordem, color_discrete_map=cores,
                 color_discrete_sequence=CORES, text=texto)
    fig.update_traces(marker_line_width=1, marker_line_color="rgba(255,255,255,0.6)")
    if texto:
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(bargap=0.18)
    fig = _layout(fig, titulo, altura, legenda=cor is not None and not horizontal)
    if horizontal:
        # poucas categorias: encolhe o gráfico e limita a espessura da barra (~28 px), em vez de uma faixa larga
        n = max(1, df[x].nunique())
        altura = min(altura, 120 + 44 * n)
        area = altura - (48 if titulo else 16) - 16 - 24
        fig.update_layout(height=altura, bargap=max(0.18, 1 - 28 / (area / n)))
        fig.update_yaxes(autorange="reversed" if not ordem else None, gridcolor="rgba(0,0,0,0)")
        fig.update_xaxes(gridcolor="rgba(128,128,128,0.18)")
        fig.update_layout(hovermode="closest")
    fmt = None if horizontal else _formato_data(df[x])
    unificado = cor is not None and not horizontal
    val = "R$ %{VAL:,.2f}" if moeda else "%{VAL:,.2f}"
    if horizontal:
        modelo = "%{y}<br>" + val.replace("VAL", "x") + "<extra>%{fullData.name}</extra>"
    elif unificado:  # o cabeçalho do hover unificado já mostra o período
        modelo = val.replace("VAL", "y") + "<extra>%{fullData.name}</extra>"
    else:
        modelo = _x_hover("x", fmt) + "<br>" + val.replace("VAL", "y") + "<extra></extra>"
    fig.update_traces(hovertemplate=modelo)
    fig = _eixo_data(fig, fmt, df[x])
    if (total if total is not None else (unificado and empilhar)) and unificado:
        fig = _total_no_hover(fig, df, x, y, fmt)
    return eixo_moeda(fig, "x" if horizontal else "y") if moeda else fig


def treemap(df, caminho: list[str], valor: str, titulo=None, altura=560, raiz="Total", pct_de="do total"):
    """`raiz` nomeia o nó raiz; `pct_de` diz no hover a que total o percentual se refere."""
    d = df[df[valor] > 0]
    fig = px.treemap(d, path=[px.Constant(raiz)] + caminho, values=valor, color_discrete_sequence=CORES)
    fig.update_traces(root_color="rgba(128,128,128,0.08)", texttemplate="%{label}<br>%{percentRoot:.1%}",
                      hovertemplate=f"%{{label}}<br>R$ %{{value:,.2f}}<br>%{{percentRoot:.2%}} {pct_de}<extra></extra>",
                      marker=dict(line=dict(width=2)))
    return _layout(fig, titulo, altura, legenda=False)


def sunburst(df, caminho: list[str], valor: str, titulo=None, altura=560):
    d = df[df[valor] > 0]
    fig = px.sunburst(d, path=caminho, values=valor, color_discrete_sequence=CORES, maxdepth=3)
    fig.update_traces(hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percentRoot:.2%}<extra></extra>",
                      insidetextorientation="radial")
    return _layout(fig, titulo, altura, legenda=False)


def pareto(df: pd.DataFrame, rotulo: str, valor: str, titulo=None, altura=440, n=30):
    d = df.sort_values(valor, ascending=False).head(n).copy()
    total = df[valor].sum()
    d["acum"] = d[valor].cumsum() / total * 100 if total else 0
    fig = go.Figure()
    fig.add_bar(x=d[rotulo], y=d[valor], marker_color=CORES[0], name="Valor",
                hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
    fig = _layout(fig, titulo, altura, legenda=False)
    fig.update_xaxes(showticklabels=False)
    return eixo_moeda(fig), d


def indicador_limite(serie: pd.DataFrame, x: str, y: str, limites: dict[str, float], titulo=None, altura=420):
    """Linha do indicador (% da RCL) com linhas horizontais de limite legal."""
    fig = go.Figure()
    fig.add_scatter(x=serie[x], y=serie[y], mode="lines+markers+text", name="Executado", line=dict(width=2, color=CORES[0]),
                    marker=dict(size=9), text=[pct(v, 2) for v in serie[y]], textposition="top center",
                    hovertemplate="%{x}<br>%{y:.2f}% da RCL<extra></extra>")
    estilos = ["dot", "dash", "solid"]
    cores = [STATUS["alerta"], STATUS["serio"], STATUS["critico"]]
    for (nome, v), est, c in zip(limites.items(), estilos, cores):
        fig.add_hline(y=v, line=dict(color=c, width=2, dash=est), annotation_text=f"{nome}: {pct(v, 2)}",
                      annotation_position="top left", annotation_font_size=11)
    fig = _layout(fig, titulo, altura, legenda=False)
    fig.update_yaxes(ticksuffix="%")
    return fig


def progresso(itens: list[tuple[str, float, str]], esperado: float | None = None, titulo=None, altura=300):
    """Barras de progresso (% de 0 a 100) sobre um trilho cinza; `itens` = (rótulo, %, cor).

    `esperado` marca com uma linha vertical o ritmo linear do ano (ex.: 4 de 6 bimestres = 66,7%).
    """
    rot = [i[0] for i in itens]
    fig = go.Figure()
    fig.add_bar(y=rot, x=[100] * len(itens), orientation="h", marker_color="rgba(128,128,128,0.16)",
                hoverinfo="skip", showlegend=False)
    fig.add_bar(y=rot, x=[i[1] for i in itens], orientation="h", marker_color=[i[2] for i in itens], showlegend=False,
                text=[pct(i[1]) for i in itens], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>")
    fig = _layout(fig, titulo, altura, legenda=False)
    fig.update_layout(barmode="overlay", bargap=0.45)
    fig.update_xaxes(range=[0, 108], ticksuffix="%", gridcolor="rgba(128,128,128,0.18)", dtick=25)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    if esperado is not None:
        fig.add_vline(x=esperado, line=dict(color=OUTROS, width=2, dash="dot"),
                      annotation_text=f"ritmo linear: {pct(esperado)}", annotation_position="top",
                      annotation_font_size=11)
    return fig


def resultado_vs_meta(df: pd.DataFrame, x: str, valor: str, meta: str, titulo=None, altura=420):
    """Barras do resultado apurado (verde se ≥ meta, vermelho se abaixo) e degraus da meta anual."""
    fig = go.Figure()
    cor = [STATUS["bom"] if v >= m else STATUS["critico"] for v, m in zip(df[valor], df[meta])]
    fig.add_bar(x=df[x], y=df[valor], marker_color=cor, name="Apurado até o bimestre",
                hovertemplate="%{x}<br>Apurado: R$ %{y:,.2f}<extra></extra>")
    fig.add_scatter(x=df[x], y=df[meta], mode="lines+markers", line=dict(color=OUTROS, width=2, dash="dash", shape="hv"),
                    marker=dict(size=6), name="Meta anual da LDO", hovertemplate="%{x}<br>Meta: R$ %{y:,.2f}<extra></extra>")
    fig = _layout(fig, titulo, altura, legenda=True)
    fig.update_layout(hovermode="closest")
    return eixo_moeda(fig)


def percentuais_minimo(df: pd.DataFrame, x: str, series: dict[str, tuple[str, float, str]], titulo=None, altura=420):
    """Linhas de % aplicado com a linha do mínimo legal de cada série; `series` = {coluna: (nome, mínimo, cor)}."""
    fig = go.Figure()
    for col, (nome, minimo, cor) in series.items():
        fig.add_scatter(x=df[x], y=df[col], mode="lines+markers", name=nome, line=dict(width=2, color=cor),
                        marker=dict(size=7), connectgaps=True, hovertemplate=f"{nome}<br>%{{x}}: %{{y:.2f}}%<extra></extra>")
        fig.add_hline(y=minimo, line=dict(color=cor, width=1.5, dash="dot"), annotation_text=f"mínimo {pct(minimo, 0)}",
                      annotation_position="top left", annotation_font_size=11, annotation_font_color=cor)
    fig = _layout(fig, titulo, altura, legenda=True)
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return fig


def notas_com_faixas(df: pd.DataFrame, x: str, series: dict[str, tuple[str, str]], faixas: list[tuple[float, str, str]],
                     titulo=None, altura=440):
    """Notas de 0 a 1 em linhas sobre faixas de conceito; `series` = {coluna: (nome, cor)};
    `faixas` = [(limite inferior, nome, cor da faixa)], da melhor para a pior."""
    fig = go.Figure()
    topo = 1.0
    for lim, nome, cor in faixas:
        fig.add_hrect(y0=lim, y1=topo, fillcolor=cor, opacity=0.07, line_width=0, layer="below",
                      annotation_text=nome, annotation_position="top left", annotation_font_size=10,
                      annotation_font_color=cor)
        topo = lim
    for col, (nome, cor) in series.items():
        grossa = col == list(series)[0]
        fig.add_scatter(x=df[x], y=df[col], mode="lines+markers", name=nome, connectgaps=False,
                        line=dict(width=3.5 if grossa else 1.8, color=cor, dash=None if grossa else "solid"),
                        marker=dict(size=8 if grossa else 5), hovertemplate=f"{nome}<br>%{{x}}: %{{y:.3f}}<extra></extra>")
    fig = _layout(fig, titulo, altura, legenda=True)
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(range=[0, 1.04], dtick=0.2, tickformat=".1f")
    return fig
