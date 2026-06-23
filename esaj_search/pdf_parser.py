"""
Parse the calculation PDF (Cálculo de Falência) to extract execution numbers and CDAs.

Uses PyMuPDF block positions to correctly associate each CDA with its CNPJ group,
even when the PDF has multiple groups on the same page.
"""

import re
import fitz  # PyMuPDF
from typing import List, Optional, Tuple, Dict
from models import CDA, CNPJGroup, CalculationReport


_CNPJ_RE = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
_EXEC_RE  = re.compile(r'\d{7}-\d{2}\.\d{4}\.8\.26\.\d{4}')
_CDA_10   = re.compile(r'\b(\d{10})\b')
_BRL_VAL  = re.compile(r'R\$\s*([\d.]+,\d{2})')
_DATE_RE  = re.compile(r'\d{2}/\d{2}/\d{4}')


def _brl(s: str) -> float:
    m = _BRL_VAL.search(s)
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0


def _all_brl(s: str) -> List[float]:
    return [float(v.replace('.', '').replace(',', '.'))
            for v in _BRL_VAL.findall(s)]


def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s or '').strip()


def parse_calculation_pdf(pdf_path: str) -> CalculationReport:
    """Parse the calculation PDF and return a structured CalculationReport."""
    doc = fitz.open(pdf_path)

    company = ""
    data_fal = ""
    data_base = ""
    all_groups: List[CNPJGroup] = []

    for page in doc:
        groups = _parse_page(page)
        all_groups.extend(groups)

    doc.close()

    # Extract global metadata from any group
    for g in all_groups:
        if not company:
            company = g.company
        if not data_fal:
            data_fal = g.data_falencia
        if not data_base:
            data_base = g.data_base

    return CalculationReport(
        company=company or "TRANSPORTES PANAZZOLO LTDA",
        data_falencia=data_fal or "13/03/2017",
        data_base=data_base or "26/09/2025",
        cnpj_groups=all_groups,
    )


# ─── Block-based page parser ───────────────────────────────────────────────────

def _parse_page(page) -> List[CNPJGroup]:
    """
    Parse one PDF page into one or more CNPJGroups.

    Strategy:
    1. Extract all blocks with their y-positions.
    2. Find "CNPJ header blocks" (blocks containing CPF / CNPJ).
    3. Each header defines a section that ends where the next header begins.
    4. CDA rows belong to the section whose header is spatially above them.
    """
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, type)

    # Normalise: keep only text blocks and clean text
    text_blocks = []
    for b in blocks:
        x0, y0, x1, y1, text, _, btype = b
        if btype != 0:  # Skip image blocks
            continue
        text_clean = _clean(text.replace('\n', ' '))
        if text_clean:
            text_blocks.append((y0, x0, x1, y1, text_clean))

    # Sort by vertical position (top-to-bottom), tie-break by horizontal (left-to-right)
    text_blocks.sort(key=lambda b: (b[0], b[1]))

    # Find CNPJ header blocks
    # Typical text: "CPF / CNPJ 92.758.457/0001-88"
    # or two consecutive blocks: "CPF / CNPJ" then "92.758.457/0001-88"
    header_blocks: List[Tuple[float, str, str, str]] = []  # (y, cnpj, company, context)

    for i, (y0, x0, x1, y1, text) in enumerate(text_blocks):
        m = _CNPJ_RE.search(text)
        if m and ('CNPJ' in text.upper() or 'CPF' in text.upper()):
            cnpj = m.group(0)
            # Find company name near this block (previous blocks)
            company = ""
            data_fal = ""
            data_base = ""
            for j in range(max(0, i - 10), i + 10):
                if j >= len(text_blocks):
                    break
                _, _, _, _, ctx_text = text_blocks[j]
                if 'EXECUTADA' in ctx_text.upper() or 'TRANSPORTES' in ctx_text.upper():
                    parts = ctx_text.split('EXECUTADA')
                    company = _clean(parts[-1]) if len(parts) > 1 else ctx_text
                    # Strip "TRANSPORTES PANAZZOLO LTDA" from "EXECUTADA TRANSPORTES..."
                    company = re.sub(r'^EXECUTADA\s*', '', company, flags=re.I).strip()
                if not company and re.search(r'LTDA|S\.A\.|EIRELI', ctx_text, re.I):
                    company = ctx_text
                if 'DATA DA FAL' in ctx_text.upper():
                    dm = _DATE_RE.search(ctx_text)
                    if dm:
                        data_fal = dm.group(0)
                if 'DATA BASE' in ctx_text.upper() or 'DATA-BASE' in ctx_text.upper():
                    dm = _DATE_RE.search(ctx_text)
                    if dm:
                        data_base = dm.group(0)
            header_blocks.append((y0, cnpj, company, data_fal, data_base))

    if not header_blocks:
        return []

    # Sort header blocks by y0 (should already be sorted but ensure)
    header_blocks.sort(key=lambda h: h[0])

    # Build y-range for each header: from its y to the next header's y
    sections = []
    for i, (h_y, cnpj, company, data_fal, data_base) in enumerate(header_blocks):
        next_y = header_blocks[i + 1][0] if i + 1 < len(header_blocks) else float('inf')
        sections.append({
            'cnpj': cnpj,
            'company': company,
            'data_fal': data_fal,
            'data_base': data_base,
            'y_start': 0,     # CDAs can be above the header on this layout
            'y_header': h_y,
            'y_end': next_y,
        })

    # For each CDA row block, find which section owns it based on its y-position.
    # The tricky part: the CDA data tables appear ABOVE the CNPJ header on the same page.
    # We assign each CDA to the section whose header is CLOSEST (below or above).
    # Observation: header y=90 → owns CDAs around y=172-238 (below it)
    #              header y=263 → owns CDAs around y=382-497 (below it)
    # So: assign CDA at y to the section whose header is the HIGHEST y STILL ≤ CDA y.
    # If no header is ≤ CDA y, use the first header.

    cda_blocks = []  # (y, text) blocks that contain CDA data
    for (y0, x0, x1, y1, text) in text_blocks:
        if _CDA_10.search(text):
            cda_blocks.append((y0, x0, text))

    # Assign each CDA block to a section
    def assign_section(cda_y: float) -> int:
        # Find the section whose header y <= cda_y (nearest header above the CDA)
        best = 0
        for i, s in enumerate(sections):
            if s['y_header'] <= cda_y:
                best = i
        return best

    # Group CDA blocks per section
    section_cda_blocks: Dict[int, List[str]] = {i: [] for i in range(len(sections))}
    for (y0, x0, text) in cda_blocks:
        sec_idx = assign_section(y0)
        section_cda_blocks[sec_idx].append(text)

    # Parse CDAs for each section
    groups: List[CNPJGroup] = []
    for i, s in enumerate(sections):
        raw_lines = section_cda_blocks[i]
        cdas = _parse_cda_blocks(raw_lines)
        if cdas or s['cnpj']:
            groups.append(CNPJGroup(
                cnpj=s['cnpj'],
                company=s['company'] or "TRANSPORTES PANAZZOLO LTDA",
                data_falencia=s['data_fal'] or "13/03/2017",
                data_base=s['data_base'] or "26/09/2025",
                cdas=cdas,
            ))

    return groups


def _parse_cda_blocks(raw_lines: List[str]) -> List[CDA]:
    """
    Each raw_line is a cleaned block text containing:
      CDANUM R$correcao R$juros R$multa R$jurosM R$honAdm R$verba R$total TIPO [EXEC]
    """
    cdas: List[CDA] = []
    for text in raw_lines:
        m = _CDA_10.search(text)
        if not m:
            continue
        cda_num = m.group(1)

        amounts = _all_brl(text)
        while len(amounts) < 7:
            amounts.append(0.0)

        exec_m = _EXEC_RE.search(text)
        exec_num = exec_m.group(0) if exec_m else None

        tipo = _extract_tipo(text)

        cdas.append(CDA(
            number=cda_num,
            principal=0.0,
            correcao=amounts[0] if amounts else 0.0,
            juros_principal=amounts[1] if len(amounts) > 1 else 0.0,
            multa=amounts[2] if len(amounts) > 2 else 0.0,
            juros_multa=amounts[3] if len(amounts) > 3 else 0.0,
            honorarios_adm=amounts[4] if len(amounts) > 4 else 0.0,
            verba_honoraria=amounts[5] if len(amounts) > 5 else 0.0,
            valor_total=amounts[6] if len(amounts) > 6 else sum(amounts),
            situacao="Inscrito",
            tipo_debito=tipo,
            execucao_fiscal=exec_num,
        ))
    return cdas


def _extract_tipo(text: str) -> str:
    lower = text.lower()
    if 'icms declarado' in lower:
        return 'ICMS Declarado'
    if 'icms autuação' in lower or 'icms autuacao' in lower:
        return 'ICMS Autuação'
    if 'taxa judiciária' in lower or 'taxa judiciaria' in lower:
        return 'Taxa Judiciária'
    if 'ipva' in lower:
        return 'IPVA'
    if 'itcmd' in lower:
        return 'ITCMD'
    # Fallback: last word-group before execution number or end
    m = re.search(r'(ICMS\s+\w+|Taxa\s+\w+)', text, re.I)
    return m.group(0) if m else 'ICMS'
