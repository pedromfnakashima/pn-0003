# Painel Fiscal de Mato Grosso do Sul

Painel em **Streamlit** para acompanhar as receitas e despesas do Estado de MS a partir das fontes primárias.
A coleta "em tempo real" usa **Playwright**, que lê o Portal da Transparência como um navegador. Os testes
ponta a ponta também usam o Playwright.

## Como rodar

```bash
conda activate llm_001
cd dashboard
pip install -r requirements-dev.txt && python -m playwright install chromium   # só na primeira vez

python coletar.py --tudo        # primeira carga (~20–30 min): Siconfi, RREO das UFs, dados abertos, portal, IPCA
streamlit run app.py            # abre em http://localhost:8501
```

Para atualizar depois:

| Comando | Fonte | Frequência da fonte | Duração |
|---|---|---|---|
| `python coletar.py --portal` | Portal da Transparência (Playwright) | diária | 2–4 min |
| `python coletar.py --siconfi` | MSC (mensal), RREO (bimestral), RGF (quadrimestral) | mensal | 1–3 min (incremental) |
| `python coletar.py --rreo-estados` | RREO das 27 UFs, últimos 4 exercícios (Siconfi) | bimestral | 1–5 min (incremental; ~10 min na 1ª carga) |
| `python coletar.py --rgf-estados` | RGF das 27 UFs e dos 5 Poderes, últimos 4 exercícios (Siconfi) | quadrimestral | 2–5 min (incremental; ~10 min na 1ª carga) |
| `python coletar.py --credores --repasses` | dados.ms.gov.br | mensal | 1–3 min |
| `python coletar.py --ipca` | IBGE (tabela 1737; reserva SIDRA e BCB/SGS 433) | mensal | ~10 s |

A barra lateral do painel tem botões que rodam essas mesmas coletas.
Para manter o painel em dia sem intervenção, agende a coleta (`crontab -e`):

```cron
# portal todo dia útil às 7h e 19h; demais fontes no dia 16 de cada mês
0 7,19 * * 1-5  cd ~/Documentos/Projetos/MeusProjetos/Permanentes/pn-0003/dashboard && ~/anaconda3/envs/llm_001/bin/python coletar.py --portal
30 7 16 * *     cd ~/Documentos/Projetos/MeusProjetos/Permanentes/pn-0003/dashboard && ~/anaconda3/envs/llm_001/bin/python coletar.py --siconfi --rreo-estados --credores --repasses --ipca
```

Os dados ficam em `../dados/dashboard/` (Parquet, um arquivo por período, nenhum acima de 1 MB) e são versionados no
Git: o painel funciona logo após o `git clone`, sem coletar nada. O painel recarrega sozinho quando os arquivos mudam.

## Deploy no Streamlit Community Cloud

1. Faça commit e push do repositório (inclusive `dados/dashboard/`).
2. Em share.streamlit.io › *Create app*, escolha o repositório, o ramo `main` e **Main file path** `dashboard/app.py`.
   As dependências vêm de `dashboard/requirements.txt`; o tema, de `.streamlit/config.toml`.
   As versões ficam fixas no `requirements.txt` para o Cloud rodar o mesmo que foi testado; use as mesmas no ambiente
   local (`pip install -r requirements.txt`).
3. Os botões de **Atualizar dados** funcionam na nuvem (IPCA, Siconfi, RREO das UFs, dados abertos), mas o disco do
   Cloud é temporário: o que for baixado vale até o app reiniciar. Para tornar a atualização permanente, rode a coleta
   localmente (ou no cron) e faça commit dos Parquet. O botão do Portal da Transparência fica desabilitado na nuvem,
   porque exige o Chromium do Playwright.

### Desempenho na nuvem

O Community Cloud dá ao app uma fração pequena de um núcleo de CPU. Enquanto o script de uma página roda, o mesmo
processo Python também entrega os arquivos JavaScript do navegador; se o script passa muito tempo em código Python
linha a linha, esses arquivos atrasam e o navegador mostra `TypeError: Failed to fetch dynamically imported module`.
Por isso as cargas e transformações trabalham com valores distintos e categorias, em vez de `.map`/`astype(str)`
sobre centenas de milhares de linhas, e as séries pesadas ficam em `st.cache_data`. Ao escrever código novo para o
painel, siga o mesmo padrão (`transformacoes.distintos`, `ui.filtro_multiplo`, `ui.aplicar_filtro`).

## Páginas

| Página | Conteúdo | Fonte |
|---|---|---|
| Visão geral | Execução do ano até hoje (portal), acumulado do exercício contra o ano anterior (MSC), limites de pessoal por Poder | Portal, MSC, RGF |
| Tempo real | Movimento diário de despesa (empenho, liquidação, pagamento) e de receita por órgão; mês corrente por órgão | Portal (Playwright) |
| Receitas | Natureza da receita em todos os níveis do MCASP; ICMS, IPVA, ITCD, IRRF, FPE, FUNDEB…; bruta × deduções; árvore do portal até hoje | MSC, portal |
| Despesas | Estágios; função e subfunção; categoria, grupo, modalidade e elemento; fontes de recursos; restos a pagar | MSC |
| Órgãos e fornecedores | Órgãos, ranking e concentração de credores (HHI, curva), ficha do credor, elemento, tipo de licitação, mês corrente | Despesas por Credor, portal |
| Transferências | Repasses constitucionais por município; transferências por modalidade (municípios, fundo a fundo, entidades, consórcios) | Repasses, MSC, credores |
| RREO | Destaques (balanço, funções, mínimos de educação e saúde, resultados primário e nominal, RCL mensal), séries por linha e anexo completo; **aba Anexos**: todos os anexos do RREO das 27 UFs, últimos 4 exercícios, em séries mensais (colunas `<MR-k>`), comparação entre Estados e dentro de um Estado, em R$ ou % da RCL | Siconfi |
| RGF | Abas legadas de MS (pessoal por Poder, dívida, anexo completo); **aba Anexos**: todos os anexos do RGF das 27 UFs, por Poder e somados, em séries mensais, entre Estados e dentro de um Estado, e a sub-aba **Limites da LRF** (pessoal por Poder e total, dívida, garantias e operações de crédito, quadro de cumprimento das 27 UFs) | Siconfi |
| Fontes e metodologia | Situação das bases, extrato de entregas ao Siconfi, cálculos e cuidados de interpretação | — |

Todas as páginas têm filtros na parte de cima, tabelas com ordenação e download em CSV, opção global de
valores reais (IPCA), um glossário de siglas e um quadro "Base normativa" com os itens do MCASP e os artigos da LRF
correspondentes. Cada gráfico e tabela traz a legenda "Fonte primária", cuja tooltip mostra a página, o formato, o
endpoint com os parâmetros e o nome do arquivo de origem. Essas informações vêm do catálogo em
`ms_fiscal/fontes_dados.py`, também exibido na página Fontes e metodologia. Acima de cada conjunto de filtros, o quadro
"De onde vêm as opções dos filtros" (`ui.explicar_filtros`) explica a origem de cada opção: campo da API, coluna do
CSV, lista fixa ou classificação do painel.

## Conferência dos números

- Receita líquida sem intraorçamentárias de jan a ago/2026 calculada da MSC: **R$ 17,913 bi**, igual à linha
  "Receitas (exceto intra-orçamentárias)" do RREO, Anexo 1, 4º bimestre/2026.
- Despesa liquidada sem intraorçamentárias de jan a ago/2026 calculada da MSC: **R$ 17,569 bi**, igual ao total do RREO, Anexo 2.

## Testes

```bash
pytest tests/test_dashboard_e2e.py -q     # sobe o Streamlit, abre cada página no Chromium e testa interações,
                                          # a aba Anexos do RREO e os botões de atualização (IPCA, RREO das UFs)
```

As capturas de tela ficam em `tests/capturas/`.

## Estrutura

```
dashboard/
├── app.py                 # navegação e barra lateral
├── coletar.py             # linha de comando da coleta
├── ms_fiscal/
│   ├── siconfi.py         # API do Siconfi: extrato, MSC, RREO, RGF
│   ├── rreo_estados.py    # RREO das 27 UFs: coleta, séries mensais <MR-k>, % da RCL
│   ├── rgf_estados.py     # RGF das 27 UFs e 5 Poderes: coleta, séries mensais, limites da LRF
│   ├── portal.py          # Playwright no Portal da Transparência
│   ├── dados_abertos.py   # CKAN de MS (credores, repasses) e IPCA (IBGE)
│   ├── transformacoes.py  # MSC → receitas/despesas analíticas; deflação
│   ├── relatorios.py      # séries e tabelas dos anexos do RREO e do RGF
│   ├── referencias.py     # MCASP, LRF, funções, naturezas, modalidades, fontes
│   ├── graficos.py        # Plotly com paleta validada para daltonismo
│   └── ui.py              # carga com cache, filtros, tabelas, status
├── paginas/               # uma página por arquivo
└── tests/                 # testes ponta a ponta com Playwright
```

## Limitações conhecidas

- O Portal da Transparência depende de um token emitido ao navegador. Se o portal mudar de leiaute ou de API, a coleta
  diária falha, mas as demais fontes continuam funcionando.
- A Receita Simplificada do portal é líquida das deduções; a MSC mostra a receita bruta e as deduções separadas.
- Desde 2026 a renúncia de ICMS é registrada como receita bruta e dedução ao mesmo tempo. Use "bruta exceto renúncia"
  para comparar com anos anteriores.
- O conjunto de repasses a municípios tem meses sem arquivo ou sem ICMS/IPVA (o painel lista quais).
- Os arquivos de Despesas por Credor de 05 a 08/2025 foram publicados com aspas duplicadas e quebras de linha fora
  das aspas, o que desloca as colunas. A leitura (`ms_fiscal/dados_abertos.py`) recompõe esses registros e recusa
  meses que continuem deslocados. A fonte também corta nomes em 80 caracteres, que o painel completa quando o nome
  oficial é conhecido ou marca com "…".
- A classificação dos credores (empresa, ente público, financeira, pessoa física) é heurística, feita pelo CNPJ e pelo nome.

## RREO de todas as UFs (aba Anexos)

- **Coleta**: `/rreo` do Siconfi exige `id_ente`, então são 27 consultas por bimestre (UFs do endpoint `/entes`; o DF
  aparece como esfera "D" em `/entes`, mas é publicado com `co_esfera=E` no `/rreo`). A API devolve 429 quando há
  consultas demais seguidas; a coleta usa 3 conexões e espera progressiva.
- **Arquivos**: `dados/dashboard/rreo_estados/rreo_uf_AAAA_B.parquet` (todas as UFs de um bimestre, zstd, texto como
  dicionário, ~0,5–1 MB) e `entes.parquet`. Cada atualização refaz os 2 bimestres mais recentes e os que faltarem UFs.
- **Séries mensais**: no Anexo 3, `<MR>` é o último mês do bimestre e `<MR-k>` o k-ésimo mês anterior; cada mês vem
  do relatório mais recente que o contém. Os demais anexos não têm colunas mensais: cada relatório é um ponto no seu
  mês de referência (fev, abr, jun, ago, out, dez), com opção de desacumular as colunas "até o bimestre".
- **% da RCL**: valor ÷ RCL de 12 meses da mesma UF (Anexo 3, `RREO3ReceitaCorrenteLiquida`).

## RGF de todas as UFs (aba Anexos do RGF)

- **Coleta**: `/rgf` exige `id_ente` e `co_poder` (sem o Poder a API devolve vazio): 27 UFs × 5 Poderes por
  quadrimestre. Arquivos: `dados/dashboard/rgf_estados/rgf_uf_AAAA_Q.parquet` (~0,3 MB cada).
- **Poderes**: cada um isoladamente ou *Todos os Poderes (soma)*. No Legislativo, Assembleia e Tribunal de Contas
  publicam RGFs separados e são somados. Um ponto da soma só entra se todas as instituições publicaram.
- **Séries mensais**: Anexo 1 (pessoal) tem `<MR-11>` … `<MR>` (`<MR>` = abr, ago ou dez) → série mensal de fato; a soma
  de 12 meses confere ao centavo com o 'TOTAL (ÚLTIMOS 12 MESES)' publicado. Saldos dos Anexos 2 e 3 → posição no fim
  de cada quadrimestre (opção de interpolação linear mensal). Colunas do quadrimestre ou acumuladas → valor do
  quadrimestre e média mensal (÷ 4). Interpolação e média mensal são construções do painel.
- **Limites da LRF**: pessoal com DTP e limites publicados por instituição (R$ ÷ RCL ajustada), por Poder e no total do
  Estado (60%); DCL ≤ 200% da RCL, garantias ≤ 22%, operações de crédito ≤ 16% (resoluções do Senado 40 e 43/2001), alerta
  em 90%. A Defensoria Pública não tem limite próprio no art. 20 e o RGF dela na API não traz DTP: o painel mostra a
  despesa líquida de 12 meses + RP não processados ÷ RCL ajustada, sem limite e fora do total.

## Abas Resumo do RREO e do RGF

- **RREO › Resumo** (`paginas/rreo_resumo.py`, `ms_fiscal/indicadores_rreo.py`): os indicadores do *RREO em Foco:
  Estados + DF* (Tesouro Nacional) recalculados para as 27 UFs e todos os bimestres desde 2023 — crescimento de receita e
  despesa correntes, resultado orçamentário, poupança corrente, dependência de transferências, composição da despesa
  sobre a receita total, RPPS, resultado primário com e sem RPPS, variação da dívida. Mostra os destaques negativos de
  MS (quartil pior), série temporal de MS contra a mediana e o intervalo interquartil das UFs, ranking e tabela de
  estatísticas descritivas (mínimo, quartis, média, desvio, posição, escore z). As definições foram conferidas com a
  edição do 3º bimestre de 2026 (MS, SP, GO, AC, PR): o Tesouro soma as intraorçamentárias, deduz as transferências a
  municípios registradas como despesa e usa despesas **liquidadas** (o texto fala em empenhadas).
- **RGF › Resumo** (`paginas/rgf_resumo.py`): cumprimento dos limites da LRF por MS no quadrimestre escolhido — síntese
  em texto com as consequências legais, cartões com folga até o máximo (p.p. e R$), uso de cada limite, histórico de
  situações por quadrimestre e gráficos de pessoal do Estado e do Executivo.

### Limites de pessoal por esfera, Poder e UF

O painel avalia cada Poder e o total pelo **limite legal** que se aplica à UF (LRF, arts. 19 e 20; `rgf_estados.limite_legal`):
Estados 60% (Executivo 49%, Legislativo 3%, Judiciário 6%, Ministério Público 2%); **BA, GO e PA**, que têm Tribunal de
Contas dos Municípios, Executivo 48,6% e Legislativo 3,4% (art. 20, §4º); **DF**, total de 52% (Executivo + Legislativo;
Judiciário e MP são mantidos pela União, CF art. 21, XIII). Prudencial = 95% e alerta = 90% do limite de cada Poder. O limite
que a UF publica no RGF fica ao lado para conferência; divergências acima de 0,05 p.p. são listadas (ex.: o CE ainda publica
3,4% no Legislativo após extinguir o TCM em 2017). União (50%) e Municípios (60%; Executivo 54%, Legislativo 6%) aparecem na
tabela de referência.

### Paralelos com o RREO em Foco (tooltips)

Página oficial e histórico de edições: https://www.tesourotransparente.gov.br/publicacoes/rreo-em-foco-estados-e-df/2026/16.
`ms_fiscal/rreo_em_foco.py` liga cada indicador do Resumo do RREO ao gráfico/tabela correspondente do *RREO em Foco* e
guarda os valores de MS publicados nas edições do 3º bimestre (thot-arquivos.tesouro.gov.br/publicacao/55399) e do 4º
bimestre de 2026 (…/publicacao/56111), que têm a mesma numeração. Os tooltips (ícone ⓘ) dos cartões, gráficos e tabela
mostram esse paralelo. Para outras edições localizadas (1º e 2º bim/2026, 6º bim/2025 e 2024) o tooltip dá o link e o
título do gráfico, porque a numeração muda entre edições. Todos os indicadores do Resumo são **acumulados de janeiro ao
fim do bimestre** (não só o bimestre nem 12 meses); os "÷ RCL" usam a RCL de 12 meses × meses decorridos ÷ 12.
