"""Fontes, periodicidade, metodologia e cuidados de interpretação."""
from __future__ import annotations

import streamlit as st

from ms_fiscal import fontes_dados as FD
from ms_fiscal import ui
from ms_fiscal.config import LRF_URL, MCASP_URL, SICONFI_DOCS


def render():
    st.title("Fontes e metodologia")
    ui.glossario()
    st.markdown("Situação das bases locais (cada uma é atualizada por `python coletar.py`):")
    st.dataframe(ui.status_fontes(), hide_index=True, width="stretch")
    st.caption("Datas de modificação dos arquivos em `dados/dashboard/`; a origem de cada base está no catálogo abaixo.")

    st.markdown("### Catálogo das fontes primárias")
    st.caption("Cada gráfico e tabela do painel cita uma destas fontes na legenda 'Fonte primária'; o ⓘ ao lado mostra "
               "o mesmo detalhe.")
    for chave in FD.FONTES:
        with st.expander(FD.FONTES[chave]["nome"]):
            st.markdown(FD.detalhe(chave))

    ex = ui.extrato()
    if not ex.empty:
        with st.expander("Entregas do Estado ao Siconfi (extrato oficial)"):
            e = ex[ex["instituicao"].str.contains("Governo do Estado")][["exercicio", "entregavel", "periodicidade", "periodo",
                                                                      "data_status", "status_relatorio", "forma_envio"]]
            ui.tabela(e, "ft_extrato", ordenar_padrao="data_status", fontes=["siconfi_extrato"],
                      nota="entregas do Governo do Estado")

    st.markdown(f"""
### Periodicidade: da mais frequente à menos frequente

| Frequência | Fonte primária | O que traz | Uso no painel |
|---|---|---|---|
| **Diária** | [Portal da Transparência de MS](https://www.transparencia.ms.gov.br/) (CGE/SEFAZ-MS), lido com **Playwright** | Despesa empenhada, liquidada e paga por órgão e por credor, com filtro de datas; receita por natureza (árvore do MCASP) e por órgão | Tempo real, mês corrente de credores, receita do ano até hoje |
| **Mensal** | [Matriz de Saldos Contábeis – Siconfi]({SICONFI_DOCS}) (`/msc_orcamentaria`, classe 6) | Receita realizada e deduções por natureza; despesa por estágio com função, subfunção, natureza, fonte e Poder | Séries mensais de receitas e despesas |
| **Mensal** | [Despesas por Credor – Mensal](https://www.dados.ms.gov.br/dataset/despesas-por-credor-mensal) (SEFAZ-MS) | Cada empenho com órgão, função, ação, elemento, modalidade, CPF/CNPJ, credor e tipo de licitação | Órgãos, fornecedores, transferências por beneficiário |
| **Mensal** | [Repasses dos Municípios](https://www.dados.ms.gov.br/dataset/repasses-dos-municipios) (SEFAZ-MS) | ICMS, IPVA, IPI-Exportação e FUNDERSUL entregues a cada município | Transferências constitucionais |
| **Bimestral** | RREO – Siconfi (`/rreo`) | Anexos 1 a 14 (LRF, arts. 52-53) | Página RREO |
| **Bimestral** | RREO de todas as UFs – Siconfi (`/rreo`, um ente por chamada) | Anexos 1 a 14 das 26 UFs e do DF, últimos 4 exercícios | Página RREO, aba Anexos (comparação entre Estados) |
| **Quadrimestral** | RGF de todas as UFs – Siconfi (`/rgf`, um ente e um Poder por chamada) | Anexos 1 a 6 das 27 UFs e dos 5 Poderes, últimos 4 exercícios | Página RGF, aba Anexos e limites da LRF |
| **Quadrimestral** | RGF – Siconfi (`/rgf`), por Poder | Pessoal, dívida, garantias, operações de crédito (LRF, arts. 54-55) | Página RGF |
| Mensal | IPCA (IBGE, tabela 1737; reserva BCB/SGS 433) | Inflação | Opção "valores reais" |

### Como os números são calculados
- **Receita (MSC)**: movimento do mês nas contas 6.2.1.2 (receita realizada) e 6.2.1.3 (deduções: FUNDEB, transferências a
  municípios, renúncia, outras), com sinal credor positivo. **Receita líquida = bruta + deduções** (estas são negativas).
- **Despesa (MSC)**: movimento do mês nas contas 6.2.2.1.3.01 a .04. Empenhada = soma das quatro; liquidada = .03 + .04; paga = .04.
  É a despesa do exercício; o pagamento de restos a pagar está nas contas 6.3.x (aba "Restos a pagar").
- **Intraorçamentárias** (receita 7/8, modalidade 91) ficam fora por padrão, como no RREO, para não contar duas vezes o mesmo recurso.
- **Rótulos da natureza da receita**: árvore do próprio portal estadual (código de 12 dígitos = 8 do MCASP + 4 de detalhamento estadual).
- **Funções, subfunções, elementos, modalidades e fontes**: tabelas das Portarias MOG 42/1999, Interministerial 163/2001 e STN 710/2021, reproduzidas no MCASP.
- **Valores reais**: cada mês é multiplicado por (índice IPCA do último mês divulgado ÷ índice do mês).

### Cuidados de interpretação (lições dos estudos do projeto pn-0001)
- **Empenho, liquidação e pagamento são coisas diferentes.** Os estudos anteriores usaram a coluna *Pago*; o painel mostra os três.
- **Folha líquida ≠ despesa com pessoal da LRF.** A folha do portal é líquida de IR e previdência e não traz encargos
  patronais nem o 13º (a partir de 2023); a despesa do RGF é bruta e corresponde a ≈ 1,6 vez a folha líquida.
- **Credores**: o mesmo fornecedor aparece com grafias diferentes; agrupe pela **raiz do CNPJ**. Rubricas como
  "VENCIMENTOS" e "IRRF" são fluxos de folha e retenções, não fornecedores. A classificação público/privado do painel é heurística.
- **Projeções lineares** (×12/8) subestimam o ano por causa da sazonalidade de dezembro; prefira comparar o mesmo período entre anos
  (o painel faz isso nos indicadores e nas curvas acumuladas).
- **Mês corrente** no portal é parcial e pode ser revisto (anulações, estornos e retificações).
- **Reorganizações de órgãos** (ex.: DGPC desmembrada da SEJUSP) quebram séries por órgão; a classificação funcional é mais estável.
- **Dados pessoais**: nomes de pessoas físicas ficam agregados por padrão (LGPD, art. 6º; a LAI não obriga a republicação individualizada).

### Referências
- [Manual de Contabilidade Aplicada ao Setor Público – MCASP]({MCASP_URL}) (STN)
- [Lei Complementar nº 101/2000 – Lei de Responsabilidade Fiscal]({LRF_URL})
- [Documentação da API do Siconfi]({SICONFI_DOCS})
- [Portal da Transparência de MS](https://www.transparencia.ms.gov.br/) · [Dados abertos de MS](https://www.dados.ms.gov.br/)
- Lei nº 4.320/1964 (normas gerais de direito financeiro); Lei nº 14.133/2021 (licitações e contratos).
""")
