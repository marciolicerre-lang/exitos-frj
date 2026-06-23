"""
Demo/mock data for testing the report generator without live ESAJ access.
Based on realistic outcomes for fiscal executions of TRANSPORTES PANAZZOLO LTDA
(CNPJ 92.758.457/0001-88), declared bankrupt on 13/03/2017.

Under Art. 6°, caput, of Lei 11.101/2005, the declaration of bankruptcy
suspends all enforcement actions against the debtor.
"""

from datetime import datetime
from models import (
    CDA, CNPJGroup, CalculationReport, ESAJProcessInfo, ProcessEvent
)

TODAY = datetime.now().strftime('%d/%m/%Y')
QUERY_DT = datetime.now().strftime('%d/%m/%Y %H:%M')


def get_demo_calculation() -> CalculationReport:
    """Return the Panazzolo calculation data extracted from the PDF."""
    group1 = CNPJGroup(
        cnpj="92.758.457/0024-74",
        company="TRANSPORTES PANAZZOLO LTDA",
        data_falencia="13/03/2017",
        data_base="26/09/2025",
        cdas=[
            CDA(
                number="1344687779",
                principal=225.06,
                correcao=88.99,
                juros_principal=0.0,
                multa=0.0,
                juros_multa=0.0,
                honorarios_adm=31.41,
                verba_honoraria=0.0,
                valor_total=345.46,
                situacao="Inscrito",
                tipo_debito="Taxa Judiciária",
                execucao_fiscal=None,
            ),
        ],
    )

    group2 = CNPJGroup(
        cnpj="92.758.457/0001-88",
        company="TRANSPORTES PANAZZOLO LTDA",
        data_falencia="13/03/2017",
        data_base="26/09/2025",
        cdas=[
            CDA(
                number="1064249383",
                principal=4703.07,
                correcao=0.0,
                juros_principal=2814.79,
                multa=940.61,
                juros_multa=0.0,
                honorarios_adm=0.0,
                verba_honoraria=845.85,
                valor_total=9304.32,
                situacao="Inscrito",
                tipo_debito="ICMS Declarado",
                execucao_fiscal="0203254-38.2012.8.26.0014",
            ),
            CDA(
                number="1064344985",
                principal=1013971.45,
                correcao=0.0,
                juros_principal=1822960.27,
                multa=1013971.45,
                juros_multa=1700125.93,
                honorarios_adm=0.0,
                verba_honoraria=555102.91,
                valor_total=6106132.01,
                situacao="Inscrito",
                tipo_debito="ICMS Autuação",
                execucao_fiscal="0204637-51.2012.8.26.0014",
            ),
            CDA(
                number="1064507251",
                principal=7127.21,
                correcao=0.0,
                juros_principal=4122.38,
                multa=1425.44,
                juros_multa=0.0,
                honorarios_adm=0.0,
                verba_honoraria=1267.50,
                valor_total=13942.53,
                situacao="Inscrito",
                tipo_debito="ICMS Declarado",
                execucao_fiscal="0203254-38.2012.8.26.0014",
            ),
            CDA(
                number="1064670952",
                principal=1046146.30,
                correcao=0.0,
                juros_principal=1741917.87,
                multa=1146680.95,
                juros_multa=1665668.75,
                honorarios_adm=0.0,
                verba_honoraria=560041.39,
                valor_total=6160455.26,
                situacao="Inscrito",
                tipo_debito="ICMS Autuação",
                execucao_fiscal="0204120-46.2012.8.26.0014",
            ),
            CDA(
                number="1064783600",
                principal=8091.60,
                correcao=0.0,
                juros_principal=4608.98,
                multa=1618.32,
                juros_multa=0.0,
                honorarios_adm=0.0,
                verba_honoraria=1431.89,
                valor_total=15750.79,
                situacao="Inscrito",
                tipo_debito="ICMS Declarado",
                execucao_fiscal="0203254-38.2012.8.26.0014",
            ),
            CDA(
                number="1095791225",
                principal=1246881.02,
                correcao=0.0,
                juros_principal=1749832.25,
                multa=1611927.20,
                juros_multa=1698165.31,
                honorarios_adm=0.0,
                verba_honoraria=630680.58,
                valor_total=6937486.36,
                situacao="Inscrito",
                tipo_debito="ICMS Autuação",
                execucao_fiscal="1527553-18.2014.8.26.0014",
            ),
            CDA(
                number="1157686842",
                principal=88000.00,
                correcao=0.0,
                juros_principal=99821.00,
                multa=135478.60,
                juros_multa=77940.84,
                honorarios_adm=0.0,
                verba_honoraria=40124.04,
                valor_total=441364.48,
                situacao="Inscrito",
                tipo_debito="ICMS Autuação",
                execucao_fiscal="1585001-46.2014.8.26.0014",
            ),
        ],
    )

    group3 = CNPJGroup(
        cnpj="92.758.457/0011-50",
        company="TRANSPORTES PANAZZOLO LTDA",
        data_falencia="13/03/2017",
        data_base="26/09/2025",
        cdas=[
            CDA(
                number="1006712360",
                principal=71000.00,
                correcao=0.0,
                juros_principal=121508.30,
                multa=71000.00,
                juros_multa=116205.70,
                honorarios_adm=0.0,
                verba_honoraria=37971.40,
                valor_total=417685.40,
                situacao="Inscrito",
                tipo_debito="ICMS Autuação",
                execucao_fiscal="0002915-05.2011.8.26.0562",
            ),
        ],
    )

    return CalculationReport(
        company="TRANSPORTES PANAZZOLO LTDA",
        data_falencia="13/03/2017",
        data_base="26/09/2025",
        cnpj_groups=[group1, group2, group3],
    )


def get_demo_esaj_results() -> dict[str, ESAJProcessInfo]:
    """
    Return realistic simulated ESAJ data for the Panazzolo fiscal executions.

    Context: Panazzolo was declared bankrupt on 13/03/2017. Under Art. 6°
    (caput and §7-A added by Lei 14.112/2020) of Lei 11.101/2005, execution
    proceedings against the bankrupt debtor should be suspended. The PGE/SP
    (Fazenda Estadual) is the creditor in all listed executions.
    """
    results: dict[str, ESAJProcessInfo] = {}

    # 1 — 0203254-38.2012.8.26.0014 (3 CDAs — ICMS Declarado)
    results["0203254-38.2012.8.26.0014"] = ESAJProcessInfo(
        process_number="0203254-38.2012.8.26.0014",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS",
        distribuicao="25/09/2012 – Livre",
        juiz="MM. Juízo da 1ª Vara de Execuções Fiscais Estaduais e Municipais do Foro Regional XIV – Vila Prudente",
        valor_acao="R$ 39.593,38",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0001-88",
        ],
        events=[
            ProcessEvent("14/03/2025", "Juntada de Petição – Requerimento de habilitação na falência; requer suspensão das execuções nos termos do Art. 187 CTN c/c Art. 6° Lei 11.101/2005"),
            ProcessEvent("22/08/2024", "Decisão – Determina suspensão do feito em razão do decreto de falência (Proc. 1007543-02.2017.8.26.0562 – TJSP). Aguarde manifestação da massa."),
            ProcessEvent("10/03/2024", "Juntada de Ofício – Comunicação do Juízo da Falência informando decreto de quebra em 13/03/2017"),
            ProcessEvent("05/12/2023", "Certidão – Certifico que os autos aguardam cumprimento de decisão"),
            ProcessEvent("18/07/2023", "Juntada de Petição – PGE/SP requer prosseguimento ou habilitação do crédito na falência"),
            ProcessEvent("30/01/2023", "Despacho – Aguarde manifestação da Fazenda acerca da opção: prosseguimento ou habilitação"),
            ProcessEvent("15/06/2022", "Juntada de Petição – Informação sobre situação falimentar da executada"),
            ProcessEvent("10/03/2022", "Certidão – Processo aguarda retorno de ofício ao Juízo Falimentar"),
            ProcessEvent("22/09/2021", "Decisão – Processo suspenso nos termos do art. 6° da Lei 11.101/2005; oficie-se ao administrador judicial"),
            ProcessEvent("14/04/2021", "Juntada de Ofício – AJ informa habilitação de crédito em trâmite"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    # 2 — 0204637-51.2012.8.26.0014 (1 CDA — ICMS Autuação R$ 6,1 M)
    results["0204637-51.2012.8.26.0014"] = ESAJProcessInfo(
        process_number="0204637-51.2012.8.26.0014",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS (Auto de Infração)",
        distribuicao="03/10/2012 – Livre",
        juiz="MM. Juízo da 1ª Vara de Execuções Fiscais Estaduais e Municipais do Foro Regional XIV – Vila Prudente",
        valor_acao="R$ 6.106.132,01",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0001-88",
        ],
        events=[
            ProcessEvent("20/03/2025", "Certidão – Processo suspenso; aguarda resolução do incidente no juízo falimentar"),
            ProcessEvent("11/11/2024", "Decisão – Mantém suspensão em face do decreto de falência da executada (Lei 11.101/2005, Art. 6°)"),
            ProcessEvent("05/05/2024", "Juntada de Petição – PGE/SP apresenta planilha atualizada do débito para habilitação na falência"),
            ProcessEvent("14/08/2023", "Despacho – Certifique-se acerca do andamento da falência; após, concluso"),
            ProcessEvent("25/01/2023", "Certidão – Expedido ofício ao Juízo Falimentar; aguarda retorno"),
            ProcessEvent("08/09/2022", "Decisão – Processo suspenso nos termos do art. 6° da Lei 11.101/2005"),
            ProcessEvent("30/04/2022", "Juntada de Ofício – Resposta do Juízo Falimentar informando prosseguimento da massa"),
            ProcessEvent("17/12/2021", "Juntada de Petição – Requerimento de suspensão pela executada (massa falida)"),
            ProcessEvent("10/06/2021", "Certidão – Penhora sobre veículo não localizado; oficial de justiça sem êxito"),
            ProcessEvent("22/03/2021", "Mandado – Cumprido sem êxito; bens não localizados"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    # 3 — 0204120-46.2012.8.26.0014 (1 CDA — ICMS Autuação R$ 6,1 M)
    results["0204120-46.2012.8.26.0014"] = ESAJProcessInfo(
        process_number="0204120-46.2012.8.26.0014",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS (Auto de Infração)",
        distribuicao="28/09/2012 – Livre",
        juiz="MM. Juízo da 2ª Vara de Execuções Fiscais Estaduais e Municipais do Foro Regional XIV – Vila Prudente",
        valor_acao="R$ 6.160.455,26",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0001-88",
        ],
        events=[
            ProcessEvent("09/04/2025", "Despacho – Processo permanece suspenso; aguarda informes do Administrador Judicial"),
            ProcessEvent("03/12/2024", "Juntada de Petição – PGE/SP informa valores atualizados e requer prosseguimento ou habilitação"),
            ProcessEvent("18/06/2024", "Decisão – Suspensão mantida com fundamento no art. 6°, caput, da Lei 11.101/2005"),
            ProcessEvent("22/01/2024", "Certidão – Aguarda certidão de objeto e pé do processo falimentar"),
            ProcessEvent("11/07/2023", "Juntada de Ofício – Comunicado do Juízo da Falência sobre arrecadação de ativos"),
            ProcessEvent("14/02/2023", "Decisão – Determina suspensão do feito; oficie-se à massa falida e ao AJ"),
            ProcessEvent("08/10/2022", "Juntada de Petição – Requerimento da massa falida para suspensão total das execuções"),
            ProcessEvent("30/05/2022", "Certidão – Oficial sem êxito na localização de bens da executada"),
            ProcessEvent("12/01/2022", "Mandado – Cumprimento de citação com hora certa"),
            ProcessEvent("25/08/2021", "Juntada de Petição – PGE/SP apresenta memória de cálculo atualizada"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    # 4 — 1527553-18.2014.8.26.0014 (1 CDA — ICMS Autuação R$ 6,9 M)
    results["1527553-18.2014.8.26.0014"] = ESAJProcessInfo(
        process_number="1527553-18.2014.8.26.0014",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS (Auto de Infração)",
        distribuicao="15/07/2014 – Livre",
        juiz="MM. Juízo da 1ª Vara de Execuções Fiscais Estaduais e Municipais do Foro Regional XIV – Vila Prudente",
        valor_acao="R$ 6.937.486,36",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0001-88",
        ],
        events=[
            ProcessEvent("25/03/2025", "Certidão – Processo suspenso aguardando definição da falência"),
            ProcessEvent("08/10/2024", "Despacho – Reitere-se ofício ao Administrador Judicial sobre status do crédito habilitado"),
            ProcessEvent("28/05/2024", "Juntada de Petição – PGE/SP junta planilha atualizada (base 26/09/2025)"),
            ProcessEvent("14/11/2023", "Decisão – Processo suspenso; prosseguirá tão logo haja deliberação no juízo falimentar"),
            ProcessEvent("02/05/2023", "Juntada de Ofício – Resposta do AJ informando habilitação em análise pela administradora"),
            ProcessEvent("19/10/2022", "Decisão – Determina suspensão com base no art. 6° Lei 11.101/2005"),
            ProcessEvent("14/04/2022", "Juntada de Petição – Pedido de habilitação formulado pela Fazenda do Estado"),
            ProcessEvent("21/12/2021", "Certidão – Penhora sobre imóvel levantada por decisão judicial"),
            ProcessEvent("09/08/2021", "Mandado – Penhora realizada sobre imóvel avaliado em R$ 980.000,00"),
            ProcessEvent("17/03/2021", "Juntada de Petição – PGE/SP requer constrição de bens"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    # 5 — 1585001-46.2014.8.26.0014 (1 CDA — ICMS Autuação R$ 441 K)
    results["1585001-46.2014.8.26.0014"] = ESAJProcessInfo(
        process_number="1585001-46.2014.8.26.0014",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS (Auto de Infração)",
        distribuicao="19/08/2014 – Livre",
        juiz="MM. Juízo da 2ª Vara de Execuções Fiscais Estaduais e Municipais do Foro Regional XIV – Vila Prudente",
        valor_acao="R$ 441.364,48",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0001-88",
        ],
        events=[
            ProcessEvent("12/04/2025", "Decisão – Suspensão mantida; os créditos deverão ser habilitados no processo falimentar"),
            ProcessEvent("15/11/2024", "Juntada de Petição – PGE/SP requer informes sobre andamento da massa"),
            ProcessEvent("22/06/2024", "Certidão – Aguarda retorno do ofício expedido ao Juízo Falimentar"),
            ProcessEvent("10/01/2024", "Despacho – Reitere-se ofício; certificado o decurso de prazo"),
            ProcessEvent("05/07/2023", "Juntada de Ofício – Juízo Falimentar informa arrecadação em andamento"),
            ProcessEvent("20/02/2023", "Decisão – Suspender o feito com base no art. 6° da Lei 11.101/2005"),
            ProcessEvent("11/08/2022", "Juntada de Petição – Pedido de tutela de urgência para bloqueio de contas"),
            ProcessEvent("14/03/2022", "Despacho – Indefere tutela; executada já declarada falida"),
            ProcessEvent("09/11/2021", "Certidão – Expedido BACENJUD sem sucesso; contas zeradas"),
            ProcessEvent("28/04/2021", "Juntada de Petição – PGE/SP requer pesquisa BACENJUD/RENAJUD"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    # 6 — 0002915-05.2011.8.26.0562 (1 CDA — ICMS Autuação R$ 417 K — Foro Santos)
    results["0002915-05.2011.8.26.0562"] = ESAJProcessInfo(
        process_number="0002915-05.2011.8.26.0562",
        status="Suspenso",
        classe="Execução Fiscal",
        assunto="Dívida Ativa Estadual – ICMS (Auto de Infração)",
        distribuicao="10/01/2011 – Livre",
        juiz="MM. Juízo da Vara de Execuções Fiscais Estaduais da Comarca de Santos",
        valor_acao="R$ 417.685,40",
        parties=[
            "Exequente: Fazenda do Estado de São Paulo (PGE/SP)",
            "Executada: Transportes Panazzolo Ltda – CNPJ 92.758.457/0011-50",
        ],
        events=[
            ProcessEvent("17/03/2025", "Decisão – Suspensão mantida em razão da falência decretada em 13/03/2017; aguarda habilitação"),
            ProcessEvent("04/11/2024", "Juntada de Petição – PGE/SP junta cálculo atualizado para habilitação na falência"),
            ProcessEvent("19/06/2024", "Certidão – Ofício expedido ao Juízo Falimentar de Santos; sem retorno"),
            ProcessEvent("21/01/2024", "Despacho – Reitera expedição de ofício ao administrador judicial"),
            ProcessEvent("12/07/2023", "Juntada de Ofício – AJ confirma recebimento do crédito fiscal para análise"),
            ProcessEvent("08/03/2023", "Decisão – Processo suspenso com fundamento no art. 6° da Lei 11.101/2005"),
            ProcessEvent("25/10/2022", "Juntada de Petição – Fazenda requer constrição de bens; executada declarada falida"),
            ProcessEvent("30/05/2022", "Mandado – Sem êxito; bens já arrecadados pela massa falida"),
            ProcessEvent("14/01/2022", "Certidão – RENAJUD: nenhum veículo localizado em nome da executada"),
            ProcessEvent("09/08/2021", "Juntada de Petição – PGE/SP noticia falência e requer providências"),
        ],
        query_date=QUERY_DT,
        source="demo",
    )

    return results
