#!/usr/bin/env python3
"""Build a Client Tracker quick-start PDF and worksheet-preview images.

The input PNGs are rasterized pages from the workbook's own print exports.
This script crops and captions those exports; it does not recreate or edit
spreadsheet cells.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as PDFImage
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REFERENCE_PAGE = (1430, 1105)
PURPLE = "#1E1B4B"
INDIGO = "#4338CA"
PAPER = "#FFFFFF"
CANVAS = "#F4F2FC"
INK = "#27243F"
MUTED = "#686782"
LINE = "#D9D7E7"


def image_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("arialbd.ttf", "Arial_Bold.ttf") if bold else ("arial.ttf", "Arial.ttf")
    roots = (Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts/truetype/msttcorefonts"))
    for root in roots:
        for name in names:
            path = root / name
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def crop_page(path: Path, box: tuple[int, int, int, int]) -> Image.Image:
    with Image.open(path) as source:
        page = source.convert("RGB")
    sx = page.width / REFERENCE_PAGE[0]
    sy = page.height / REFERENCE_PAGE[1]
    scaled = tuple(
        round(value * (sx if index in (0, 2) else sy))
        for index, value in enumerate(box)
    )
    if scaled[0] < 0 or scaled[1] < 0 or scaled[2] > page.width or scaled[3] > page.height:
        raise ValueError(f"Crop box {box} falls outside page {path} ({page.width}x{page.height}).")
    return page.crop(scaled)


def fit_width(image: Image.Image, width: int) -> Image.Image:
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill: str, bold: bool = False) -> None:
    draw.text(xy, value, font=image_font(size, bold), fill=fill)


def frame_header(draw: ImageDraw.ImageDraw, step: int, title: str, subtitle: str) -> None:
    draw.rectangle((0, 0, 1200, 128), fill=PURPLE)
    draw_text(draw, (36, 15), "CLIENT TRACKER  |  QUICK START", 18, "#C7C3F5", True)
    draw_text(draw, (36, 41), f"{step:02d}  {title}", 34, PAPER, True)
    draw_text(draw, (36, 88), subtitle, 17, "#E8E6F7")


def frame_footer(draw: ImageDraw.ImageDraw, height: int) -> None:
    y = height - 70
    draw_text(draw, (36, y + 9), "FICTIONAL SAMPLE DATA  |  WORKSHEET PREVIEW", 15, MUTED, True)
    draw_text(draw, (36, y + 34), "LibreOffice Calc worksheet export - not a live-app screenshot.", 14, MUTED)


def make_single_frame(step: int, title: str, subtitle: str, crop: Image.Image, output: Path) -> None:
    body_width = 1128
    rendered = fit_width(crop, body_width)
    body_top = 152
    height = body_top + rendered.height + 24 + 70
    canvas = Image.new("RGB", (1200, height), CANVAS)
    draw = ImageDraw.Draw(canvas)
    frame_header(draw, step, title, subtitle)
    panel = (24, body_top - 12, 1176, body_top + rendered.height + 12)
    draw.rounded_rectangle(panel, radius=14, fill=PAPER, outline=LINE, width=2)
    canvas.paste(rendered, (36, body_top))
    frame_footer(draw, height)
    canvas.save(output, format="PNG", optimize=True)


def make_invoice_frame(input_crop: Image.Image, calculated_crop: Image.Image, output: Path) -> None:
    body_top = 183
    card_width = 552
    image_width = card_width - 24
    left = fit_width(input_crop, image_width)
    right = fit_width(calculated_crop, image_width)
    body_height = max(left.height, right.height)
    height = body_top + body_height + 24 + 70
    canvas = Image.new("RGB", (1200, height), CANVAS)
    draw = ImageDraw.Draw(canvas)
    frame_header(
        draw,
        2,
        "Log an invoice",
        "Enter invoice details; blank Terms or Tax rate use Settings defaults.",
    )
    draw_text(draw, (36, 150), "INPUT COLUMNS", 17, INDIGO, True)
    draw_text(draw, (612, 150), "CALCULATED COLUMNS", 17, INDIGO, True)
    left_panel = (24, body_top - 12, 24 + card_width, body_top + left.height + 12)
    right_panel = (600, body_top - 12, 600 + card_width, body_top + right.height + 12)
    draw.rounded_rectangle(left_panel, radius=12, fill=PAPER, outline=LINE, width=2)
    draw.rounded_rectangle(right_panel, radius=12, fill=PAPER, outline=LINE, width=2)
    canvas.paste(left, (36, body_top))
    canvas.paste(right, (612, body_top))
    frame_footer(draw, height)
    canvas.save(output, format="PNG", optimize=True)


def register_pdf_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\arial.ttf")
    bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if regular.is_file() and bold.is_file():
        pdfmetrics.registerFont(TTFont("GuideArial", str(regular)))
        pdfmetrics.registerFont(TTFont("GuideArialBold", str(bold)))
        return "GuideArial", "GuideArialBold"
    return "Helvetica", "Helvetica-Bold"


def image_flowable(path: Path, width: float) -> PDFImage:
    with Image.open(path) as source:
        ratio = source.height / source.width
    flowable = PDFImage(str(path), width=width, height=width * ratio)
    flowable.hAlign = "CENTER"
    return flowable


def make_pdf(output: Path, image_paths: dict[str, Path]) -> None:
    regular, bold = register_pdf_fonts()
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=72,
        bottomMargin=34,
        title="Client Tracker Quick Start",
        author="Client Tracker",
        subject="Manual guide to clients, invoices, the dashboard and follow-ups",
    )
    base = getSampleStyleSheet()
    intro = ParagraphStyle(
        "GuideIntro",
        parent=base["BodyText"],
        fontName=bold,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor(INK),
        spaceAfter=0,
    )
    body = ParagraphStyle(
        "GuideBody",
        parent=base["BodyText"],
        fontName=regular,
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor(INK),
        spaceAfter=0,
    )
    note = ParagraphStyle(
        "GuideNote",
        parent=body,
        fontSize=9,
        leading=11.5,
        textColor=colors.HexColor(PURPLE),
    )
    story = [
        Paragraph(
            "Start with the blank workbook for your own records, or use the sample file to follow along.",
            intro,
        ),
        Spacer(1, 5),
        KeepTogether(
            [
                image_flowable(image_paths["client"], 445),
                Spacer(1, 4),
                Paragraph(
                    "On <b>Clients</b>, add one row per client. Choose a unique Client ID; fill the indigo input columns and leave teal calculated columns alone. Match the ID exactly on related tabs.",
                    body,
                ),
            ]
        ),
        Spacer(1, 7),
        KeepTogether(
            [
                image_flowable(image_paths["invoice"], 445),
                Spacer(1, 4),
                Paragraph(
                    "On <b>Invoices</b>, enter the invoice number, Client ID, issue date and subtotal. Leave Terms or Tax rate blank to use the Settings defaults; leave Issue date blank for a draft.",
                    body,
                ),
            ]
        ),
        Spacer(1, 7),
        Table(
            [[Paragraph("<b>Capacity</b>  Each data tab supports 300 records. Extra rows are outside linked totals and dropdowns.", note)]],
            colWidths=[540],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAE8F8")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(LINE)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        PageBreak(),
        Paragraph(
            "Use the Dashboard to review what is owed and which follow-ups need attention.",
            intro,
        ),
        Spacer(1, 5),
        KeepTogether(
            [
                image_flowable(image_paths["dashboard"], 430),
                Spacer(1, 4),
                Paragraph(
                    "Review money owed, overdue invoices, payments received in the last 30 days, and follow-ups due. The report date defaults to today; enter another date in the Report date override field on Settings to view a different day.",
                    body,
                ),
            ]
        ),
        Spacer(1, 7),
        KeepTogether(
            [
                image_flowable(image_paths["followups"], 430),
                Spacer(1, 4),
                Paragraph(
                    "On <b>Follow-ups</b>, choose a Client ID, add an Action and Due date. When complete, enter the date under Done on; open items also appear on the Dashboard.",
                    body,
                ),
            ]
        ),
    ]

    def page_chrome(pdf_canvas, page_doc) -> None:
        pdf_canvas.saveState()
        page_width, page_height = letter
        pdf_canvas.setFillColor(colors.HexColor(PURPLE))
        pdf_canvas.rect(0, page_height - 60, page_width, 60, stroke=0, fill=1)
        pdf_canvas.setFillColor(colors.HexColor("#C7C3F5"))
        pdf_canvas.setFont(bold, 10)
        pdf_canvas.drawString(36, page_height - 22, "CLIENT TRACKER")
        pdf_canvas.setFillColor(colors.white)
        pdf_canvas.setFont(bold, 19)
        pdf_canvas.drawString(36, page_height - 46, "Quick Start")
        pdf_canvas.setFillColor(colors.HexColor(MUTED))
        pdf_canvas.setFont(regular, 7.5)
        pdf_canvas.drawString(36, 18, "FICTIONAL SAMPLE DATA | WORKSHEET PREVIEWS FROM CALC EXPORTS")
        pdf_canvas.drawRightString(page_width - 36, 18, f"{page_doc.page} / 2")
        pdf_canvas.restoreState()

    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-page", required=True, type=Path, help="Rasterized Clients worksheet page")
    parser.add_argument("--invoice-page", required=True, type=Path, help="Rasterized Invoices worksheet page")
    parser.add_argument("--dashboard-page", required=True, type=Path, help="Rasterized Dashboard worksheet page")
    parser.add_argument("--follow-ups-page", required=True, type=Path, help="Rasterized Follow-ups worksheet page")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for the four PNGs and PDF")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = (args.client_page, args.invoice_page, args.dashboard_page, args.follow_ups_page)
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    crops = {
        "client": crop_page(args.client_page, (96, 129, 905, 456)),
        "invoice_input": crop_page(args.invoice_page, (96, 220, 756, 657)),
        "invoice_calculated": crop_page(args.invoice_page, (756, 220, 1326, 657)),
        "dashboard": crop_page(args.dashboard_page, (96, 129, 960, 520)),
        "followups": crop_page(args.follow_ups_page, (96, 129, 1180, 600)),
    }
    image_paths = {
        "client": args.output_dir / "01-add-client.png",
        "invoice": args.output_dir / "02-log-invoice.png",
        "dashboard": args.output_dir / "03-dashboard.png",
        "followups": args.output_dir / "04-follow-ups.png",
    }
    make_single_frame(
        1,
        "Add a client",
        "Choose a unique Client ID and fill the indigo input columns.",
        crops["client"],
        image_paths["client"],
    )
    make_invoice_frame(crops["invoice_input"], crops["invoice_calculated"], image_paths["invoice"])
    make_single_frame(
        3,
        "Check the Dashboard",
        "Review amounts owed, overdue items and follow-up counts.",
        crops["dashboard"],
        image_paths["dashboard"],
    )
    make_single_frame(
        4,
        "Plan a follow-up",
        "Record a Client ID, Action, Due and Done on date.",
        crops["followups"],
        image_paths["followups"],
    )
    make_pdf(args.output_dir / "client-tracker-quick-start.pdf", image_paths)
    print("Built:")
    for path in (*image_paths.values(), args.output_dir / "client-tracker-quick-start.pdf"):
        print(f"{path.name} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
