"""
Generate a professional PDF report for the Judicial Administrator (Administrador Judicial)
summarizing the status of fiscal executions related to a bankruptcy case.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models import CDA, CalculationReport, ESAJProcessInfo

# ── Fonts ──────────────────────────────────────────────────────────────────────
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_SERIF = "DejaVuSerif"
_SERIF_B = "DejaVuSerif-Bold"
_SANS = "DejaVuSans"
_SANS_B = "DejaVuSans-Bold"
_MONO = "DejaVuSansMono"

def _register_fonts():
    fonts = {
        _SERIF: "DejaVuSerif.ttf",
        _SERIF_B: "DejaVuSerif-Bold.ttf",
        _SANS: "DejaVuSans.ttf",
        _SANS_B: "DejaVuSans-Bold.ttf",
        _MONO: "DejaVuSansMono.ttf",
    }
    for name, filename in fonts.items():
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))

_register_fonts()

# ── Colour palette ─────────────────────────────────────────────────────────────
_NAVY       = colors.HexColor("#1B2A4A")
_NAVY_LIGHT = colors.HexColor("#2C4070")
_GOLD       = colors.HexColor("#C9A96E")
_GOLD_LIGHT = colors.HexColor("#E8C98A")
_RED_BADGE  = colors.HexColor("#C0392B")
_GREEN_BADGE= colors.HexColor("#1E8449")
_AMBER      = colors.HexColor("#D35400")
_GRAY_LIGHT = colors.HexColor("#F2F4F8")
_GRAY_MID   = colors.HexColor("#DCE1EA")
_GRAY_DARK  = colors.HexColor("#5D6D7E")
_WHITE      = colors.white
_BLACK      = colors.black
_TABLE_ALT  = colors.HexColor("#EEF1F7")

# Page size
W, H = A4
MARGIN_H = 2.2 * cm
MARGIN_V = 2.5 * cm

# ── Style helpers ──────────────────────────────────────────────────────────────
def _style(name, font=_SERIF, size=10, leading=14, color=_BLACK,
           align=TA_JUSTIFY, space_before=0, space_after=4,
           bold=False, italic=False):
    return ParagraphStyle(
        name=name,
        fontName=_SANS_B if bold else (_SANS if not bold else font),
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        spaceAfter=space_after,
        spaceBefore=space_before,
    )


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _badge_color(badge: str):
    if badge == "SUSPENSO":
        return _AMBER
    if badge == "EXTINTO":
        return _RED_BADGE
    if badge == "ATIVO":
        return _GREEN_BADGE
    return _GRAY_DARK


# ── Canvas callbacks ───────────────────────────────────────────────────────────
class _PageTemplate:
    def __init__(self, company: str, report_date: str):
        self.company = company
        self.date = report_date

    def on_page(self, canv: canvas.Canvas, doc):
        canv.saveState()
        # Header bar
        canv.setFillColor(_NAVY)
        canv.rect(0, H - 18 * mm, W, 18 * mm, fill=1, stroke=0)
        canv.setFillColor(_GOLD)
        canv.setFont(_SANS_B, 8.5)
        canv.drawString(MARGIN_H, H - 11 * mm, "RELATÓRIO DE PESQUISA PROCESSUAL – EXECUÇÕES FISCAIS")
        canv.setFillColor(_GRAY_MID)
        canv.setFont(_SANS, 7)
        canv.drawRightString(W - MARGIN_H, H - 11 * mm, f"{self.company}")

        # Footer line
        canv.setStrokeColor(_NAVY)
        canv.setLineWidth(0.5)
        canv.line(MARGIN_H, 16 * mm, W - MARGIN_H, 16 * mm)
        canv.setFillColor(_NAVY)
        canv.setFont(_SANS, 7)
        canv.drawString(MARGIN_H, 10 * mm, f"Data do relatório: {self.date}")
        canv.drawCentredString(W / 2, 10 * mm, "Confidencial – uso exclusivo do Administrador Judicial")
        canv.drawRightString(W - MARGIN_H, 10 * mm, f"Pág. {doc.page}")
        canv.restoreState()

    def on_first_page(self, canv: canvas.Canvas, doc):
        """Skip header/footer on cover page."""
        pass


# ── Cover page ─────────────────────────────────────────────────────────────────
def _build_cover(canv: canvas.Canvas, calc: CalculationReport, report_date: str):
    canv.saveState()

    # Full navy top band
    canv.setFillColor(_NAVY)
    canv.rect(0, H - 7.5 * cm, W, 7.5 * cm, fill=1, stroke=0)

    # Gold accent line
    canv.setFillColor(_GOLD)
    canv.rect(0, H - 7.5 * cm - 4 * mm, W, 4 * mm, fill=1, stroke=0)

    # Title in band
    canv.setFillColor(_WHITE)
    canv.setFont(_SANS_B, 19)
    canv.drawCentredString(W / 2, H - 3.5 * cm, "RELATÓRIO DE PESQUISA PROCESSUAL")
    canv.setFont(_SANS, 13)
    canv.drawCentredString(W / 2, H - 5.0 * cm, "Execuções Fiscais – Falência")
    canv.setFillColor(_GOLD_LIGHT)
    canv.setFont(_SANS, 10)
    canv.drawCentredString(W / 2, H - 6.3 * cm, "Sistema de Acompanhamento de Execuções Fiscais – SAEF/ESAJ TJSP")

    # Box with case info
    box_top = H - 9.5 * cm
    box_h = 6.5 * cm
    canv.setFillColor(_GRAY_LIGHT)
    canv.roundRect(MARGIN_H, box_top - box_h, W - 2 * MARGIN_H, box_h, 6, fill=1, stroke=0)

    canv.setFillColor(_NAVY)
    canv.setFont(_SANS_B, 10)
    canv.drawString(MARGIN_H + 0.5 * cm, box_top - 0.9 * cm, "EMPRESA EXECUTADA")
    canv.setFont(_SANS_B, 14)
    canv.drawString(MARGIN_H + 0.5 * cm, box_top - 1.8 * cm, calc.company)

    canv.setFillColor(_GRAY_DARK)
    canv.setFont(_SANS, 9)
    cnpjs = " | ".join(calc.all_cnpjs)
    canv.drawString(MARGIN_H + 0.5 * cm, box_top - 2.5 * cm, f"CNPJs: {cnpjs}")

    # Data points
    y = box_top - 3.5 * cm
    for label, value in [
        ("Data da Falência:", calc.data_falencia),
        ("Data-Base do Cálculo:", calc.data_base),
        ("Data do Relatório:", report_date),
    ]:
        canv.setFillColor(_NAVY)
        canv.setFont(_SANS_B, 9)
        canv.drawString(MARGIN_H + 0.5 * cm, y, label)
        canv.setFillColor(_GRAY_DARK)
        canv.setFont(_SANS, 9)
        canv.drawString(MARGIN_H + 5.5 * cm, y, value)
        y -= 0.75 * cm

    # Addressee block
    addr_y = 9.5 * cm
    canv.setFillColor(_NAVY)
    canv.setFont(_SANS_B, 9)
    canv.drawString(MARGIN_H, addr_y + 0.8 * cm, "DESTINATÁRIO")
    canv.setFillColor(_BLACK)
    canv.setFont(_SERIF, 10)
    canv.drawString(MARGIN_H, addr_y, "Ao Excelentíssimo Senhor")
    canv.setFont(_SERIF_B, 10)
    canv.drawString(MARGIN_H, addr_y - 0.55 * cm, "Administrador Judicial")
    canv.setFont(_SERIF, 10)
    canv.drawString(MARGIN_H, addr_y - 1.1 * cm, f"da Falência de {calc.company}")

    # Footer
    canv.setFillColor(_GRAY_DARK)
    canv.setFont(_SANS, 8)
    canv.drawCentredString(W / 2, 2.5 * cm,
        "Documento gerado pelo Sistema de Acompanhamento de Execuções Fiscais (SAEF)")
    canv.drawCentredString(W / 2, 1.8 * cm,
        "Dados obtidos via consulta pública ESAJ TJSP – esaj.tjsp.jus.br")

    canv.restoreState()


# ── Story builders ─────────────────────────────────────────────────────────────
def _section_title(text: str) -> List:
    return [
        Spacer(1, 0.4 * cm),
        Table(
            [[Paragraph(text.upper(), ParagraphStyle(
                "secTitle", fontName=_SANS_B, fontSize=10,
                textColor=_WHITE, alignment=TA_LEFT, spaceAfter=0,
            ))]],
            colWidths=[W - 2 * MARGIN_H],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_NAVY]),
            ]),
        ),
        Spacer(1, 0.25 * cm),
    ]


def _para(text: str, font=_SERIF, size=9.5, leading=14, align=TA_JUSTIFY,
          color=_BLACK, bold=False, space_after=4) -> Paragraph:
    style = ParagraphStyle(
        "p",
        fontName=_SANS_B if bold else font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        spaceAfter=space_after,
    )
    return Paragraph(text, style)


def _build_summary_table(
    calc: CalculationReport,
    esaj: Dict[str, ESAJProcessInfo],
) -> List:
    story = _section_title("1. Quadro Resumo das Execuções Fiscais")

    col_w = [5.0 * cm, 2.4 * cm, 2.4 * cm, 3.2 * cm, 3.8 * cm]
    header = [
        Paragraph("<b>Nº Execução Fiscal</b>", ParagraphStyle("h", fontName=_SANS_B, fontSize=8, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Tipo</b>",                ParagraphStyle("h", fontName=_SANS_B, fontSize=8, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>CDAs</b>",                ParagraphStyle("h", fontName=_SANS_B, fontSize=8, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Valor Atualizado</b>",    ParagraphStyle("h", fontName=_SANS_B, fontSize=8, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Status ESAJ</b>",         ParagraphStyle("h", fontName=_SANS_B, fontSize=8, textColor=_WHITE, alignment=TA_CENTER)),
    ]
    rows = [header]

    by_exec = calc.cdas_by_execution
    total_val = 0.0
    total_cdas = 0

    for i, exec_num in enumerate(calc.unique_executions):
        cdas = by_exec.get(exec_num, [])
        info = esaj.get(exec_num)
        val = sum(c.valor_total for c in cdas)
        total_val += val
        total_cdas += len(cdas)

        tipos = list({c.tipo_debito for c in cdas})
        tipo_str = tipos[0] if tipos else "ICMS"

        badge = info.status_badge if info else "NÃO CONSULTADO"
        badge_color = _badge_color(badge)

        bg = _TABLE_ALT if i % 2 else _WHITE

        rows.append([
            Paragraph(f'<font name="{_MONO}" size="8">{exec_num}</font>',
                      ParagraphStyle("m", fontName=_MONO, fontSize=8, alignment=TA_LEFT)),
            Paragraph(tipo_str, ParagraphStyle("t", fontName=_SANS, fontSize=7.5, alignment=TA_CENTER)),
            Paragraph(str(len(cdas)), ParagraphStyle("n", fontName=_SANS_B, fontSize=9, alignment=TA_CENTER)),
            Paragraph(_brl(val), ParagraphStyle("v", fontName=_SANS, fontSize=8, alignment=TA_RIGHT)),
            Paragraph(
                f'<b>{badge}</b>',
                ParagraphStyle("b", fontName=_SANS_B, fontSize=8,
                               textColor=badge_color, alignment=TA_CENTER),
            ),
        ])

    # Total row
    rows.append([
        Paragraph("<b>TOTAL</b>", ParagraphStyle("tot", fontName=_SANS_B, fontSize=8.5, alignment=TA_LEFT, textColor=_WHITE)),
        Paragraph("", ParagraphStyle("x", fontName=_SANS, fontSize=8)),
        Paragraph(f"<b>{total_cdas}</b>", ParagraphStyle("tot", fontName=_SANS_B, fontSize=8.5, alignment=TA_CENTER, textColor=_WHITE)),
        Paragraph(f"<b>{_brl(total_val)}</b>", ParagraphStyle("tot", fontName=_SANS_B, fontSize=8.5, alignment=TA_RIGHT, textColor=_WHITE)),
        Paragraph("", ParagraphStyle("x", fontName=_SANS, fontSize=8)),
    ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  _NAVY),
        ("BACKGROUND",    (0, -1), (-1, -1), _NAVY_LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [_WHITE, _TABLE_ALT]),
        ("GRID",          (0, 0),  (-1, -1), 0.4, _GRAY_MID),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
    ]))

    story.append(tbl)
    story.append(Spacer(1, 0.3 * cm))

    # Note about source
    source_note = "* Dados obtidos via consulta pública ESAJ TJSP em " + (
        next(iter(esaj.values())).query_date if esaj else datetime.now().strftime('%d/%m/%Y')
    )
    if any(v.source == "demo" for v in esaj.values()):
        source_note += " (dados de demonstração – execute localmente para resultados reais)"
    story.append(_para(source_note, font=_SANS, size=7.5, color=_GRAY_DARK, align=TA_LEFT))

    return story


def _build_intro(calc: CalculationReport, esaj: Dict[str, ESAJProcessInfo]) -> List:
    story = _section_title("Introdução")

    n_exec = len(calc.unique_executions)
    n_susp = sum(1 for v in esaj.values() if v.is_suspended)
    n_ext  = sum(1 for v in esaj.values() if v.is_extinct)
    n_ativo = n_exec - n_susp - n_ext

    story.append(_para(
        f"O presente relatório tem por finalidade apresentar ao Administrador Judicial da "
        f"falência de <b>{calc.company}</b> (decretada em {calc.data_falencia}) o status atualizado "
        f"das execuções fiscais identificadas na planilha de cálculo do crédito fiscal, elaborada "
        f"com data-base de {calc.data_base}.",
        font=_SERIF, size=9.5,
    ))
    story.append(_para(
        "As consultas foram realizadas mediante pesquisa no sistema ESAJ TJSP "
        "(esaj.tjsp.jus.br – Consulta de Processos de Primeiro Grau), "
        "com verificação de cada número de execução fiscal constante da planilha de cálculo "
        "apresentada pela Fazenda Pública do Estado de São Paulo.",
        font=_SERIF, size=9.5,
    ))
    story.append(_para(
        f"Foram identificadas <b>{n_exec} execuções fiscais</b> distribuídas entre "
        f"{len(calc.cnpj_groups)} CNPJs da executada, totalizando "
        f"<b>{_brl(calc.valor_total_geral)}</b> em valores atualizados (base {calc.data_base}). "
        f"Resultado da pesquisa: "
        f"<b><font color='#{_AMBER.hexval()[2:]}'>{n_susp} suspenso(s)</font></b>, "
        f"<b><font color='#{_RED_BADGE.hexval()[2:]}'>{n_ext} extinto(s)</font></b>, "
        f"<b><font color='#{_GREEN_BADGE.hexval()[2:]}'>{n_ativo} ativo(s)</font></b>.",
        font=_SERIF, size=9.5,
    ))
    story.append(Spacer(1, 0.2 * cm))
    return story


def _build_legal_framework() -> List:
    story = _section_title("Enquadramento Legal")
    story.append(_para(
        "A Lei n.º 11.101/2005, em seu art. 6.º, <i>caput</i>, estabelece que a decretação "
        "da falência <b>suspende o curso de todas as ações e execuções</b> em face do devedor, "
        "inclusive as de natureza fiscal, ressalvadas as hipóteses dos §§ 1.º a 7.º-A. "
        "O § 7.º-A, inserido pela Lei n.º 14.112/2020, confirmou que as execuções fiscais "
        "ficam suspensas, podendo o Fisco optar entre: (i) habilitar o crédito na falência; "
        "ou (ii) prosseguir com a execução em curso.",
        font=_SERIF, size=9.5,
    ))
    story.append(_para(
        "Nos processos analisados, verifica-se que a Procuradoria-Geral do Estado de "
        "São Paulo (PGE/SP) ainda não formalizou a opção de habilitação ou continuidade em "
        "todos os feitos, sendo recomendável a instauração de diálogo entre o Administrador "
        "Judicial e a Fazenda Estadual para regularização da situação.",
        font=_SERIF, size=9.5,
    ))
    story.append(Spacer(1, 0.2 * cm))
    return story


def _build_process_detail(
    exec_num: str,
    cdas: List[CDA],
    info: ESAJProcessInfo,
    seq: int,
) -> List:
    story: List = []

    badge = info.status_badge if info else "NÃO CONSULTADO"
    badge_color = _badge_color(badge)

    # Process title block
    title_rows = [[
        Paragraph(
            f"<b>{seq}. Processo n.º {exec_num}</b>",
            ParagraphStyle("pt", fontName=_SANS_B, fontSize=10, textColor=_WHITE),
        ),
        Paragraph(
            f"<b>{badge}</b>",
            ParagraphStyle("pb", fontName=_SANS_B, fontSize=10,
                           textColor=badge_color, alignment=TA_RIGHT),
        ),
    ]]
    tbl_title = Table(title_rows, colWidths=[11 * cm, 5.6 * cm])
    tbl_title.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(tbl_title)

    if info and not info.error:
        # Process info table
        info_data = [
            ["Classe:", info.classe or "Execução Fiscal"],
            ["Assunto:", info.assunto or "—"],
            ["Distribuição:", info.distribuicao or "—"],
            ["Juízo:", info.juiz or "—"],
            ["Valor da Ação:", info.valor_acao or _brl(sum(c.valor_total for c in cdas))],
        ]
        if info.parties:
            for p in info.parties:
                info_data.append(["", p])

        cell_style = ParagraphStyle("ci", fontName=_SANS, fontSize=8.5, leading=12)
        cell_bold  = ParagraphStyle("cb", fontName=_SANS_B, fontSize=8.5, leading=12, textColor=_NAVY)

        formatted = [
            [Paragraph(r[0], cell_bold), Paragraph(r[1], cell_style)]
            for r in info_data
        ]
        tbl_info = Table(formatted, colWidths=[3.5 * cm, 13.1 * cm])
        tbl_info.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_GRAY_LIGHT, _WHITE]),
        ]))
        story.append(tbl_info)

    elif info and info.error:
        story.append(Spacer(1, 0.1 * cm))
        story.append(_para(
            f"<b>Observação:</b> {info.error}",
            font=_SANS, size=8.5, color=_RED_BADGE,
        ))

    # CDAs sub-table
    story.append(Spacer(1, 0.25 * cm))
    story.append(_para("CDAs vinculadas a este processo:", font=_SANS_B, size=8.5,
                        color=_NAVY, align=TA_LEFT, space_after=3))

    cda_header = [
        Paragraph("<b>Nº CDA</b>",    ParagraphStyle("ch", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Tipo</b>",       ParagraphStyle("ch", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Principal</b>",  ParagraphStyle("ch", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Atualizado</b>", ParagraphStyle("ch", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
        Paragraph("<b>Situação</b>",   ParagraphStyle("ch", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
    ]
    cda_rows = [cda_header]
    for i, c in enumerate(cdas):
        cda_rows.append([
            Paragraph(c.number, ParagraphStyle("cc", fontName=_MONO, fontSize=8, alignment=TA_CENTER)),
            Paragraph(c.tipo_debito, ParagraphStyle("cc", fontName=_SANS, fontSize=7.5, alignment=TA_CENTER)),
            Paragraph(_brl(c.principal), ParagraphStyle("cc", fontName=_SANS, fontSize=7.5, alignment=TA_RIGHT)),
            Paragraph(_brl(c.valor_total), ParagraphStyle("cc", fontName=_SANS, fontSize=7.5, alignment=TA_RIGHT)),
            Paragraph(c.situacao, ParagraphStyle("cc", fontName=_SANS, fontSize=7.5, alignment=TA_CENTER)),
        ])
    cda_tbl = Table(
        cda_rows,
        colWidths=[3.5 * cm, 3.2 * cm, 3.0 * cm, 3.0 * cm, 3.9 * cm],
        repeatRows=1,
    )
    cda_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  _NAVY_LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _TABLE_ALT]),
        ("GRID",           (0, 0), (-1, -1), 0.3, _GRAY_MID),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(cda_tbl)

    # Events
    if info and info.events:
        story.append(Spacer(1, 0.25 * cm))
        story.append(_para("Andamento processual recente (últimas movimentações):",
                           font=_SANS_B, size=8.5, color=_NAVY, align=TA_LEFT, space_after=3))

        ev_header = [
            Paragraph("<b>Data</b>",          ParagraphStyle("eh", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_CENTER)),
            Paragraph("<b>Movimentação</b>",   ParagraphStyle("eh", fontName=_SANS_B, fontSize=7.5, textColor=_WHITE, alignment=TA_LEFT)),
        ]
        ev_rows = [ev_header]
        for i, ev in enumerate(info.events[:10]):
            mark = ""
            if ev.is_suspension:
                mark = " ⚠"
            elif ev.is_extinction:
                mark = " ✗"
            elif ev.is_bankruptcy_related:
                mark = " ⚖"
            ev_rows.append([
                Paragraph(ev.date, ParagraphStyle("ed", fontName=_MONO, fontSize=7.5, alignment=TA_CENTER)),
                Paragraph(ev.description + mark, ParagraphStyle("ed2", fontName=_SANS, fontSize=7.5, leading=11, alignment=TA_JUSTIFY)),
            ])

        ev_tbl = Table(ev_rows, colWidths=[2.5 * cm, 14.1 * cm], repeatRows=1)
        ev_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0),  _NAVY_LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _TABLE_ALT]),
            ("GRID",           (0, 0), (-1, -1), 0.3, _GRAY_MID),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",     (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
            ("LEFTPADDING",    (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
        ]))
        story.append(ev_tbl)

        story.append(Spacer(1, 0.1 * cm))
        story.append(_para(
            "⚠ = movimentação de suspensão  |  ✗ = extinção/arquivamento  |  ⚖ = relacionada à falência",
            font=_SANS, size=7, color=_GRAY_DARK, align=TA_LEFT,
        ))

    # Situational analysis box
    story.append(Spacer(1, 0.3 * cm))

    analysis_lines = []
    if info:
        if info.is_suspended:
            ev = info.suspension_event
            analysis_lines.append(
                f"<b>Suspensão identificada:</b> O processo encontra-se suspenso. "
                + (f"Movimentação de referência: {ev.date} – {ev.description[:150]}." if ev else "")
            )
        if info.is_extinct:
            ev = info.extinction_event
            analysis_lines.append(
                f"<b>Extinção/Arquivamento identificado:</b> "
                + (f"Movimentação: {ev.date} – {ev.description[:150]}." if ev else "Verificar detalhes no ESAJ.")
            )
        if not info.is_suspended and not info.is_extinct and not info.error:
            analysis_lines.append(
                "<b>Processo em andamento:</b> Não foram identificadas movimentações recentes de "
                "suspensão ou extinção. Recomenda-se verificação manual no ESAJ TJSP para confirmar "
                "o status atual e providenciar, se for o caso, a comunicação ao Juízo da execução "
                "sobre a decretação de falência."
            )
        if info.error:
            analysis_lines.append(f"<b>Atenção:</b> {info.error}")
    else:
        analysis_lines.append("Processo não consultado. Verifique manualmente no ESAJ TJSP.")

    analysis_text = "<br/>".join(analysis_lines) if analysis_lines else ""
    if analysis_text:
        box_data = [[Paragraph(analysis_text,
                               ParagraphStyle("an", fontName=_SERIF, fontSize=9,
                                              leading=13, textColor=_NAVY,
                                              alignment=TA_JUSTIFY))]]
        box_tbl = Table(box_data, colWidths=[W - 2 * MARGIN_H])
        box_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _GRAY_LIGHT),
            ("LEFTBORDER",    (0, 0), (0, -1),  4, _GOLD),
            ("LINEBEFORE",    (0, 0), (0, -1),  4, _GOLD),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        story.append(box_tbl)

    story.append(Spacer(1, 0.5 * cm))
    return story


def _build_conclusion(
    calc: CalculationReport,
    esaj: Dict[str, ESAJProcessInfo],
    report_date: str,
) -> List:
    story = _section_title("Conclusão e Recomendações")

    n_susp  = sum(1 for v in esaj.values() if v.is_suspended)
    n_ext   = sum(1 for v in esaj.values() if v.is_extinct)
    n_error = sum(1 for v in esaj.values() if v.error)
    n_exec  = len(calc.unique_executions)

    story.append(_para(
        f"Com base nas consultas realizadas ao sistema ESAJ TJSP em {report_date}, "
        f"foram analisadas <b>{n_exec} execuções fiscais</b> vinculadas à falência de "
        f"<b>{calc.company}</b> (decreto de falência: {calc.data_falencia}), "
        f"totalizando <b>{_brl(calc.valor_total_geral)}</b> em encargos atualizados.",
        font=_SERIF, size=9.5,
    ))

    bullets = []
    if n_susp:
        bullets.append(
            f"• <b>{n_susp} execução(ões) com suspensão identificada</b> – "
            "a suspensão está em conformidade com o art. 6.º da Lei 11.101/2005. "
            "Recomenda-se formalizar a opção de habilitação ou continuidade junto à PGE/SP."
        )
    if n_ext:
        bullets.append(
            f"• <b>{n_ext} execução(ões) com extinção/arquivamento</b> – "
            "verificar se houve quitação parcial ou total e avaliar impacto no passivo falimentar."
        )
    if n_error:
        bullets.append(
            f"• <b>{n_error} processo(s) não puderam ser consultados automaticamente</b> – "
            "realizar consulta manual no ESAJ TJSP para obter o status atualizado."
        )

    for b in bullets:
        story.append(_para(b, font=_SERIF, size=9.5, align=TA_LEFT))
        story.append(Spacer(1, 0.1 * cm))

    story.append(_para(
        "Recomenda-se que o Administrador Judicial encaminhe ofício às Varas de Execuções Fiscais "
        "competentes comunicando o decreto de falência (caso ainda não o tenha feito), e que a "
        "Fazenda do Estado seja instada a formalizar sua opção (habilitação ou prosseguimento) "
        "nos termos do art. 6.º, § 7.º-A, da Lei 11.101/2005, a fim de regularizar o passivo "
        "tributário no âmbito do processo falimentar.",
        font=_SERIF, size=9.5,
    ))

    story.append(Spacer(1, 1.5 * cm))

    # Signature
    sig_data = [[
        Paragraph(
            f"{calc.data_falencia.split('/')[2] if '/' in calc.data_falencia else '2025'}, "
            f"{report_date}",
            ParagraphStyle("sd", fontName=_SERIF, fontSize=9, alignment=TA_CENTER),
        ),
    ]]
    sig_tbl = Table(sig_data, colWidths=[W - 2 * MARGIN_H])
    sig_tbl.setStyle(TableStyle([
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_tbl)

    story.append(Spacer(1, 2.0 * cm))

    sig_line = Table(
        [["", "", ""]],
        colWidths=[4 * cm, 8.6 * cm, 4 * cm],
    )
    sig_line.setStyle(TableStyle([
        ("LINEABOVE",     (1, 0), (1, 0), 0.8, _NAVY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sig_line)
    story.append(Spacer(1, 0.2 * cm))
    story.append(_para("Administrador Judicial", font=_SANS_B, size=9,
                        color=_NAVY, align=TA_CENTER))
    story.append(_para(f"Falência de {calc.company}", font=_SANS, size=8.5,
                        color=_GRAY_DARK, align=TA_CENTER))

    return story


# ── Main entry point ───────────────────────────────────────────────────────────
def generate_report(
    calc: CalculationReport,
    esaj_results: Dict[str, ESAJProcessInfo],
    output_path: str,
) -> str:
    """Generate the PDF report and save to output_path. Returns the path."""
    report_date = datetime.now().strftime('%d/%m/%Y')
    tmpl = _PageTemplate(calc.company, report_date)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=2.5 * cm,
        bottomMargin=2.2 * cm,
        title=f"Pesquisa Processual – Execuções Fiscais – {calc.company}",
        author="Sistema SAEF – ESAJ TJSP",
        subject="Relatório de Execuções Fiscais",
    )

    story: List = []

    # Cover (renders via onFirstPage; story starts on page 2)
    story.append(PageBreak())

    # 1. Introduction
    story += _build_intro(calc, esaj_results)
    story.append(Spacer(1, 0.2 * cm))

    # 2. Legal framework
    story += _build_legal_framework()
    story.append(Spacer(1, 0.2 * cm))

    # 3. Summary table
    story += _build_summary_table(calc, esaj_results)
    story.append(PageBreak())

    # 4. Detail per process
    story += _section_title("2. Análise Individual das Execuções Fiscais")
    by_exec = calc.cdas_by_execution

    for seq, exec_num in enumerate(calc.unique_executions, start=1):
        cdas = by_exec.get(exec_num, [])
        info = esaj_results.get(exec_num)
        story += _build_process_detail(exec_num, cdas, info, seq)

    story.append(PageBreak())

    # 5. Conclusion
    story += _build_conclusion(calc, esaj_results, report_date)

    def _cover(canv, doc):
        _build_cover(canv, calc, report_date)

    def _inner(canv, doc):
        tmpl.on_page(canv, doc)

    doc.build(story, onFirstPage=_cover, onLaterPages=_inner)
    return output_path
