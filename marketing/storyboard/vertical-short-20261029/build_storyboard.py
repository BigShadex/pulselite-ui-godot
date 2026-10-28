"""Build transparent portrait overlays and a separate conservative safe-zone guide."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZE = (1080, 1920)
REDUCED = (360, 640)
FONT_NAME = "Pillow built-in Aileron Regular"
PALETTES = {
    "menu-kit": {"accent": (87, 218, 215), "paper": (241, 246, 244), "muted": (177, 199, 201), "panel": (9, 23, 35, 240), "line": (73, 135, 146, 255)},
    "sci-fi": {"accent": (88, 221, 240), "paper": (239, 246, 248), "muted": (163, 193, 209), "panel": (8, 22, 42, 240), "line": (63, 115, 156, 255)},
    "horror": {"accent": (250, 112, 80), "paper": (247, 239, 231), "muted": (197, 164, 159), "panel": (27, 12, 20, 240), "line": (127, 57, 64, 255)},
}
OVERLAYS = [
    {"name": "01-opening-title.png", "kind": "title"},
    {"name": "02-menu-kit-cue.png", "kind": "cue", "pack": "menu-kit", "event": "button_click", "file": "click_03.ogg"},
    {"name": "03-sci-fi-cue.png", "kind": "cue", "pack": "sci-fi", "event": "panel_open", "file": "panel_open_04.ogg"},
    {"name": "04-horror-cue.png", "kind": "cue", "pack": "horror", "event": "reward", "file": "reward_05.ogg"},
    {"name": "05-closing-card.png", "kind": "closing"},
]


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def put(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str, size: int,
        color: tuple[int, int, int], bold: bool = False,
        anchor: str | None = None) -> tuple[int, int, int, int]:
    f = font(size)
    stroke = max(1, size // 42) if bold else 0
    draw.text(xy, label, font=f, fill=color, anchor=anchor, stroke_width=stroke,
              stroke_fill=color)
    return draw.textbbox(xy, label, font=f, anchor=anchor, stroke_width=stroke)


def fit(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str, width: int,
        size: int, color: tuple[int, int, int], bold: bool = False) -> tuple[int, int, int, int]:
    while size > 24:
        f = font(size)
        stroke = max(1, size // 42) if bold else 0
        box = draw.textbbox((0, 0), label, font=f, stroke_width=stroke)
        if box[2] - box[0] <= width:
            break
        size -= 2
    return put(draw, xy, label, size, color, bold)


def fit_center(draw: ImageDraw.ImageDraw, center: tuple[int, int], label: str,
               width: int, size: int, color: tuple[int, int, int],
               bold: bool = False) -> tuple[int, int, int, int]:
    while size > 24:
        f = font(size)
        stroke = max(1, size // 42) if bold else 0
        box = draw.textbbox((0, 0), label, font=f, stroke_width=stroke)
        if box[2] - box[0] <= width:
            break
        size -= 2
    return put(draw, center, label, size, color, bold, "mm")


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
            fill: tuple[int, int, int, int], outline: tuple[int, int, int, int],
            radius: int = 30, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def title_card() -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    theme = PALETTES["menu-kit"]
    rounded(draw, (80, 315, 900, 1050), theme["panel"], theme["line"], 42, 4)
    draw.rounded_rectangle((80, 315, 900, 333), radius=8, fill=theme["accent"])
    brand = put(draw, (490, 495), "PULSELITE", 92, theme["paper"], True, "mm")
    hook = fit_center(draw, (490, 620), "UI SOUND EFFECTS", 720, 56, theme["accent"], True)
    packs = fit_center(draw, (490, 712), "MENU KIT  /  SCI-FI  /  HORROR", 720, 34, theme["muted"], True)
    draw.line((178, 786, 802, 786), fill=theme["line"], width=3)
    note1 = fit_center(draw, (490, 865), "ILLUSTRATIVE UI - NOT INCLUDED", 720, 36, theme["paper"], True)
    note2 = fit_center(draw, (490, 928), "PROCEDURAL DSP AUDIO  /  AI-ASSISTED VISUALS", 720, 30, theme["muted"], True)
    return image, {"group_bbox": [80, 315, 900, 1050], "center": [490, 682.5],
                   "brand_bbox": list(brand), "hook_bbox": list(hook),
                   "disclosure_bbox": [*note1, *note2], "canvas": list(SIZE)}


def cue_card(pack: str, event: str, filename: str) -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    box = (80, 1110, 900, 1460)
    rounded(draw, box, p["panel"], p["line"], 30, 3)
    draw.rounded_rectangle((80, 1110, 98, 1460), radius=8, fill=p["accent"])
    put(draw, (132, 1166), f"{pack.upper()} / EXAMPLE CUE", 29, p["accent"], True)
    event_box = fit(draw, (132, 1246), event.upper(), 710, 48, p["paper"], True)
    path_box = fit(draw, (132, 1320), filename, 710, 40, p["muted"], True)
    put(draw, (132, 1400), "CAPTION CARD / NO AUDIO EMBEDDED", 21, p["muted"], True)
    return image, {"box": list(box), "event_bbox": list(event_box),
                   "filename_bbox": list(path_box), "canvas": list(SIZE)}


def closing_card() -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    p = PALETTES["menu-kit"]
    rounded(draw, (80, 360, 900, 1370), p["panel"], p["line"], 40, 4)
    put(draw, (490, 470), "PULSELITE", 86, p["paper"], True, "mm")
    fit_center(draw, (490, 555), "UI SOUND EFFECTS", 700, 42, p["accent"], True)
    put(draw, (490, 685), "MENU KIT  /  SCI-FI  /  HORROR", 30, p["muted"], True, "mm")
    rounded(draw, (145, 780, 835, 960), p["panel"], p["line"], 25, 2)
    put(draw, (490, 828), "BIGSHADEX.ITCH.IO", 38, p["accent"], True, "mm")
    put(draw, (490, 900), "LINKS IN DESCRIPTION", 29, p["paper"], True, "mm")
    rounded(draw, (145, 1000, 835, 1155), p["panel"], p["line"], 24, 2)
    put(draw, (490, 1045), "BIGSHADEX.GITHUB.IO", 31, p["accent"], True, "mm")
    put(draw, (490, 1105), "/PULSELITE-PREVIEWER/", 27, p["paper"], True, "mm")
    put(draw, (490, 1210), "ILLUSTRATIVE UI - NOT INCLUDED", 29, p["paper"], True, "mm")
    put(draw, (490, 1272), "PROCEDURAL DSP AUDIO  /  AI-ASSISTED VISUALS", 24, p["muted"], True, "mm")
    return image, {"card_bbox": [80, 360, 900, 1370], "canvas": list(SIZE),
                   "links_text": ["bigshadex.itch.io", "bigshadex.github.io/pulselite-previewer/"]}


def safe_zone_guide() -> tuple[Image.Image, dict]:
    image = Image.new("RGBA", SIZE, (9, 16, 26, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    # These margins are a conservative proposal, not platform certification.
    draw.rectangle((900, 0, 1079, 1919), fill=(244, 92, 75, 58))
    draw.rectangle((0, 1500, 1079, 1919), fill=(240, 174, 68, 68))
    draw.rectangle((80, 160, 899, 1499), outline=(89, 231, 177, 255), width=5)
    put(draw, (80, 70), "VERTICAL SHORT / PROPOSED COMPOSITION GUIDE", 32, (247, 249, 250), True)
    put(draw, (80, 105), "GUIDE ONLY - VERIFY IN THE DESTINATION APP", 25, (186, 207, 216), True)
    put(draw, (110, 210), "PROPOSED CONTENT AREA", 29, (89, 231, 177), True)
    put(draw, (930, 220), "KEEP CLEAR", 22, (255, 210, 196), True)
    put(draw, (90, 1542), "RESERVE BOTTOM FOR PLATFORM CONTROLS", 23, (255, 220, 173), True)
    return image, {"proposed_content_rect": [80, 160, 900, 1500],
                   "right_platform_reserve": [900, 0, 1080, 1920],
                   "bottom_platform_reserve": [0, 1500, 1080, 1920],
                   "note": "Conservative layout proposal only; not a platform-safe-area guarantee."}


def render_asset(item: dict) -> tuple[Image.Image, dict]:
    if item["kind"] == "title":
        return title_card()
    if item["kind"] == "cue":
        return cue_card(item["pack"], item["event"], item["file"])
    if item["kind"] == "closing":
        return closing_card()
    raise ValueError(item)


def build(output: Path, preview: Path, sample_only: bool, overwrite: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    selected = OVERLAYS[:2] if sample_only else OVERLAYS
    all_rows = []
    preview_files = []
    for item in selected:
        target = output / item["name"]
        if target.exists() and not overwrite:
            raise FileExistsError(f"Refusing to replace existing storyboard PNG without --overwrite: {target.name}")
        image, measurement = render_asset(item)
        image.save(target, format="PNG", optimize=True, compress_level=9)
        with Image.open(target) as check:
            if check.size != SIZE or check.mode != "RGBA":
                raise ValueError(f"Expected transparent 1080x1920 RGBA output: {target.name}")
        reduced = image.resize(REDUCED, Image.Resampling.LANCZOS)
        preview_path = preview / f"{target.stem}-360x640.png"
        reduced.save(preview_path, format="PNG", optimize=True)
        all_rows.append({"path": target.name, "kind": item["kind"], "dimensions": list(SIZE),
                         "mode": "RGBA", "alpha_min": image.getchannel("A").getextrema()[0],
                         "alpha_max": image.getchannel("A").getextrema()[1],
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                         "bytes": target.stat().st_size, "measurement": measurement})
        preview_files.append(preview_path)
        print(f"OVERLAY_OK {target.name} {SIZE[0]}x{SIZE[1]} RGBA {target.stat().st_size} bytes")
    guide_path = output / "safe-zone-guide.png"
    guide, guide_measurement = safe_zone_guide()
    if guide_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to replace existing guide without --overwrite: {guide_path.name}")
    guide.save(guide_path, format="PNG", optimize=True)
    with Image.open(guide_path) as check:
        if check.size != SIZE or check.mode != "RGBA":
            raise ValueError("Safe-zone guide geometry or mode mismatch")
    guide_preview = preview / "safe-zone-guide-360x640.png"
    guide.resize(REDUCED, Image.Resampling.LANCZOS).save(guide_preview, format="PNG", optimize=True)
    preview_files.append(guide_preview)
    all_rows.append({"path": guide_path.name, "kind": "guide", "dimensions": list(SIZE),
                     "mode": "RGBA", "alpha_min": guide.getchannel("A").getextrema()[0],
                     "alpha_max": guide.getchannel("A").getextrema()[1],
                     "sha256": hashlib.sha256(guide_path.read_bytes()).hexdigest(),
                     "bytes": guide_path.stat().st_size, "measurement": guide_measurement})
    sheet = Image.new("RGB", (720, math.ceil(len(preview_files) / 2) * 640), (10, 17, 28))
    for index, p in enumerate(preview_files):
        with Image.open(p) as image:
            sheet.paste(image.convert("RGB"), ((index % 2) * 360, (index // 2) * 640))
    contact = preview / ("sample-contact-360x640.png" if sample_only else "storyboard-contact-360x640.png")
    sheet.save(contact, format="PNG", optimize=True)
    report = {"generator": "build_storyboard.py", "font": FONT_NAME,
              "sample_only": sample_only, "assets": all_rows,
              "preview_contact": contact.name}
    report_path = preview / ("sample-measurements.json" if sample_only else "storyboard-measurements.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"GUIDE_OK {guide_path.name} {SIZE[0]}x{SIZE[1]} RGBA alpha={guide.getchannel('A').getextrema()}")
    print(f"PREVIEW_OK {contact} {sheet.size[0]}x{sheet.size[1]}")


def main() -> None:
    default_output = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--preview-dir", type=Path, required=True,
                        help="Private 360x640 review images and measured bounds")
    parser.add_argument("--sample-only", action="store_true",
                        help="Render the opening, Menu Kit caption and safe-zone guide for early review")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    build(args.output_dir, args.preview_dir, args.sample_only, args.overwrite)


if __name__ == "__main__":
    main()
