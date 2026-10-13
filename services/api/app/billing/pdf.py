"""Render existing invoice records; rendering never issues a new invoice."""
import io
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.billing.schemas import InvoiceOut


@lru_cache(maxsize=1)
def invoice_font() -> str:
    name = "PriveoInvoice"
    pdfmetrics.registerFont(TTFont(name, str(Path(__file__).parent / "assets" / "Manrope.ttf")))
    return name


def render_invoice(invoice: InvoiceOut, *, preview: bool, legacy: bool = False) -> bytes:
    stream = io.BytesIO()
    font = invoice_font()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("invoice-body", parent=styles["Normal"], fontName=font,
                          fontSize=10, leading=15, textColor=colors.HexColor("#252b35"))
    heading = ParagraphStyle("invoice-heading", parent=body, fontSize=23, leading=30)
    label = ParagraphStyle("invoice-label", parent=body, fontSize=9,
                           textColor=colors.HexColor("#596579"))
    right = ParagraphStyle("invoice-right", parent=body, alignment=TA_RIGHT)

    def paragraph(value, style=body):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)

    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                           topMargin=18 * mm, bottomMargin=22 * mm,
                           title=f"Invoice {invoice.number}", author=invoice.seller_name)
    width = A4[0] - 40 * mm
    story = [paragraph("INVOICE", heading), Spacer(1, 5 * mm)]
    if preview:
        story += [paragraph("PREVIEW — supplier/GST settings are incomplete. Not for tax use.", label),
                  Spacer(1, 4 * mm)]
    story += [paragraph(invoice.seller_name), paragraph(invoice.seller_address),
              paragraph(f"GSTIN: {invoice.seller_gstin}", label), Spacer(1, 8 * mm),
              paragraph(f"Invoice number: {invoice.number}"),
              paragraph(f"Issued on: {invoice.issued_on:%d-%b-%Y}"), Spacer(1, 6 * mm),
              paragraph("BILLED TO", label), paragraph(invoice.customer_name)]
    if invoice.vehicle:
        story.append(paragraph(invoice.vehicle))
    story.append(Spacer(1, 7 * mm))
    total = f"INR {invoice.amount_rupees:,.2f}"
    tax_rows = []
    if invoice.tax_details:
        tax = invoice.tax_details
        def money(key):
            return f"INR {tax[key] / 100:,.2f}"
        tax_rows.append([paragraph("Taxable value"), paragraph(money("taxable_paise"), right)])
        for key, name in (("cgst_paise", "CGST"), ("sgst_paise", "SGST"), ("igst_paise", "IGST")):
            if tax[key]:
                rate = tax["rate_percent"] if key == "igst_paise" else tax["rate_percent"] / 2
                tax_rows.append([paragraph(f"{name} ({rate:g}%)"), paragraph(money(key), right)])
    items = Table([
        [paragraph("Service", label), paragraph("Amount", right)],
        [paragraph(invoice.description), paragraph(total, right)],
        *tax_rows,
        [paragraph("Total paid"), paragraph(total, right)],
    ], colWidths=[width * .73, width * .27], repeatRows=1, hAlign="LEFT")
    items.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f5")),
        ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#cbd3df")),
        ("LINEABOVE", (0, -1), (-1, -1), .6, colors.HexColor("#cbd3df")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [items, Spacer(1, 5 * mm), paragraph("The total includes GST.", label)]
    if legacy:
        story.append(paragraph(
            "Legacy invoice: supplier details are shown from current settings; "
            "they were not stored when this invoice was issued.", label))
    if invoice.tax_details is None:
        story.append(paragraph("Legacy invoice: GST breakdown was not recorded at issue time.", label))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#596579"))
        canvas.drawString(20 * mm, 12 * mm, invoice.number)
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
