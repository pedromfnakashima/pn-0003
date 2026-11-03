# pn-0003 – Painel Fiscal de Mato Grosso do Sul

Painel em Streamlit com receitas, despesas, RREO e RGF do Estado de MS, e comparação do RREO entre as 27 UFs.

```bash
conda activate llm_001
streamlit run dashboard/app.py
```

Detalhes (coleta, deploy no Streamlit Community Cloud, testes): [dashboard/README.md](dashboard/README.md).
Os dados do painel ficam em `dados/dashboard/` (Parquet, versionados).
