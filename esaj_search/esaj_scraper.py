"""Scrape ESAJ TJSP for process information."""

import re
import time
import requests
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup

from models import ESAJProcessInfo, ProcessEvent


CPOPG_BASE = "https://esaj.tjsp.jus.br/cpopg"

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def _extract_foro(process_number: str) -> str:
    """Extract the foro code from the unified process number NNNNNNN-DD.AAAA.8.26.OOOO."""
    m = re.search(r'\.8\.26\.(\d+)$', process_number)
    if m:
        return str(int(m.group(1)))
    return ""


def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '')).strip()


class ESAJScraper:
    def __init__(self, delay: float = 2.5):
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)
        self.delay = delay
        self._initialized = False

    def _init_session(self) -> bool:
        """Load main CPOPG page to establish a session."""
        if self._initialized:
            return True
        try:
            resp = self.session.get(f"{CPOPG_BASE}/open.do", timeout=30)
            resp.raise_for_status()
            self._initialized = True
            return True
        except Exception as e:
            print(f"  [ESAJ] Não foi possível iniciar sessão: {e}")
            return False

    def query(self, process_number: str) -> ESAJProcessInfo:
        """Query ESAJ TJSP for a single process. Returns ESAJProcessInfo."""
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        foro = _extract_foro(process_number)

        if not foro:
            return ESAJProcessInfo(
                process_number=process_number,
                error=f"Foro não identificado no número do processo: {process_number}",
                status="Erro",
                query_date=now,
                source="esaj",
            )

        self._init_session()
        time.sleep(self.delay)

        url = f"{CPOPG_BASE}/show.do"
        params = {
            'processo.codigo': '',
            'processo.foro': foro,
            'processo.numero': process_number,
            'uuidCaptcha': '',
        }

        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            return ESAJProcessInfo(
                process_number=process_number,
                error=f"Sem acesso à internet ou ESAJ bloqueado neste ambiente. Execute localmente. ({e})",
                status="Sem Conexão",
                query_date=now,
                source="esaj",
            )
        except requests.exceptions.RequestException as e:
            return ESAJProcessInfo(
                process_number=process_number,
                error=f"Erro HTTP: {e}",
                status="Erro na Consulta",
                query_date=now,
                source="esaj",
            )

        # Check for CAPTCHA
        if 'captcha' in resp.url.lower() or (
            'captcha' in resp.text.lower() and 'Identificação de usuário' in resp.text
        ):
            return ESAJProcessInfo(
                process_number=process_number,
                error="CAPTCHA detectado. Consulte manualmente em esaj.tjsp.jus.br/cpopg",
                status="CAPTCHA",
                query_date=now,
                source="esaj",
            )

        # Check for "not found" response
        if 'Processo não encontrado' in resp.text or 'não localizado' in resp.text.lower():
            return ESAJProcessInfo(
                process_number=process_number,
                status="Não Localizado",
                query_date=now,
                source="esaj",
            )

        return _parse_cpopg_page(resp.text, process_number, now)


def _parse_cpopg_page(html: str, process_number: str, query_date: str) -> ESAJProcessInfo:
    """Parse the ESAJ CPOPG HTML page and extract process information."""
    soup = BeautifulSoup(html, 'lxml')

    def txt(selector: str, attr: str = None) -> str:
        el = soup.find(attrs={'id': selector}) or soup.select_one(selector)
        if not el:
            return ""
        return _clean(el.get(attr, '') if attr else el.get_text())

    classe = txt('classeProcesso')
    assunto = txt('assuntoProcesso')
    distribuicao = txt('dataHoraDistribuicaoProcesso')
    juiz = txt('juizProcesso')
    valor_acao = txt('valorAcaoProcesso')

    # Situação / Status
    status_raw = ""
    situacao_el = soup.find(id='situacaoProcesso')
    if situacao_el:
        status_raw = _clean(situacao_el.get_text())
    if not status_raw:
        # Some versions embed status in a different element
        for label_el in soup.find_all(class_='nomeLabel'):
            if 'situaç' in label_el.get_text().lower():
                nxt = label_el.find_next_sibling()
                if nxt:
                    status_raw = _clean(nxt.get_text())
                break

    # Parties
    parties: List[str] = []
    party_table = soup.find(id='tableTodasPartes') or soup.find(id='tablePartesPrincipais')
    if party_table:
        for row in party_table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                role = _clean(cells[0].get_text())
                name = _clean(cells[1].get_text())
                if role and name:
                    parties.append(f"{role}: {name}")

    # Events (andamentos)
    events: List[ProcessEvent] = []
    tbody = (
        soup.find(id='tabelaTodasMovimentacoes') or
        soup.find(id='tabelaUltimasMovimentacoes') or
        soup.find('tbody', id=re.compile(r'tabela.*ovimenta', re.I))
    )
    if tbody:
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                date_cell = _clean(cells[0].get_text())
                # Description is usually in cells[2] (cells[1] is usually blank)
                desc_cell = _clean(cells[-1].get_text()) if len(cells) >= 3 else _clean(cells[1].get_text())
                if date_cell and re.match(r'\d{2}/\d{2}/\d{4}', date_cell):
                    events.append(ProcessEvent(date=date_cell, description=desc_cell))

    # Determine status
    if not status_raw:
        # Infer from events
        if events:
            top_events = [e.description.lower() for e in events[:10]]
            if any('suspen' in d for d in top_events):
                status_raw = "Suspenso"
            elif any('extint' in d or 'arquiv' in d for d in top_events):
                status_raw = "Extinto/Arquivado"
            else:
                status_raw = "Em Andamento"
        else:
            status_raw = "Consultado"

    return ESAJProcessInfo(
        process_number=process_number,
        status=status_raw,
        classe=classe or "Execução Fiscal",
        assunto=assunto,
        distribuicao=distribuicao,
        juiz=juiz,
        valor_acao=valor_acao,
        parties=parties,
        events=events,
        query_date=query_date,
        source="esaj",
    )
