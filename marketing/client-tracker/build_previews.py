#!/usr/bin/env python3
"""Build Client Tracker marketing previews from LibreOffice worksheet exports.

The inputs are rasterized pages from the fictional sample workbook PDF. This
script crops and captions those real worksheet renders; it does not recreate
or alter worksheet cells.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PAGE_REFERENCE = (1430, 1105)  # LibreOffice PDF pages rasterized at 130 DPI.
PURPLE = "#1E1B4B"
INDIGO = "#4338CA"
PAPER = "#FFFFFF"
CANVAS = "#F4F2FC"
INK = "#27243F"
MUTED = "#686782"
LINE = "#D9D7E7"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
        if bold
        else [
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def load_crop(path: Path, box: tuple[int, int, int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    sx = image.width / PAGE_REFERENCE[0]
    sy = image.height / PAGE_REFERENCE[1]
    scaled_box = tuple(
        round(value * (sx if index in (0, 2) else sy))
        for index, value in enumerate(box)
    )
    return image.crop(scaled_box)


def fit_width(image: Image.Image, width: int) -> Image.Image:
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, color: str, bold: bool = False) -> None:
    draw.text(xy, text, font=font(size, bold), fill=color)


def static_frame(title: str, subtitle: str, body: Image.Image) -> Image.Image:
    width = 1200
    pad = 36
    body_width = width - 2 * pad - 24
    rendered = fit_width(body, body_width)
    header_h = 122
    body_top = header_h + 24
    footer_h = 66
    height = body_top + rendered.height + 24 + footer_h

    canvas = Image.new("RGB", (width, height), CANVAS)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, header_h), fill=PURPLE)
    label(draw, (pad, 18), "CLIENT TRACKER", 20, "#C7C3F5", True)
    label(draw, (pad, 43), title, 34, PAPER, True)
    label(draw, (pad, 88), subtitle, 18, "#E8E6F7")

    panel = (pad, body_top, width - pad, body_top + rendered.height + 24)
    draw.rounded_rectangle(panel, radius=16, fill=PAPER, outline=LINE, width=2)
    canvas.paste(rendered, (pad + 12, body_top + 12))

    footer_y = height - footer_h
    label(draw, (pad, footer_y + 12), "FICTIONAL SAMPLE DATA  ·  WORKSHEET PREVIEW", 16, MUTED, True)
    label(draw, (pad, footer_y + 36), "Exported from LibreOffice Calc; not a live-app screenshot.", 15, MUTED)
    return canvas


def client_comparison(before: Image.Image, after: Image.Image) -> Image.Image:
    width = 1200
    pad = 36
    body_width = width - 2 * pad - 24
    before_fit = fit_width(before, body_width)
    after_fit = fit_width(after, body_width)
    label_h = 42
    gap = 20
    header_h = 122
    body_top = header_h + 24
    body_h = 2 * (label_h + before_fit.height) + gap + 24
    footer_h = 66
    height = body_top + body_h + footer_h

    canvas = Image.new("RGB", (width, height), CANVAS)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, header_h), fill=PURPLE)
    label(draw, (pad, 18), "CLIENT TRACKER", 20, "#C7C3F5", True)
    label(draw, (pad, 43), "Adding one fictional client", 34, PAPER, True)
    label(draw, (pad, 88), "Before and after worksheet exports. No typing was recorded.", 18, "#E8E6F7")

    y = body_top + 12
    for title, image in (("BEFORE  ·  10 SAMPLE CLIENTS", before_fit), ("AFTER  ·  C011 RILEY MORGAN ADDED", after_fit)):
        label(draw, (pad + 14, y), title, 18, INDIGO, True)
        y += label_h
        panel = (pad, y - 6, width - pad, y + image.height + 6)
        draw.rounded_rectangle(panel, radius=12, fill=PAPER, outline=LINE, width=2)
        canvas.paste(image, (pad + 12, y))
        y += image.height + gap

    footer_y = height - footer_h
    label(draw, (pad, footer_y + 12), "FICTIONAL SAMPLE DATA  ·  WORKSHEET PREVIEW", 16, MUTED, True)
    label(draw, (pad, footer_y + 36), "One Lead record is added within the existing client table.", 15, MUTED)
    return canvas


def invoice_fields(left: Image.Image, right: Image.Image) -> Image.Image:
    gap = 28
    width = left.width + gap + right.width
    height = max(left.height, right.height)
    composite = Image.new("RGB", (width, height), PAPER)
    composite.paste(left, (0, 0))
    composite.paste(right, (left.width + gap, 0))
    return composite


def gif_slide(
    title: str,
    subtitle: str,
    content: Image.Image,
    sequence_index: int,
    sequence_total: int,
) -> Image.Image:
    width, height = 1200, 1000
    pad = 42
    header_h = 122
    footer_h = 72
    panel_width = width - 2 * pad - 28
    body_top = header_h + 24
    body_bottom = height - footer_h - 18
    panel_height = body_bottom - body_top
    scale = min(panel_width / content.width, (panel_height - 24) / content.height)
    rendered = content.resize(
        (round(content.width * scale), round(content.height * scale)),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGB", (width, height), CANVAS)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, header_h), fill=PURPLE)
    label(draw, (pad, 16), f"FICTIONAL DEMO  ·  {sequence_index:02d}/{sequence_total:02d}", 20, "#C7C3F5", True)
    label(draw, (pad, 42), title, 34, PAPER, True)
    label(draw, (pad, 88), subtitle, 18, "#E8E6F7")

    panel = (pad, body_top, width - pad, body_bottom)
    draw.rounded_rectangle(panel, radius=16, fill=PAPER, outline=LINE, width=2)
    x = (width - rendered.width) // 2
    y = body_top + (panel_height - rendered.height) // 2
    canvas.paste(rendered, (x, y))

    footer_y = height - footer_h
    label(draw, (pad, footer_y + 12), "SILENT SIMULATED SEQUENCE  ·  WORKSHEET EXPORTS", 16, MUTED, True)
    label(draw, (pad, footer_y + 36), "No live GUI input or cursor recording.", 15, MUTED)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-before", type=Path, required=True)
    parser.add_argument("--dashboard-after", type=Path, required=True)
    parser.add_argument("--clients-before", type=Path, required=True)
    parser.add_argument("--clients-after", type=Path, required=True)
    parser.add_argument("--invoices", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.dashboard_before, args.dashboard_after, args.clients_before, args.clients_after, args.invoices):
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dashboard_after = load_crop(args.dashboard_after, (96, 128, 960, 973))
    dashboard_before_top = load_crop(args.dashboard_before, (96, 128, 960, 520))
    dashboard_after_top = load_crop(args.dashboard_after, (96, 128, 960, 520))
    clients_before = load_crop(args.clients_before, (96, 129, 905, 456))
    clients_after = load_crop(args.clients_after, (96, 129, 905, 456))
    invoice_page = Image.open(args.invoices).convert("RGB")
    sx = invoice_page.width / PAGE_REFERENCE[0]
    sy = invoice_page.height / PAGE_REFERENCE[1]
    def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(round(value * (sx if index in (0, 2) else sy)) for index, value in enumerate(box))
    invoice_left = invoice_page.crop(scaled_box((96, 220, 384, 657)))
    invoice_right = invoice_page.crop(scaled_box((1008, 220, 1326, 657)))
    invoice_view = invoice_fields(invoice_left, invoice_right)

    images = {
        "01-dashboard.png": static_frame(
            "Dashboard", "Sample report date: 26 Oct 2026 · after one Lead entry", dashboard_after
        ),
        "02-client-before-after.png": client_comparison(clients_before, clients_after),
        "03-invoice-status.png": static_frame(
            "Invoice status", "Selected worksheet columns from the same fictional invoice rows", invoice_view
        ),
    }
    for name, image in images.items():
        image.save(args.output_dir / name, format="PNG", optimize=True)

    slides = [
        gif_slide("Dashboard before", "Two open Leads in the original sample", dashboard_before_top, 1, 5),
        gif_slide("Client list before", "Ten fictional clients in the source sample", clients_before, 2, 5),
        gif_slide("One fictional Lead added", "C011 Riley Morgan entered in the existing Clients table", clients_after, 3, 5),
        gif_slide("Dashboard after", "The open-Lead count updates from 2 to 3", dashboard_after_top, 4, 5),
        gif_slide("Invoice status", "Selected rows show Overdue and Open examples", invoice_view, 5, 5),
    ]
    frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128) for frame in slides]
    frames[0].save(
        args.output_dir / "client-tracker-demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1600] * len(frames),
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    main()
