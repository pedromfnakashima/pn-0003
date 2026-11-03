"""Paralelos entre os indicadores do painel e o "RREO em Foco: Estados e DF" (Tesouro Nacional).

Fontes oficiais (domínios do Tesouro Nacional):
- página da publicação, com o histórico de edições: https://www.tesourotransparente.gov.br/publicacoes/rreo-em-foco-estados-e-df/2026/16
  (/2026/13 a /2026/16 = 1º a 4º bimestre de 2026);
- PDF do 3º bimestre de 2026: https://thot-arquivos.tesouro.gov.br/publicacao/55399 (dados extraídos em 03/08/2026);
- PDF do 4º bimestre de 2026: https://thot-arquivos.tesouro.gov.br/publicacao/56111 (dados extraídos em 01/10/2026).
Os números de gráficos e tabelas são os mesmos nessas duas edições; os valores de MS abaixo foram transcritos delas.
"""
from __future__ import annotations

from .graficos import MESES

TT = "https://www.tesourotransparente.gov.br/publicacoes/rreo-em-foco-estados-e-df"
PAGINA_SERIE = f"{TT}/2026/16"  # página da edição mais recente, com o histórico de todas as edições (2017–2026)
PAGINAS = {(2026, 1): f"{TT}/2026/13", (2026, 2): f"{TT}/2026/14", (2026, 3): f"{TT}/2026/15", (2026, 4): f"{TT}/2026/16"}

EDICOES = {  # (exercício, bimestre): (URL do PDF, data da extração dos dados)
    (2026, 3): ("https://thot-arquivos.tesouro.gov.br/publicacao/55399", "03/08/2026"),
    (2026, 4): ("https://thot-arquivos.tesouro.gov.br/publicacao/56111", "01/10/2026"),
}
_THOT = "https://thot-arquivos.tesouro.gov.br/publicacao"
# Outras edições localizadas (bimestre conferido na capa). A numeração dos gráficos MUDA entre edições (ex.: 12 gráficos
# em 2024 e no 1º/2º bimestre de 2026, 13 no 3º/4º de 2026), então para elas o painel indica o título, não o número.
OUTRAS_EDICOES = {
    (2026, 1): f"{_THOT}/54471",
    (2026, 2): f"{_THOT}/54955",
    (2025, 6): f"{_THOT}/53966",
    (2024, 6): f"{_THOT}/51431",
}

# indicador do painel → (gráfico/tabela da publicação, observação sobre o período ou a definição). Números conforme as
# edições do 3º e do 4º bimestres de 2026.
FIGURAS = {
    "cresc_receita": ("Gráfico 1 – Crescimento das Receitas e Despesas Correntes (e tabela do gráfico)",
                      "o texto diz \"referente ao Nº bimestre\", mas os valores publicados são acumulados de janeiro "
                      "ao fim do bimestre (no 4º/2026, MS: R$ 18,11 bi de receita corrente, jan–ago)"),
    "cresc_despesa": ("Gráfico 1 – Crescimento das Receitas e Despesas Correntes (e tabela do gráfico)",
                      "o texto fala em despesas empenhadas, mas os valores publicados são os liquidados, acumulados "
                      "de janeiro ao fim do bimestre"),
    "dif_crescimento": ("Gráfico 1 – Crescimento das Receitas e Despesas Correntes",
                        "o painel subtrai as duas barras do gráfico (despesa − receita)"),
    "res_orcamentario": ("Gráfico 2 e Tabela 1 – Resultado Orçamentário em relação à RCL",
                         "acumulado até o bimestre ÷ RCL proporcional; despesas liquidadas (o texto diz empenhadas)"),
    "dependencia": ("Gráfico 3 – Grau de Dependência das Transferências",
                    "a publicação mostra receita própria e transferências como partes da receita corrente; o painel "
                    "mostra a parte das transferências"),
    "poupanca_corrente": ("Gráfico 4 – Poupança Corrente em relação à RCL",
                          "acumulado até o bimestre ÷ RCL proporcional"),
    "pessoal_rt": ("Gráfico 5 e Tabela 2 – Composição das Despesas em relação à Receita Total", ""),
    "custeio_rt": ("Gráfico 5 e Tabela 2 – Composição das Despesas em relação à Receita Total", ""),
    "divida_rt": ("Gráfico 5 e Tabela 2 – Composição das Despesas em relação à Receita Total", ""),
    "invest_rt": ("Gráfico 5 e Tabela 2 – Composição das Despesas em relação à Receita Total", ""),
    "despesa_rt": ("Gráfico 5 – Composição das Despesas em relação à Receita Total",
                   "o painel soma as quatro colunas da Tabela 2"),
    "rpps_capitalizacao": ("Gráfico 6 e Tabela 3 – Resultado do RPPS em relação à RCL (Fundo em Capitalização)", ""),
    "rpps_reparticao": ("Gráfico 6 e Tabela 3 – Resultado do RPPS em relação à RCL (Fundo em Repartição)", ""),
    "primario_sem_rpps": ("Gráfico 7 e Tabela 4 – Resultado Primário sem RPPS em relação à RCL", ""),
    "primario_com_rpps": ("Gráfico 8 e Tabela 5 – Resultado Primário com RPPS em relação à RCL", ""),
    "var_divida": ("Gráfico 9 – Variação da Dívida Consolidada",
                   "variação do saldo de 31/12 do ano anterior até o fim do bimestre"),
}

# Valores de MS publicados: (edição) → indicador → (valor numérico em % do exercício, texto exibido)
PUBLICADO_MS: dict[tuple[int, int], dict[str, tuple[float | None, str]]] = {
    (2026, 3): {
        "cresc_receita": (8, "8% (R$ 13,67 bi em jan–jun/2026 × R$ 12,70 bi em jan–jun/2025)"),
        "cresc_despesa": (14, "14% (R$ 12,94 bi × R$ 11,33 bi)"),
        "res_orcamentario": (4, "4% da RCL (R$ 0,50 bi); 2025: 2% (R$ 0,21 bi); MS é o 2º menor entre 27"),
        "poupanca_corrente": (None, "MS é o 1º no gráfico, o menor valor entre as 27 UFs"),
        "pessoal_rt": (60, "60% da receita total"),
        "custeio_rt": (24, "24% da receita total"),
        "divida_rt": (3, "3% da receita total"),
        "invest_rt": (9, "9% da receita total"),
        "despesa_rt": (96, "96% (60% + 24% + 3% + 9%); MS é o 25º de 27 na ordem crescente do gráfico"),
        "rpps_capitalizacao": (-8, "−8% da RCL (−R$ 869,37 mi); 2025: −5% (−R$ 520,02 mi)"),
        "primario_sem_rpps": (-4, "−4% da RCL (−R$ 0,46 bi); 2025: −2% (−R$ 0,18 bi); MS é o 2º menor"),
        "primario_com_rpps": (-3.48, "−3,48% da RCL (−R$ 0,40 bi); 2025: 0,06% (R$ 0,01 bi); MS é o 2º menor"),
        "var_divida": (None, "MS é o 25º de 27 na ordem crescente do gráfico (entre as maiores altas)"),
    },
    (2026, 4): {
        "cresc_receita": (8, "8% (R$ 18,11 bi em jan–ago/2026 × R$ 16,76 bi em jan–ago/2025)"),
        "cresc_despesa": (12, "12% (R$ 17,03 bi × R$ 15,19 bi)"),
        "res_orcamentario": (1, "1% da RCL (R$ 0,20 bi); 2025: −0% (−R$ 0,03 bi); MS é o 2º menor entre 27"),
        "poupanca_corrente": (None, "MS é o 2º no gráfico, o 2º menor valor entre as 27 UFs"),
        "pessoal_rt": (60, "60% da receita total"),
        "custeio_rt": (26, "26% da receita total"),
        "divida_rt": (3, "3% da receita total"),
        "invest_rt": (10, "10% da receita total"),
        "despesa_rt": (99, "99% (60% + 26% + 3% + 10%)"),
        "rpps_capitalizacao": (-7, "−7% da RCL (−R$ 1.016,70 mi); 2025: −6% (−R$ 850,78 mi)"),
        "primario_sem_rpps": (-5, "−5% da RCL (−R$ 0,81 bi); 2025: −1% (−R$ 0,17 bi); MS é o 3º menor"),
        "primario_com_rpps": (-4.63, "−4,63% da RCL (−R$ 0,71 bi); 2025: −0,72% (−R$ 0,10 bi); MS é o 5º menor"),
    },
}


def tooltip(indicador: str, exercicio: int, bimestre: int) -> str:
    """Texto (markdown) com o paralelo do indicador no RREO em Foco, para usar em `help=`."""
    fig, obs = FIGURAS.get(indicador, ("", ""))
    if not fig:
        return "Sem paralelo direto no RREO em Foco."
    linhas = [f"**Paralelo no RREO em Foco (Tesouro Nacional):** {fig}."]
    if obs:
        linhas.append(f"Observação: {obs}.")
    ed = EDICOES.get((exercicio, bimestre))
    if ed:
        pub = PUBLICADO_MS.get((exercicio, bimestre), {}).get(indicador)
        linhas.append(f"Edição do {bimestre}º bimestre de {exercicio} — página: {PAGINAS[(exercicio, bimestre)]}; "
                      f"PDF: {ed[0]}; dados extraídos em {ed[1]}"
                      + (f". **Publicado para MS:** {pub[1]}." if pub else "."))
        linhas.append("Diferenças pequenas em relação ao painel vêm do arredondamento da publicação e da data de "
                      "extração (o painel usa o Siconfi mais recente, com retificações).")
    elif (exercicio, bimestre) in OUTRAS_EDICOES:
        titulo = fig.split(" – ", 1)[-1]
        pag = PAGINAS.get((exercicio, bimestre))
        linhas.append(f"Edição do {bimestre}º bimestre de {exercicio}: " + (f"página {pag}; " if pag else "")
                      + f"PDF {OUTRAS_EDICOES[(exercicio, bimestre)]} — "
                      f"procure o gráfico \"{titulo}\" (nesta edição a numeração dos gráficos pode ser outra; os "
                      "números citados acima valem para as edições do 3º e 4º bimestres de 2026).")
    else:
        conhecidas = ", ".join(f"{b}º bim/{a}: {u}" for (a, b), (u, _) in sorted(EDICOES.items()))
        linhas.append(f"Edição do {bimestre}º bimestre de {exercicio}: consulte o histórico de edições em "
                      f"{PAGINA_SERIE} (filtro por ano). Edições conferidas no painel: {conhecidas}.")
    return "\n\n".join(linhas)


def periodo(indicador: str, exercicio: int, bimestre: int) -> str:
    """Período coberto pelo indicador, por extenso."""
    mes = MESES[2 * bimestre - 1]
    if indicador == "var_divida":
        return f"variação de 31/12/{exercicio - 1} ao fim de {mes}/{exercicio} ({bimestre}º bimestre)"
    if indicador in ("cresc_receita", "cresc_despesa", "dif_crescimento"):
        return f"jan–{mes}/{exercicio} contra jan–{mes}/{exercicio - 1} (acumulado até o {bimestre}º bimestre)"
    return f"acumulado de jan a {mes}/{exercicio} (até o {bimestre}º bimestre)"
