"""Tabelas de classificação orçamentária e referências normativas.

As classificações seguem o Manual de Contabilidade Aplicada ao Setor Público
(MCASP, Parte I – Procedimentos Contábeis Orçamentários), que consolida:
- Portaria MOG nº 42/1999 (classificação funcional: funções e subfunções);
- Portaria Interministerial STN/SOF nº 163/2001 (natureza da despesa e da receita);
- Portaria STN nº 710/2021 (padronização das fontes ou destinações de recursos).
Os relatórios fiscais seguem a LRF (LC nº 101/2000) e o Manual de
Demonstrativos Fiscais (MDF) da STN.
"""
from __future__ import annotations

from .config import LRF_URL, MCASP_URL

# --------------------------------------------------------------------------
# Referências normativas (texto curto + link), usadas nos quadros "Base legal"
# --------------------------------------------------------------------------
LRF = {
    "art1": ("LRF, art. 1º, §1º", "Gestão fiscal responsável: ação planejada e transparente, cumprimento de metas e limites."),
    "art2iv": ("LRF, art. 2º, IV", "Receita Corrente Líquida (RCL): receitas correntes menos as transferências constitucionais a municípios e as contribuições previdenciárias; base de todos os limites."),
    "art9": ("LRF, art. 9º", "Ao fim de cada bimestre, se a receita não comportar as metas fiscais, os Poderes promovem limitação de empenho."),
    "art11": ("LRF, art. 11", "Requisito de gestão fiscal: instituição, previsão e efetiva arrecadação de todos os tributos de competência do ente (ICMS, IPVA, ITCD)."),
    "art12": ("LRF, arts. 12 e 13", "Previsão da receita e desdobramento em metas bimestrais de arrecadação."),
    "art14": ("LRF, art. 14", "Renúncia de receita (anistia, remissão, crédito presumido, isenção, alteração de base de cálculo) exige estimativa de impacto e compensação."),
    "art18": ("LRF, art. 18", "Definição de despesa total com pessoal (ativos, inativos, pensionistas, encargos e terceirização de mão de obra substitutiva)."),
    "art19": ("LRF, art. 19, II", "Limite de despesa com pessoal dos Estados: 60% da RCL."),
    "art20": ("LRF, art. 20, II", "Repartição nos Estados: Executivo 49%, Legislativo (incl. TCE) 3%, Judiciário 6%, Ministério Público 2%."),
    "art22": ("LRF, art. 22, parágrafo único", "Limite prudencial: 95% do limite máximo (46,55% da RCL para o Executivo estadual)."),
    "art23": ("LRF, art. 23", "Excedido o limite, o percentual excedente deve ser eliminado nos dois quadrimestres seguintes."),
    "art25": ("LRF, art. 25", "Transferências voluntárias: entrega de recursos a outro ente a título de cooperação, auxílio ou assistência financeira."),
    "art29": ("LRF, arts. 29 a 31", "Dívida consolidada e limites (fixados pela Resolução do Senado nº 40/2001: DCL até 200% da RCL para Estados)."),
    "art32": ("LRF, art. 32", "Operações de crédito (Res. Senado nº 43/2001: até 16% da RCL por ano)."),
    "art40": ("LRF, art. 40", "Concessão de garantias (Res. Senado nº 43/2001: até 22% da RCL)."),
    "art42": ("LRF, art. 42", "Vedação de contrair, nos dois últimos quadrimestres do mandato, obrigação sem disponibilidade de caixa."),
    "art48": ("LRF, art. 48, §1º, II", "Transparência: disponibilização, em tempo real, de informações pormenorizadas sobre a execução orçamentária e financeira, em meio eletrônico de acesso público."),
    "art48a": ("LRF, art. 48-A", "Despesa: atos das unidades gestoras no momento de sua realização, com o bem ou serviço e o beneficiário do pagamento; receita: lançamento e recebimento de toda a receita."),
    "art50": ("LRF, art. 50", "Escrituração contábil e consolidação das contas; demonstrativos por Poder e órgão."),
    "art51": ("LRF, art. 51", "Consolidação nacional das contas pelo Poder Executivo da União (Siconfi)."),
    "art52": ("LRF, arts. 52 e 53", "RREO: publicado até 30 dias após o encerramento de cada bimestre; anexos de receita, despesa por função, RCL, RPPS, resultados primário e nominal, restos a pagar."),
    "art54": ("LRF, arts. 54 e 55", "RGF: publicado por quadrimestre; despesa com pessoal, dívida consolidada, garantias, operações de crédito e, no último quadrimestre, disponibilidade de caixa e restos a pagar."),
    "art59": ("LRF, art. 59, §1º, II", "Alerta dos Tribunais de Contas quando a despesa com pessoal ultrapassar 90% do limite (44,1% da RCL para o Executivo estadual)."),
}

MCASP = {
    "receita_natureza": ("MCASP, Parte I (PCO) – Receita Orçamentária: classificação por natureza",
                         "Código de 8 dígitos: categoria econômica (1º), origem (2º), espécie (3º), desdobramentos (4º–7º) e tipo (8º)."),
    "receita_deducoes": ("MCASP, Parte I (PCO) – Deduções da Receita Orçamentária",
                         "Restituições, renúncias e transferências constitucionais ou legais a outros entes (ex.: 25% do ICMS e 50% do IPVA aos municípios; 20% ao FUNDEB) são registradas como deduções."),
    "receita_estagios": ("MCASP, Parte I (PCO) – Etapas da receita",
                         "Previsão, lançamento, arrecadação e recolhimento. A MSC registra a receita realizada na conta 6.2.1.2."),
    "despesa_funcional": ("MCASP, Parte I (PCO) – Classificação funcional (Portaria MOG nº 42/1999)",
                          "Função: maior nível de agregação das áreas de atuação; subfunção: partição da função. A subfunção pode combinar-se com funções diferentes."),
    "despesa_natureza": ("MCASP, Parte I (PCO) – Classificação da despesa por natureza (Portaria Interministerial nº 163/2001)",
                         "Código c.g.mm.ee.dd: categoria econômica, grupo de natureza de despesa, modalidade de aplicação, elemento e desdobramento."),
    "despesa_modalidade": ("MCASP, Parte I (PCO) – Modalidade de aplicação",
                           "Indica se os recursos são aplicados diretamente ou transferidos a outros entes (municípios: 40/41/42), a fundos (fundo a fundo), consórcios ou instituições privadas."),
    "despesa_estagios": ("MCASP, Parte I (PCO) – Etapas da despesa",
                         "Fixação, empenho, liquidação e pagamento (Lei nº 4.320/1964, arts. 58 a 65). Na MSC: 6.2.2.1.3.01 a .04."),
    "despesa_institucional": ("MCASP, Parte I (PCO) – Classificação institucional",
                              "Reflete a estrutura organizacional: órgãos e unidades orçamentárias."),
    "fontes": ("MCASP, Parte I (PCO) – Fonte ou destinação de recursos (Portaria STN nº 710/2021)",
               "Identifica a origem e a vinculação dos recursos; 1º dígito: 1 = exercício corrente, 2 = exercícios anteriores."),
    "restos_pagar": ("MCASP, Parte I (PCO) – Restos a pagar",
                     "Despesas empenhadas e não pagas até 31/12: processados (liquidados) e não processados."),
    "msc": ("MCASP, Parte IV (PCASP) e leiaute da Matriz de Saldos Contábeis",
            "A MSC é enviada mensalmente ao Siconfi com saldos por conta contábil e informações complementares (poder/órgão, fonte, função, natureza)."),
    "transferencias": ("MCASP, Parte I (PCO) – Transferências e delegações",
                       "Transferências constitucionais e legais (CF, arts. 158 e 159) e voluntárias (LRF, art. 25)."),
}


def link_lrf() -> str:
    return LRF_URL


def link_mcasp() -> str:
    return MCASP_URL


# --------------------------------------------------------------------------
# Classificação funcional – Portaria MOG nº 42/1999 (com atualizações)
# --------------------------------------------------------------------------
FUNCOES = {
    "01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "05": "Defesa Nacional", "06": "Segurança Pública", "07": "Relações Exteriores",
    "08": "Assistência Social", "09": "Previdência Social", "10": "Saúde", "11": "Trabalho",
    "12": "Educação", "13": "Cultura", "14": "Direitos da Cidadania", "15": "Urbanismo",
    "16": "Habitação", "17": "Saneamento", "18": "Gestão Ambiental", "19": "Ciência e Tecnologia",
    "20": "Agricultura", "21": "Organização Agrária", "22": "Indústria", "23": "Comércio e Serviços",
    "24": "Comunicações", "25": "Energia", "26": "Transporte", "27": "Desporto e Lazer",
    "28": "Encargos Especiais", "99": "Reserva de Contingência",
}

SUBFUNCOES = {
    "031": "Ação Legislativa", "032": "Controle Externo", "061": "Ação Judiciária",
    "062": "Defesa do Interesse Público no Processo Judiciário", "091": "Defesa da Ordem Jurídica",
    "092": "Representação Judicial e Extrajudicial", "121": "Planejamento e Orçamento",
    "122": "Administração Geral", "123": "Administração Financeira", "124": "Controle Interno",
    "125": "Normatização e Fiscalização", "126": "Tecnologia da Informação",
    "127": "Ordenamento Territorial", "128": "Formação de Recursos Humanos",
    "129": "Administração de Receitas", "130": "Administração de Concessões", "131": "Comunicação Social",
    "151": "Defesa Aérea", "152": "Defesa Naval", "153": "Defesa Terrestre", "181": "Policiamento",
    "182": "Defesa Civil", "183": "Informação e Inteligência", "211": "Relações Diplomáticas",
    "212": "Cooperação Internacional", "241": "Assistência ao Idoso",
    "242": "Assistência ao Portador de Deficiência", "243": "Assistência à Criança e ao Adolescente",
    "244": "Assistência Comunitária", "271": "Previdência Básica", "272": "Previdência do Regime Estatutário",
    "273": "Previdência Complementar", "274": "Previdência Especial", "301": "Atenção Básica",
    "302": "Assistência Hospitalar e Ambulatorial", "303": "Suporte Profilático e Terapêutico",
    "304": "Vigilância Sanitária", "305": "Vigilância Epidemiológica", "306": "Alimentação e Nutrição",
    "331": "Proteção e Benefícios ao Trabalhador", "332": "Relações de Trabalho", "333": "Empregabilidade",
    "334": "Fomento ao Trabalho", "361": "Ensino Fundamental", "362": "Ensino Médio",
    "363": "Ensino Profissional", "364": "Ensino Superior", "365": "Educação Infantil",
    "366": "Educação de Jovens e Adultos", "367": "Educação Especial", "368": "Educação Básica",
    "391": "Patrimônio Histórico, Artístico e Arqueológico", "392": "Difusão Cultural",
    "421": "Custódia e Reintegração Social", "422": "Direitos Individuais, Coletivos e Difusos",
    "423": "Assistência aos Povos Indígenas", "451": "Infraestrutura Urbana", "452": "Serviços Urbanos",
    "453": "Transportes Coletivos Urbanos", "481": "Habitação Rural", "482": "Habitação Urbana",
    "511": "Saneamento Básico Rural", "512": "Saneamento Básico Urbano",
    "541": "Preservação e Conservação Ambiental", "542": "Controle Ambiental",
    "543": "Recuperação de Áreas Degradadas", "544": "Recursos Hídricos", "545": "Meteorologia",
    "571": "Desenvolvimento Científico", "572": "Desenvolvimento Tecnológico e Engenharia",
    "573": "Difusão do Conhecimento Científico e Tecnológico", "601": "Promoção da Produção Vegetal",
    "602": "Promoção da Produção Animal", "603": "Defesa Sanitária Vegetal", "604": "Defesa Sanitária Animal",
    "605": "Abastecimento", "606": "Extensão Rural", "607": "Irrigação",
    "608": "Promoção da Produção Agropecuária", "609": "Defesa Agropecuária", "631": "Reforma Agrária",
    "632": "Colonização", "661": "Promoção Industrial", "662": "Produção Industrial", "663": "Mineração",
    "664": "Propriedade Industrial", "665": "Normalização e Qualidade", "691": "Promoção Comercial",
    "692": "Comercialização", "693": "Comércio Exterior", "694": "Serviços Financeiros", "695": "Turismo",
    "721": "Comunicações Postais", "722": "Telecomunicações", "751": "Conservação de Energia",
    "752": "Energia Elétrica", "753": "Combustíveis Minerais", "754": "Biocombustíveis",
    "781": "Transporte Aéreo", "782": "Transporte Rodoviário", "783": "Transporte Ferroviário",
    "784": "Transporte Hidroviário", "785": "Transportes Especiais", "811": "Desporto de Rendimento",
    "812": "Desporto Comunitário", "813": "Lazer", "841": "Refinanciamento da Dívida Interna",
    "842": "Refinanciamento da Dívida Externa", "843": "Serviço da Dívida Interna",
    "844": "Serviço da Dívida Externa", "845": "Outras Transferências", "846": "Outros Encargos Especiais",
    "847": "Transferências para a Educação Básica", "997": "Reserva do RPPS", "999": "Reserva de Contingência",
}

# --------------------------------------------------------------------------
# Natureza da despesa – Portaria Interministerial nº 163/2001 (anexo II)
# --------------------------------------------------------------------------
CATEGORIAS_DESPESA = {"3": "Despesas Correntes", "4": "Despesas de Capital", "9": "Reserva de Contingência"}

GRUPOS_DESPESA = {
    "1": "Pessoal e Encargos Sociais", "2": "Juros e Encargos da Dívida", "3": "Outras Despesas Correntes",
    "4": "Investimentos", "5": "Inversões Financeiras", "6": "Amortização da Dívida",
    "7": "Reserva do RPPS", "9": "Reserva de Contingência",
}

MODALIDADES = {
    "20": "Transferências à União", "22": "Execução Orçamentária Delegada à União",
    "30": "Transferências a Estados e ao DF", "31": "Transferências a Estados e ao DF – Fundo a Fundo",
    "32": "Execução Orçamentária Delegada a Estados e ao DF",
    "35": "Transf. Fundo a Fundo a Estados e DF (LC 141, art. 24)", "36": "Transf. Fundo a Fundo a Estados e DF (LC 141, art. 25)",
    "40": "Transferências a Municípios", "41": "Transferências a Municípios – Fundo a Fundo",
    "42": "Execução Orçamentária Delegada a Municípios",
    "45": "Transf. Fundo a Fundo a Municípios (LC 141, art. 24)", "46": "Transf. Fundo a Fundo a Municípios (LC 141, art. 25)",
    "50": "Transferências a Instituições Privadas sem Fins Lucrativos",
    "60": "Transferências a Instituições Privadas com Fins Lucrativos",
    "67": "Execução de Contrato de Parceria Público-Privada (PPP)",
    "70": "Transferências a Instituições Multigovernamentais",
    "71": "Transferências a Consórcios Públicos (contrato de rateio)",
    "72": "Execução Orçamentária Delegada a Consórcios Públicos",
    "73": "Transf. a Consórcios Públicos (LC 141, art. 24)", "74": "Transf. a Consórcios Públicos (LC 141, art. 25)",
    "75": "Transf. a Instituições Multigovernamentais (LC 141, art. 24)", "76": "Transf. a Instituições Multigovernamentais (LC 141, art. 25)",
    "80": "Transferências ao Exterior", "90": "Aplicações Diretas",
    "91": "Aplicação Direta – Operações entre Órgãos, Fundos e Entidades (intraorçamentária)",
    "93": "Aplicação Direta – Operação com Consórcio Público do qual o Ente Participe",
    "94": "Aplicação Direta – Operação com Consórcio Público do qual o Ente Não Participe",
    "95": "Aplicação Direta (LC 141, art. 24)", "96": "Aplicação Direta (LC 141, art. 25)", "99": "A Definir",
}

# Agrupamento das modalidades para análise de transferências
GRUPO_MODALIDADE = {
    **{m: "Transferências à União" for m in ("20", "22")},
    **{m: "Transferências a Estados" for m in ("30", "31", "32", "35", "36")},
    **{m: "Transferências a Municípios" for m in ("40", "41", "42", "45", "46")},
    "50": "Instituições privadas sem fins lucrativos", "60": "Instituições privadas com fins lucrativos",
    "67": "Parcerias Público-Privadas",
    **{m: "Consórcios e instituições multigovernamentais" for m in ("70", "71", "72", "73", "74", "75", "76")},
    "80": "Exterior",
    **{m: "Aplicações diretas" for m in ("90", "93", "94", "95", "96", "99")},
    "91": "Intraorçamentárias (entre órgãos e fundos do próprio Estado)",
}

ELEMENTOS = {
    "01": "Aposentadorias, Reserva Remunerada e Reformas", "03": "Pensões",
    "04": "Contratação por Tempo Determinado", "05": "Outros Benefícios Previdenciários do Servidor ou Militar",
    "06": "Benefício Mensal ao Deficiente e ao Idoso", "07": "Contribuição a Entidades Fechadas de Previdência",
    "08": "Outros Benefícios Assistenciais do Servidor e do Militar", "10": "Seguro Desemprego e Abono Salarial",
    "11": "Vencimentos e Vantagens Fixas – Pessoal Civil", "12": "Vencimentos e Vantagens Fixas – Pessoal Militar",
    "13": "Obrigações Patronais", "14": "Diárias – Civil", "15": "Diárias – Militar",
    "16": "Outras Despesas Variáveis – Pessoal Civil", "17": "Outras Despesas Variáveis – Pessoal Militar",
    "18": "Auxílio Financeiro a Estudantes", "19": "Auxílio-Fardamento", "20": "Auxílio Financeiro a Pesquisadores",
    "21": "Juros sobre a Dívida por Contrato", "22": "Outros Encargos sobre a Dívida por Contrato",
    "23": "Juros, Deságios e Descontos da Dívida Mobiliária", "24": "Outros Encargos sobre a Dívida Mobiliária",
    "25": "Encargos sobre Operações de Crédito por Antecipação da Receita",
    "27": "Encargos pela Honra de Avais, Garantias, Seguros e Similares",
    "28": "Remuneração de Cotas de Fundos Autárquicos", "29": "Distribuição de Resultado de Estatais Dependentes",
    "30": "Material de Consumo", "31": "Premiações Culturais, Artísticas, Científicas, Desportivas e Outras",
    "32": "Material, Bem ou Serviço para Distribuição Gratuita", "33": "Passagens e Despesas com Locomoção",
    "34": "Outras Despesas de Pessoal decorrentes de Contratos de Terceirização", "35": "Serviços de Consultoria",
    "36": "Outros Serviços de Terceiros – Pessoa Física", "37": "Locação de Mão de Obra", "38": "Arrendamento Mercantil",
    "39": "Outros Serviços de Terceiros – Pessoa Jurídica", "40": "Serviços de Tecnologia da Informação e Comunicação – PJ",
    "41": "Contribuições", "42": "Auxílios", "43": "Subvenções Sociais", "45": "Subvenções Econômicas",
    "46": "Auxílio-Alimentação", "47": "Obrigações Tributárias e Contributivas",
    "48": "Outros Auxílios Financeiros a Pessoas Físicas", "49": "Auxílio-Transporte", "51": "Obras e Instalações",
    "52": "Equipamentos e Material Permanente", "59": "Pensões Especiais", "61": "Aquisição de Imóveis",
    "62": "Aquisição de Produtos para Revenda", "63": "Aquisição de Títulos de Crédito",
    "64": "Aquisição de Títulos Representativos de Capital já Integralizado",
    "65": "Constituição ou Aumento de Capital de Empresas", "66": "Concessão de Empréstimos e Financiamentos",
    "67": "Depósitos Compulsórios", "70": "Rateio pela Participação em Consórcio Público",
    "71": "Principal da Dívida Contratual Resgatado", "72": "Principal da Dívida Mobiliária Resgatado",
    "73": "Correção Monetária ou Cambial da Dívida Contratual Resgatada",
    "74": "Correção Monetária ou Cambial da Dívida Mobiliária Resgatada",
    "76": "Principal Corrigido da Dívida Mobiliária Refinanciado", "77": "Principal Corrigido da Dívida Contratual Refinanciado",
    "81": "Distribuição Constitucional ou Legal de Receitas",
    "82": "Aporte de Recursos pelo Parceiro Público em favor do Parceiro Privado",
    "83": "Despesas Decorrentes de Contrato de PPP", "84": "Participação em Fundos, Organismos ou Entidades Assemelhadas",
    "85": "Contrato de Gestão", "86": "Compensação Financeira entre RGPS e RPPS", "87": "Compensações ao RGPS",
    "91": "Sentenças Judiciais", "92": "Despesas de Exercícios Anteriores", "93": "Indenizações e Restituições",
    "94": "Indenizações e Restituições Trabalhistas", "95": "Indenização pela Execução de Trabalhos de Campo",
    "96": "Ressarcimento de Despesas de Pessoal Requisitado", "97": "Aporte para Cobertura do Déficit Atuarial do RPPS",
    "98": "Compensações ao RGPS", "99": "A Classificar",
}

# --------------------------------------------------------------------------
# Fontes de recursos – Portaria STN nº 710/2021 (3 últimos dígitos)
# --------------------------------------------------------------------------
FONTES = {
    "500": "Recursos não vinculados de impostos", "501": "Outros recursos não vinculados",
    "540": "FUNDEB – impostos e transferências de impostos", "541": "FUNDEB – complementação da União (VAAF)",
    "542": "FUNDEB – complementação da União (VAAT)", "543": "FUNDEB – complementação da União (VAAR)",
    "550": "Salário-Educação", "551": "PDDE", "552": "PNAE", "553": "PNATE",
    "569": "Outras transferências do FNDE", "570": "Convênios da União – educação",
    "571": "Convênios dos Estados – educação", "572": "Convênios dos Municípios – educação",
    "573": "Royalties – educação", "574": "Operações de crédito – educação", "599": "Outros recursos vinculados à educação",
    "600": "SUS fundo a fundo – manutenção", "601": "SUS fundo a fundo – estruturação",
    "602": "SUS – outras transferências da União", "659": "Outros recursos vinculados à saúde",
    "660": "FNAS – assistência social", "661": "Assistência social – Estados",
    "669": "Outros recursos vinculados à assistência social",
    "700": "Convênios e repasses da União", "701": "Convênios e repasses dos Estados",
    "702": "Convênios e repasses dos Municípios", "703": "Transferências da União – compensações financeiras",
    "706": "Transferência especial da União", "749": "Outras vinculações de transferências",
    "750": "CIDE", "752": "Recursos vinculados ao trânsito", "753": "Taxas e contribuições vinculadas",
    "754": "Operações de crédito", "755": "Alienação de bens", "756": "Doações", "757": "Depósitos judiciais",
    "759": "Recursos vinculados a fundos", "760": "Emolumentos", "799": "Outras vinculações legais",
    "800": "RPPS – fundo em capitalização", "801": "RPPS – fundo em repartição", "802": "RPPS – taxa de administração",
    "803": "Sistema de Proteção Social dos Militares", "860": "Recursos extraorçamentários",
}


def rotulo_fonte(codigo: str | None) -> str:
    if not codigo:
        return "Não informada"
    c = str(codigo)
    ex = {"1": "exercício corrente", "2": "exercícios anteriores"}.get(c[:1], "")
    nome = FONTES.get(c[-3:], "Outras fontes")
    return f"{c} – {nome}" + (f" ({ex})" if ex else "")


# Poder/órgão informado na MSC (código de 5 dígitos)
PODER_ORGAO = {
    "10111": "Poder Executivo",
    "10112": "Poder Executivo – unidade previdenciária (RPPS)",
    "20211": "Assembleia Legislativa",
    "20212": "Tribunal de Contas do Estado",
    "30390": "Tribunal de Justiça",
    "50511": "Ministério Público",
    "60611": "Defensoria Pública",
}


def rotulo_poder(c: str | None) -> str:
    return PODER_ORGAO.get(str(c), f"Poder/órgão {c}")


# --------------------------------------------------------------------------
# Receita – grupos de interesse (prefixos da natureza de receita de 8 dígitos)
# --------------------------------------------------------------------------
# Ordem importa: o primeiro prefixo que casar define o grupo.
TRIBUTOS_CHAVE = [
    ("ICMS", "1114501", "Imposto sobre Circulação de Mercadorias e Serviços (CF, art. 155, II)"),
    ("Adicional ICMS – FECOMP", "1114502", "Adicional de ICMS para o Fundo de Combate à Pobreza (ADCT, art. 82)"),
    ("IPVA", "111251", "Imposto sobre a Propriedade de Veículos Automotores (CF, art. 155, III)"),
    ("ITCD", "111252", "Imposto sobre Transmissão Causa Mortis e Doação (CF, art. 155, I)"),
    ("IRRF", "1113", "Imposto de Renda retido na fonte pertencente ao Estado (CF, art. 157, I)"),
    ("Taxas", "112", "Taxas pelo poder de polícia e pela prestação de serviços"),
    ("Contribuições previdenciárias (RPPS/SPSM)", "1215", "Contribuições de servidores e militares"),
    ("Contribuições previdenciárias intraorçamentárias", "7215", "Contribuição patronal do próprio Estado ao RPPS"),
    ("FPE", "171150", "Cota-parte do Fundo de Participação dos Estados (CF, art. 159, I, a)"),
    ("IPI-Exportação", "171153", "Cota-parte do IPI – Estados exportadores (CF, art. 159, II)"),
    ("CIDE-Combustíveis", "171154", "Cota-parte da CIDE (CF, art. 159, III)"),
    ("Transferências do SUS", "1713", "Repasses fundo a fundo do SUS"),
    ("Transferências do FNDE", "1714", "Salário-Educação, PNAE, PNATE e outros"),
    ("Transferências do FUNDEB", "1751", "Retorno do FUNDEB ao Estado"),
    ("Compensações financeiras (royalties)", "1712", "Exploração de recursos naturais"),
    ("Transferências de instituições privadas", "1741", "Inclui recursos de fundos e contribuições privadas"),
    ("Outras transferências correntes", "17", "Demais transferências correntes"),
    ("Receita patrimonial", "13", "Rendimentos de aplicações, dividendos, concessões"),
    ("Receita de serviços", "16", "Serviços administrativos, de registro e fiscalização"),
    ("Outras receitas correntes", "19", "Multas, indenizações, restituições e demais"),
    ("Operações de crédito", "21", "Empréstimos contratados (LRF, art. 32)"),
    ("Alienação de bens", "22", "Venda de bens móveis e imóveis (LRF, art. 44)"),
    ("Amortização de empréstimos", "23", "Retorno de empréstimos concedidos"),
    ("Transferências de capital", "24", "Convênios e outras transferências de capital"),
    ("Receitas intraorçamentárias", "7", "Operações entre órgãos do próprio Estado"),
    ("Receitas de capital intraorçamentárias", "8", "Operações de capital entre órgãos do próprio Estado"),
]


def tributo_chave(natureza8: str | None) -> str:
    if not natureza8:
        return "Não informada"
    n = str(natureza8)
    for nome, pref, _ in TRIBUTOS_CHAVE:
        if n.startswith(pref):
            return nome
    return "Demais receitas correntes" if n.startswith("1") else "Demais receitas"


CATEGORIAS_RECEITA = {
    "1": "Receitas Correntes", "2": "Receitas de Capital",
    "7": "Receitas Correntes Intraorçamentárias", "8": "Receitas de Capital Intraorçamentárias",
}
ORIGENS_RECEITA = {
    "11": "Impostos, Taxas e Contribuições de Melhoria", "12": "Contribuições", "13": "Receita Patrimonial",
    "14": "Receita Agropecuária", "15": "Receita Industrial", "16": "Receita de Serviços",
    "17": "Transferências Correntes", "19": "Outras Receitas Correntes", "21": "Operações de Crédito",
    "22": "Alienação de Bens", "23": "Amortização de Empréstimos", "24": "Transferências de Capital",
    "29": "Outras Receitas de Capital", "72": "Contribuições (intra)", "73": "Receita Patrimonial (intra)",
    "76": "Receita de Serviços (intra)", "79": "Outras Receitas Correntes (intra)", "89": "Outras Receitas de Capital (intra)",
}

# Níveis da natureza de receita de 8 dígitos (MCASP 2018+: C.O.E.D.DD.D.T)
NIVEIS_RECEITA = {
    "Categoria econômica": 1, "Origem": 2, "Espécie": 3, "Desdobramento (1)": 4,
    "Desdobramento (2)": 6, "Desdobramento (3)": 7, "Tipo": 8,
}

# Contas da MSC (PCASP) usadas no painel
CONTAS_MSC = {
    "621100000": "Receita a realizar",
    "621200000": "Receita realizada (bruta)",
    "621310100": "(–) Dedução para o FUNDEB",
    "621310200": "(–) Transferências constitucionais a municípios",
    "621320000": "(–) Renúncia de receita",
    "621390000": "(–) Outras deduções",
    "622110000": "Crédito disponível",
    "622130100": "Empenhada a liquidar",
    "622130200": "Empenhada em liquidação",
    "622130300": "Liquidada a pagar",
    "622130400": "Paga",
    "631100000": "RP não processados a liquidar",
    "631300000": "RP não processados liquidados a pagar",
    "631400000": "RP não processados pagos",
    "632100000": "RP processados a pagar",
    "632200000": "RP processados pagos",
}

# Limites e referências de RCL usados nos gráficos do RGF
LIMITES_PESSOAL_EXECUTIVO = {"Alerta (LRF, art. 59)": 44.10, "Prudencial (LRF, art. 22)": 46.55, "Máximo (LRF, art. 20)": 49.00}
LIMITES_PESSOAL_PODER = {  # limite máximo (% RCL) por poder, LRF art. 20, II
    "E": 49.0, "L": 3.0, "J": 6.0, "M": 2.0, "D": 49.0,
}
NOMES_PODER = {"E": "Executivo", "L": "Legislativo (ALEMS + TCE)", "J": "Judiciário", "M": "Ministério Público", "D": "Defensoria Pública"}

# ---------------------------------------------------------------- glossário de siglas
GLOSSARIO: dict[str, str] = {
    "ALEMS": "Assembleia Legislativa do Estado de Mato Grosso do Sul.",
    "API": "Interface de programação: endereço na internet que devolve dados estruturados (aqui, em JSON) em vez de uma página.",
    "ASPS": "Ações e Serviços Públicos de Saúde. O Estado deve aplicar nelas ao menos 12% da receita de impostos (LC 141/2012).",
    "BCB": "Banco Central do Brasil.",
    "CF": "Constituição Federal de 1988.",
    "CGE-MS": "Controladoria-Geral do Estado de MS, responsável pelo Portal da Transparência.",
    "CIDE": "Contribuição de Intervenção no Domínio Econômico sobre combustíveis; 29% vão aos Estados (CF, art. 159, III).",
    "CKAN": "Sistema de catálogo usado pelo portal de dados abertos de MS (dados.ms.gov.br).",
    "CNPJ / CPF": "Cadastros de pessoa jurídica e de pessoa física na Receita Federal.",
    "CSV": "Arquivo de texto com valores separados por um delimitador (aqui, ponto e vírgula).",
    "DCL": "Dívida Consolidada Líquida: dívida de longo prazo menos disponibilidades e haveres financeiros (LRF, art. 29).",
    "DP": "Defensoria Pública do Estado.",
    "DTP": "Despesa Total com Pessoal, apurada em 12 meses para os limites da LRF (arts. 18 a 20).",
    "FECOMP": "Fundo Estadual de Combate e Erradicação da Pobreza, financiado por adicional de ICMS.",
    "FNDE": "Fundo Nacional de Desenvolvimento da Educação (transferências da União para educação).",
    "FPE": "Fundo de Participação dos Estados: parcela do IR e do IPI da União repartida entre os Estados (CF, art. 159, I).",
    "FUNDEB": "Fundo de Manutenção e Desenvolvimento da Educação Básica: 20% de ICMS, IPVA, ITCD, FPE e IPI-Exportação vão a ele (CF, art. 212-A).",
    "FUNDERSUL": "Fundo de Desenvolvimento do Sistema Rodoviário de MS.",
    "HHI": "Índice Herfindahl-Hirschman: soma dos quadrados das participações; mede a concentração entre credores.",
    "IBGE": "Instituto Brasileiro de Geografia e Estatística, que calcula o IPCA.",
    "ICMS": "Imposto sobre Circulação de Mercadorias e Serviços, principal tributo estadual (CF, art. 155, II).",
    "IPCA": "Índice Nacional de Preços ao Consumidor Amplo, usado para corrigir valores pela inflação.",
    "IPI-Exportação": "Parcela do IPI repassada aos Estados exportadores (CF, art. 159, II).",
    "IPVA": "Imposto sobre a Propriedade de Veículos Automotores (CF, art. 155, III).",
    "IRRF": "Imposto de Renda Retido na Fonte sobre pagamentos do Estado; pertence ao Estado (CF, art. 157, I).",
    "ITCD": "Imposto sobre Transmissão Causa Mortis e Doação (CF, art. 155, I).",
    "JSON": "Formato de texto estruturado devolvido pelas APIs.",
    "LC": "Lei Complementar.",
    "LOA": "Lei Orçamentária Anual, que fixa a despesa e prevê a receita do exercício.",
    "LRF": "Lei de Responsabilidade Fiscal (Lei Complementar nº 101/2000).",
    "MCASP": "Manual de Contabilidade Aplicada ao Setor Público, editado pela STN; define as classificações da receita e da despesa.",
    "MDE": "Manutenção e Desenvolvimento do Ensino. O Estado deve aplicar nela ao menos 25% da receita de impostos (CF, art. 212).",
    "MP": "Ministério Público do Estado.",
    "MS": "Mato Grosso do Sul.",
    "MSC": "Matriz de Saldos Contábeis: arquivo mensal que o Estado envia ao Siconfi com os saldos e movimentos de todas as "
           "contas contábeis, detalhados por natureza, função, fonte de recursos e Poder. A classe 6 traz a execução do orçamento.",
    "MSCC": "Tipo de MSC agregada mensal, usado nas consultas à API do Siconfi.",
    "PCASP": "Plano de Contas Aplicado ao Setor Público, definido pela STN; as contas da MSC seguem esse plano.",
    "PCO": "Procedimentos Contábeis Orçamentários: Parte I do MCASP (receita e despesa orçamentárias).",
    "PF / PJ": "Pessoa física / pessoa jurídica.",
    "p.p.": "Pontos percentuais: diferença entre dois percentuais.",
    "RCL": "Receita Corrente Líquida: receitas correntes menos as deduções da LRF (art. 2º, IV); base dos limites fiscais.",
    "RGF": "Relatório de Gestão Fiscal: publicado a cada quadrimestre por Poder; verifica os limites de pessoal, dívida, garantias e crédito (LRF, arts. 54 e 55).",
    "RP": "Restos a pagar: despesas empenhadas e não pagas até 31 de dezembro (Lei 4.320/1964, art. 36).",
    "RPPS": "Regime Próprio de Previdência Social dos servidores estaduais.",
    "RREO": "Relatório Resumido da Execução Orçamentária: publicado a cada bimestre pelo Estado (LRF, arts. 52 e 53).",
    "SEFAZ-MS": "Secretaria de Estado de Fazenda de MS.",
    "SGS": "Sistema Gerenciador de Séries Temporais do Banco Central.",
    "Siconfi": "Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro, mantido pela STN; recebe a MSC, o RREO e o RGF.",
    "STN": "Secretaria do Tesouro Nacional.",
    "SUS": "Sistema Único de Saúde (transferências fundo a fundo da União para saúde).",
    "TCE": "Tribunal de Contas do Estado.",
    "TJ": "Tribunal de Justiça do Estado.",
    "UG": "Unidade Gestora: órgão ou fundo que executa o orçamento.",
}
