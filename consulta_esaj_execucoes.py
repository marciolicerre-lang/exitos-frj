#!/usr/bin/env python3
"""
Consulta de andamento processual no e-SAJ (TJSP) - Execuções Fiscais
=====================================================================

Objetivo:
    Consultar automaticamente o e-SAJ (1º grau) para uma lista de números
    de processo (execuções fiscais), extrair a movimentação processual e
    sinalizar se há pedido de suspensão do processo e se ele foi
    efetivamente deferido/homologado.

Como usar:
    1. Rode este script dentro do Claude Code (que tem acesso de rede
       irrestrito), na pasta que preferir.
    2. Ajuste a lista PROCESSOS abaixo (ou passe um CSV/JSON externo -
       veja carregar_processos_de_arquivo()).
    3. Execute:  python3 consulta_esaj_execucoes.py
    4. O script gera:
         - esaj_resultados.json  (dados brutos de cada processo)
         - relatorio_suspensao.csv (resumo tabular)
         - Impressão no console com o resumo por processo

Observações importantes:
    - O e-SAJ pode exibir captcha/reCAPTCHA em consultas automatizadas
      repetidas ou em volume. Se isso acontecer, o script vai avisar e
      você pode:
        a) reduzir a frequência (parâmetro DELAY_SEGUNDOS),
        b) rodar em lotes menores,
        c) consultar manualmente os processos que falharem.
    - A estrutura HTML do e-SAJ pode mudar. Os seletores usados aqui
      (classe CSS, ids) refletem o layout do e-SAJ observado em 2025/2026;
      se o site for atualizado, pode ser necessário ajustar as funções
      extrair_movimentacoes() e extrair_partes().
    - Este script NÃO usa login/certificado digital - ele consulta apenas
      o que está disponível na consulta pública do e-SAJ (cpopg). Processos
      em segredo de justiça não estarão acessíveis.
"""

import re
import csv
import json
import time
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

# Lista de execuções fiscais a consultar (número unificado CNJ completo)
PROCESSOS = [
    "1500096-33.2018.8.26.0511",
    "1500011-81.2017.8.26.0511",
    "1501467-03.2016.8.26.0511",
]

DELAY_SEGUNDOS = 3  # intervalo entre consultas, para reduzir risco de bloqueio/captcha

BASE_URL = "https://esaj.tjsp.jus.br"
SEARCH_URL = f"{BASE_URL}/cpopg/search.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Palavras-chave usadas para identificar, na movimentação/andamento,
# petições/decisões relacionadas a pedido de suspensão.
PALAVRAS_PEDIDO_SUSPENSAO = [
    "pedido de suspensão",
    "requer a suspensão",
    "requerimento de suspensão",
    "suspensão do feito",
    "suspensão do processo",
    "suspensão da execução",
    "petição de suspensão",
]

PALAVRAS_DEFERIMENTO_SUSPENSAO = [
    "defiro a suspensão",
    "defiro o pedido de suspensão",
    "suspendo o processo",
    "suspendo a execução",
    "determino a suspensão",
    "processo suspenso",
    "fica suspenso",
    "homologo a suspensão",
]

PALAVRAS_INDEFERIMENTO_SUSPENSAO = [
    "indefiro a suspensão",
    "indefiro o pedido de suspensão",
    "indeferido o pedido de suspensão",
]


# ---------------------------------------------------------------------------
# ESTRUTURAS DE DADOS
# ---------------------------------------------------------------------------

@dataclass
class ResultadoProcesso:
    numero_processo: str
    encontrado: bool = False
    erro: Optional[str] = None
    classe: Optional[str] = None
    assunto: Optional[str] = None
    foro: Optional[str] = None
    vara: Optional[str] = None
    valor_acao: Optional[str] = None
    situacao: Optional[str] = None
    partes: list = field(default_factory=list)
    movimentacoes: list = field(default_factory=list)  # lista de dicts {data, descricao}
    tem_pedido_suspensao: bool = False
    tem_deferimento_suspensao: bool = False
    tem_indeferimento_suspensao: bool = False
    trechos_pedido_suspensao: list = field(default_factory=list)
    trechos_decisao_suspensao: list = field(default_factory=list)
    url_consulta: Optional[str] = None


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE PARSE DO NÚMERO DO PROCESSO
# ---------------------------------------------------------------------------

def parse_numero_unificado(numero: str) -> dict:
    """
    Quebra um número CNJ unificado (NNNNNNN-DD.AAAA.J.TR.OOOO) nos
    componentes exigidos pelo formulário de busca do e-SAJ.
    """
    m = re.match(
        r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$",
        numero.strip(),
    )
    if not m:
        raise ValueError(f"Número de processo fora do padrão CNJ: {numero}")

    seq, dv, ano, orgao, tribunal, foro = m.groups()
    return {
        "numero_completo": numero,
        "numeroDigitoAnoUnificado": f"{seq}-{dv}.{ano}",
        "foroNumeroUnificado": foro,
    }


# ---------------------------------------------------------------------------
# CONSULTA HTTP
# ---------------------------------------------------------------------------

def consultar_processo(session: requests.Session, numero: str) -> ResultadoProcesso:
    resultado = ResultadoProcesso(numero_processo=numero)

    try:
        partes_numero = parse_numero_unificado(numero)
    except ValueError as e:
        resultado.erro = str(e)
        return resultado

    params = {
        "conversationId": "",
        "cbPesquisa": "NUMPROC",
        "numeroDigitoAnoUnificado": partes_numero["numeroDigitoAnoUnificado"],
        "foroNumeroUnificado": partes_numero["foroNumeroUnificado"],
        "dadosConsulta.valorConsultaNuUnificado": partes_numero["numero_completo"],
        "dadosConsulta.valorConsulta": "",
        "dadosConsulta.tipoNuProcesso": "UNIFICADO",
    }

    resultado.url_consulta = SEARCH_URL + "?" + requests.compat.urlencode(params)

    try:
        resp = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        resultado.erro = f"Falha de rede/HTTP: {e}"
        return resultado

    html = resp.text

    if "captcha" in html.lower() or "recaptcha" in html.lower():
        resultado.erro = (
            "Consulta bloqueada por CAPTCHA. Reduza a frequência de consultas "
            "(DELAY_SEGUNDOS) ou consulte manualmente este processo."
        )
        return resultado

    soup = BeautifulSoup(html, "html.parser")

    # Se a busca retornar múltiplos resultados (ex.: processo com incidentes
    # vinculados), o e-SAJ mostra uma lista intermediária. Nesse caso,
    # pegamos o primeiro link para a página de detalhes.
    link_detalhe = soup.select_one("a.linkProcesso")
    if link_detalhe and link_detalhe.get("href"):
        href = link_detalhe["href"]
        detalhe_url = href if href.startswith("http") else f"{BASE_URL}/cpopg/{href}"
        try:
            resp2 = session.get(detalhe_url, headers=HEADERS, timeout=30)
            resp2.raise_for_status()
            soup = BeautifulSoup(resp2.text, "html.parser")
            resultado.url_consulta = detalhe_url
        except requests.RequestException as e:
            resultado.erro = f"Falha ao abrir página de detalhe: {e}"
            return resultado

    # Detecta "não encontrado"
    texto_pagina = soup.get_text(" ", strip=True).lower()
    if "não foi encontrado" in texto_pagina or "nenhum processo foi encontrado" in texto_pagina:
        resultado.erro = "Processo não encontrado na consulta pública do e-SAJ."
        return resultado

    resultado.encontrado = True

    extrair_dados_cabecalho(soup, resultado)
    extrair_partes(soup, resultado)
    extrair_movimentacoes(soup, resultado)
    analisar_suspensao(resultado)

    return resultado


def extrair_dados_cabecalho(soup: BeautifulSoup, resultado: ResultadoProcesso) -> None:
    def pegar_texto(id_elemento):
        el = soup.find(id=id_elemento)
        return el.get_text(" ", strip=True) if el else None

    resultado.classe = pegar_texto("classeProcesso")
    resultado.assunto = pegar_texto("assuntoProcesso")
    resultado.foro = pegar_texto("foroProcesso")
    resultado.vara = pegar_texto("varaProcesso")
    resultado.valor_acao = pegar_texto("valorAcaoProcesso")
    resultado.situacao = pegar_texto("situacaoProcesso")


def extrair_partes(soup: BeautifulSoup, resultado: ResultadoProcesso) -> None:
    tabela = soup.find("table", id="tablePartesPrincipais")
    if not tabela:
        return
    for linha in tabela.find_all("tr"):
        celulas = linha.find_all("td")
        if len(celulas) >= 2:
            tipo = celulas[0].get_text(" ", strip=True)
            nome = celulas[1].get_text(" ", strip=True)
            if tipo or nome:
                resultado.partes.append({"tipo": tipo, "nome": nome})


def extrair_movimentacoes(soup: BeautifulSoup, resultado: ResultadoProcesso) -> None:
    # O e-SAJ normalmente usa uma tabela com id "tabelaTodasMovimentacoes"
    # ou "tabelaUltimasMovimentacoes" quando a movimentação completa está
    # colapsada. Tentamos ambas.
    tabela = soup.find(id="tabelaTodasMovimentacoes") or soup.find(
        id="tabelaUltimasMovimentacoes"
    )
    if not tabela:
        return

    for linha in tabela.find_all("tr"):
        celulas = linha.find_all("td")
        if len(celulas) < 2:
            continue
        data = celulas[0].get_text(" ", strip=True)
        descricao = celulas[-1].get_text(" ", strip=True)
        descricao = re.sub(r"\s+", " ", descricao).strip()
        if data or descricao:
            resultado.movimentacoes.append({"data": data, "descricao": descricao})


def analisar_suspensao(resultado: ResultadoProcesso) -> None:
    for mov in resultado.movimentacoes:
        desc_lower = mov["descricao"].lower()

        for termo in PALAVRAS_PEDIDO_SUSPENSAO:
            if termo in desc_lower:
                resultado.tem_pedido_suspensao = True
                resultado.trechos_pedido_suspensao.append(
                    f"[{mov['data']}] {mov['descricao']}"
                )
                break

        for termo in PALAVRAS_DEFERIMENTO_SUSPENSAO:
            if termo in desc_lower:
                resultado.tem_deferimento_suspensao = True
                resultado.trechos_decisao_suspensao.append(
                    f"[{mov['data']}] {mov['descricao']}"
                )
                break

        for termo in PALAVRAS_INDEFERIMENTO_SUSPENSAO:
            if termo in desc_lower:
                resultado.tem_indeferimento_suspensao = True
                resultado.trechos_decisao_suspensao.append(
                    f"[{mov['data']}] {mov['descricao']}"
                )
                break


# ---------------------------------------------------------------------------
# CARREGAR LISTA DE PROCESSOS DE ARQUIVO EXTERNO (opcional)
# ---------------------------------------------------------------------------

def carregar_processos_de_arquivo(caminho: str) -> list:
    """
    Aceita um .txt (um número de processo por linha) ou .csv com coluna
    'numero_execucao'. Use isso se preferir não editar a lista PROCESSOS
    diretamente no script.
    """
    processos = []
    if caminho.endswith(".csv"):
        with open(caminho, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = row.get("numero_execucao") or row.get("numero_processo")
                if num:
                    processos.append(num.strip())
    else:
        with open(caminho, encoding="utf-8") as f:
            processos = [linha.strip() for linha in f if linha.strip()]
    return processos


# ---------------------------------------------------------------------------
# SAÍDA / RELATÓRIOS
# ---------------------------------------------------------------------------

def imprimir_resumo(resultado: ResultadoProcesso) -> None:
    print("=" * 80)
    print(f"Processo: {resultado.numero_processo}")
    if resultado.erro:
        print(f"  ERRO: {resultado.erro}")
        return

    print(f"  Classe: {resultado.classe}")
    print(f"  Situação: {resultado.situacao}")
    print(f"  Foro/Vara: {resultado.foro} - {resultado.vara}")
    print(f"  Total de movimentações capturadas: {len(resultado.movimentacoes)}")

    if resultado.movimentacoes:
        ultima = resultado.movimentacoes[0]
        print(f"  Última movimentação: [{ultima['data']}] {ultima['descricao'][:150]}")

    print(f"  Pedido de suspensão identificado: {'SIM' if resultado.tem_pedido_suspensao else 'NÃO'}")
    if resultado.trechos_pedido_suspensao:
        for t in resultado.trechos_pedido_suspensao[:3]:
            print(f"      -> {t[:200]}")

    if resultado.tem_deferimento_suspensao:
        print("  Suspensão DEFERIDA/homologada: SIM")
    if resultado.tem_indeferimento_suspensao:
        print("  Suspensão INDEFERIDA: SIM")
    if not resultado.tem_deferimento_suspensao and not resultado.tem_indeferimento_suspensao:
        print("  Decisão sobre suspensão: NÃO IDENTIFICADA (verificar manualmente)")

    for t in resultado.trechos_decisao_suspensao[:3]:
        print(f"      -> {t[:200]}")


def gerar_csv(resultados: list, caminho: str = "relatorio_suspensao.csv") -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "numero_processo",
            "encontrado",
            "erro",
            "situacao",
            "pedido_suspensao",
            "suspensao_deferida",
            "suspensao_indeferida",
            "qtd_movimentacoes",
            "url_consulta",
        ])
        for r in resultados:
            writer.writerow([
                r.numero_processo,
                r.encontrado,
                r.erro or "",
                r.situacao or "",
                "SIM" if r.tem_pedido_suspensao else "NÃO",
                "SIM" if r.tem_deferimento_suspensao else "NÃO",
                "SIM" if r.tem_indeferimento_suspensao else "NÃO",
                len(r.movimentacoes),
                r.url_consulta or "",
            ])


def gerar_json(resultados: list, caminho: str = "esaj_resultados.json") -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in resultados], f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    processos = PROCESSOS

    # Se quiser carregar de arquivo em vez da lista fixa, descomente:
    # processos = carregar_processos_de_arquivo("execucoes.csv")

    session = requests.Session()

    resultados = []
    for i, numero in enumerate(processos, start=1):
        print(f"\nConsultando {i}/{len(processos)}: {numero} ...")
        resultado = consultar_processo(session, numero)
        resultados.append(resultado)
        imprimir_resumo(resultado)

        if i < len(processos):
            time.sleep(DELAY_SEGUNDOS)

    gerar_json(resultados)
    gerar_csv(resultados)

    print("\n" + "=" * 80)
    print("Concluído.")
    print("  - Dados brutos:  esaj_resultados.json")
    print("  - Resumo tabular: relatorio_suspensao.csv")

    pendentes = [r for r in resultados if r.erro]
    if pendentes:
        print(f"\n{len(pendentes)} processo(s) com erro/exigem checagem manual:")
        for r in pendentes:
            print(f"  - {r.numero_processo}: {r.erro}")


if __name__ == "__main__":
    main()
