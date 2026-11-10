# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Fiscal dashboard for the State of Mato Grosso do Sul (MS), Brazil, built with Streamlit: revenue, expenditure, RREO and RGF, and comparison across the 27 states (UFs). The UI, code identifiers, comments and docs are in Portuguese; keep new code and text in Portuguese. `dashboard/README.md` is the detailed reference (data sources, methodology, LRF limits, how indicators are computed).

## Commands

Run from `dashboard/` with the conda env `llm_001` (`~/anaconda3/envs/llm_001/bin/python`):

```bash
pip install -r requirements-dev.txt && python -m playwright install chromium   # first time
streamlit run app.py                         # http://localhost:8501
python coletar.py --tudo                     # full data collection (~20–30 min)
python coletar.py --siconfi | --rreo-estados | --rgf-estados | --credores --repasses | --ipca | --portal
pytest tests/test_dashboard_e2e.py -q        # end-to-end: starts Streamlit, drives Chromium via Playwright
pytest tests/test_dashboard_e2e.py -q -k rgf_anexos      # a single test
python -m pyflakes ms_fiscal paginas app.py coletar.py   # lint
```

- The only tests are the Playwright end-to-end tests. Screenshots go to `tests/capturas/` (gitignored).
- `test_botoes_atualizacao_e_ipca` clicks the "Atualizar dados" buttons, which download data and overwrite versioned Parquet files under `dados/dashboard/`. Check `git status` afterwards and `git checkout` those files unless the update is intended.

## Deployment and pinned versions

- The app is deployed on Streamlit Community Cloud from branch `main`, with main file `dashboard/app.py` (https://dados-fiscais.streamlit.app/). Pushing to `main` redeploys.
- `dashboard/requirements.txt` pins exact versions (Streamlit 1.66, pandas 3.x, pyarrow, numpy) so Cloud runs what was tested. Code must work on pandas 3: for example, a dict-based `.map` can change a column's dtype.
- Data is committed as Parquet in `dados/dashboard/`, so the app works right after `git clone`. Cloud disk is ephemeral: data downloaded on Cloud is lost on restart, so permanent updates come from collecting locally and committing the Parquet files.
- The Portal da Transparência collector needs Playwright's Chromium and is disabled on Cloud (`ui.playwright_disponivel()`, `ui.em_nuvem()`).

## Architecture

- **Data flow.** `coletar.py` (CLI) calls collectors in `ms_fiscal/`, which write Parquet files to `config.DIR_DADOS` (`dados/dashboard/`, overridable with env `MS_FISCAL_DADOS`). The pages only read those files; they never call external APIs while rendering. The sidebar's "Atualizar dados" buttons run `coletar.py` as a subprocess (`ui.executar_coleta`) and then clear the Streamlit caches.
- **Collectors and transforms (`ms_fiscal/`).**
  - Source modules:
    - `siconfi.py`: MSC, RREO and RGF for MS.
    - `rreo_estados.py` / `rgf_estados.py`: all 27 UFs; RGF also covers all 5 Poderes.
    - `dados_abertos.py`: CKAN credores/repasses and IPCA.
    - `portal.py`: Playwright.
  - Each source module also owns loading and preparing its own files. `transformacoes.py` turns MSC accounts into analytic revenue and expenditure tables, and does deflation. `relatorios.py` builds series and tables from the RREO/RGF annexes.
  - Siconfi `/rreo` and `/rgf` require one query per `id_ente` (per Poder too, for RGF), are rate-limited (HTTP 429), and are collected incrementally (one file per period).
- **Caching (`ms_fiscal/ui.py`).** Loaders are wrapped in `st.cache_data` / `st.cache_resource`, with a "signature" argument (`_assinatura(dir)`, derived from the data files) as the cache key, so the app reloads automatically when files change. Pages call the public wrappers (`ui.receitas_msc()`, `ui.rreo_uf()`, `ui.rgf_uf()`, …), not the collectors.
- **Pages.**
  - `app.py` builds `st.navigation` from `paginas/*.render`. Larger pages delegate tabs to sibling modules: `rreo.py` to `rreo_resumo.py` and `rreo_anexos.py`, and `rgf.py` to `rgf_resumo.py` and `rgf_anexos.py`.
  - Charts are Plotly (`graficos.py`, colorblind-safe palette). Render them through `ui.grafico(fig, chave, *fontes, nota=...)` and tables through `ui.tabela(...)`, so each output gets the "Fonte primária" caption.
  - Source keys (e.g. `"siconfi_rgf_uf"`) refer to the catalog in `fontes_dados.py`. Legal and accounting references (MCASP, LRF articles, classifications) live in `referencias.py`. The RREO em Foco parallels live in `rreo_em_foco.py`, and the RREO indicators in `indicadores_rreo.py`.
- **Global options.** The "Valores reais (IPCA)" toggle (`ui.valores_reais()`, `ui.ajustar(df, cols)`) must be honored by any monthly monetary output.

## Performance rule (important)

Cloud gives the app a fraction of one CPU, and the same Python process serves the frontend's JS chunks. Long row-by-row Python work in a page script makes those requests fail in the browser with `TypeError: Failed to fetch dynamically imported module`. Therefore:
- Never use `.map`, `.apply` or `astype(str)` over hundreds of thousands of rows. Compute once per distinct value or category, then broadcast: see `transformacoes.distintos` and `transformacoes._por_valor`, and `dados_abertos._remapear`.
- Build filter options and apply filters with `ui.filtro_multiplo` and `ui.aplicar_filtro`, which work on categories.
- Concatenate Parquet files with pyarrow (`pa.concat_tables(...).to_pandas()`), not per-row pandas loops.
- Wrap heavy derived series in `st.cache_data`, keyed by the data signature (e.g. `_estatisticas(dados["assin"], ...)` in `rreo_resumo.py`).
- When changing a transformation, check the result against the previous output with `pd.testing.assert_frame_equal`, dtypes included.

## Diagrams and flowcharts

When asked for a diagram or flowchart, use the [Archify](https://github.com/tt-a1i/archify) skill (`archify`), whether it stands alone or goes inside a report. Do not hand-draw SVG or Mermaid.

- **Location.** The skill is installed globally at `~/.claude/skills/archify`. If it is missing or fails, check it with `node ~/.claude/skills/archify/bin/archify.mjs doctor`.
- **Diagram types.** Archify covers architecture, workflow/flowchart, sequence, dataflow, lifecycle/state, ERD, class, tree, timeline and waterfall.
- **Output.** Archify produces a standalone interactive HTML file. Save it next to the related document and link it from there, or embed it when the user asks.

## Other folders

- `dados/dashboard/`: versioned Parquet data, each file under 1 MB.
- `anotacoes/`: the user's untracked notes.
