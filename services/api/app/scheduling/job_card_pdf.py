"""Job cards as a PDF (P1-2). Read only: it renders the rows from `app.scheduling.job_cards`.

Modelled on the invoice renderer in `app.billing.pdf` (reportlab, Manrope). Landscape
A4, so the detailed card lines fit on one table row each: zone, car model, cutoff,
service, time window, car number, customer, parking, status and notes. Each crew
member starts on a new page. The run date is printed in the header of every page,
and the Priveo logo sits beside it. Dates are dd-Mon-yy."""
from __future__ import annotations

import io
from datetime import date
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.changes.rules import show_date
from app.scheduling.job_cards import CrewCards

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "priveo-logo.png"
# The invoice font, kept in the billing assets (one copy of Manrope in the API).
FONT_FILE = Path(__file__).resolve().parents[1] / "billing" / "assets" / "Manrope.ttf"

PAGE = landscape(A4)
MARGIN = 12 * mm
INK = colors.HexColor("#252b35")
MUTED = colors.HexColor("#596579")
HEAD_FILL = colors.HexColor("#eef1f5")
RULE = colors.HexColor("#cbd3df")
LINE = colors.HexColor("#e3e8ef")
# Column widths in mm, in the order of HEADINGS. The last column takes the rest.
WIDTHS_MM = (24, 12, 24, 36, 40, 34, 18, 16)
HEADINGS = ("Time", "Zone", "Car", "Model", "Customer", "Service", "Cutoff", "Parking", "Status and notes")


@lru_cache(maxsize=1)
def card_font() -> str:
    name = "PriveoJobCard"
    pdfmetrics.registerFont(TTFont(name, str(FONT_FILE)))
    return name


def render_job_cards(day: date, crews: list[CrewCards]) -> bytes:
    """One PDF for every crew in `crews`, each crew on its own page or pages."""
    stream = io.BytesIO()
    font = card_font()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("card-body", parent=styles["Normal"], fontName=font,
                          fontSize=8.5, leading=10.5, textColor=INK)
    label = ParagraphStyle("card-label", parent=body, fontSize=8, leading=10, textColor=MUTED)
    heading = ParagraphStyle("card-heading", parent=body, fontSize=15, leading=19)
    cell = ParagraphStyle("card-cell", parent=body, fontSize=8, leading=9.5)
    head_cell = ParagraphStyle("card-head-cell", parent=cell, fontSize=7.5, textColor=MUTED)
    run = show_date(day)

    doc = SimpleDocTemplate(
        stream, pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=30 * mm, bottomMargin=18 * mm,
        title=f"Job cards {run}", author="Priveo Car Concierge",
    )
    width = PAGE[0] - 2 * MARGIN
    col_widths = [w * mm for w in WIDTHS_MM]
    col_widths.append(width - sum(col_widths))

    def text(value: str, style=cell) -> Paragraph:
        return Paragraph(escape(value or ""), style)

    story: list = []
    if not crews:
        story.append(Paragraph("No job cards for this day.", heading))
    for index, crew in enumerate(crews):
        if index:
            story.append(PageBreak())
        count = len(crew.rows)
        story += [
            Paragraph(escape(crew.name or "Crew"), heading),
            Paragraph(f"{count} {'job' if count == 1 else 'jobs'} on {run}", label),
            Spacer(1, 3 * mm),
        ]
        data = [[text(h, head_cell) for h in HEADINGS]]
        for r in crew.rows:
            data.append([
                text(r.window), text(r.zone), text(r.registration), text(r.model), text(r.customer),
                text(f"{r.service_code} {r.service_name}"), text(r.cutoff), text(r.parking),
                text("; ".join([r.status, *r.notes]) if r.notes else r.status),
            ])
        table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0), HEAD_FILL),
            ("LINEBELOW", (0, 0), (-1, 0), .6, RULE),
            ("LINEBELOW", (0, 1), (-1, -1), .4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    def frame(canvas, document):
        canvas.saveState()
        page_w, page_h = PAGE
        logo_h = 11 * mm
        logo_w = logo_h * 278 / 100
        canvas.drawImage(str(LOGO), MARGIN, page_h - 9 * mm - logo_h, width=logo_w, height=logo_h,
                         mask="auto", preserveAspectRatio=True)
        canvas.setFillColor(INK)
        canvas.setFont(font, 13)
        canvas.drawString(MARGIN + logo_w + 6 * mm, page_h - 13 * mm, "Job cards")
        canvas.setFont(font, 9)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN + logo_w + 6 * mm, page_h - 18.5 * mm, f"Run date: {run}")
        canvas.setFont(font, 8)
        canvas.drawString(MARGIN, 10 * mm, f"Priveo Car Concierge. Job cards {run}.")
        canvas.drawRightString(page_w - MARGIN, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return stream.getvalue()
