"""Build original code-drawn PulseLite Sci-Fi and Horror gallery stills."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZE = (1920, 1080)
SCALE_PREVIEW = (640, 360)
MAX_BYTES = 3_000_000
FONT_NAME = "Pillow built-in Aileron Regular"

THEMES = {
    "sci-fi": {
        "title": "SCI-FI UI SOUNDS",
        "game": "STARWARD",
        "world": "ORBITAL FRONTIER / SECTOR 09",
        "top": (5, 14, 29), "bottom": (11, 31, 48),
        "panel": (14, 35, 54), "panel2": (19, 45, 66),
        "line": (43, 96, 122), "accent": (75, 220, 235),
        "accent2": (136, 183, 255), "paper": (239, 246, 247),
        "muted": (155, 185, 196), "warm": (245, 194, 103),
        "theme_label": "SCI-FI PACK",
    },
    "horror": {
        "title": "HORROR UI SOUNDS",
        "game": "THE HOLLOW",
        "world": "NIGHT WATCH / OLD TOWN",
        "top": (18, 8, 18), "bottom": (39, 13, 24),
        "panel": (37, 17, 27), "panel2": (51, 22, 31),
        "line": (111, 45, 52), "accent": (250, 111, 79),
        "accent2": (205, 101, 111), "paper": (247, 239, 230),
        "muted": (190, 157, 151), "warm": (241, 190, 115),
        "theme_label": "HORROR PACK",
    },
}

SCENES = {
    "sci-fi": [
        {"filename": "04-main-menu.png", "scene": "main-menu", "event": "button_hover", "path": "hover/hover_01.ogg", "selected": "SETTINGS"},
        {"filename": "05-audio-settings.png", "scene": "settings", "event": "toggle_on", "path": "toggle/toggle_01.ogg", "toggle": "on"},
        {"filename": "06-inventory-panel.png", "scene": "inventory", "event": "panel_open", "path": "panel_open/panel_open_04.ogg"},
        {"filename": "07-level-up.png", "scene": "level-up", "event": "level_up", "path": "level_up/level_up_01.ogg"},
    ],
    "horror": [
        {"filename": "04-main-menu.png", "scene": "main-menu", "event": "button_hover", "path": "hover/hover_01.ogg", "selected": "SETTINGS"},
        {"filename": "05-audio-settings.png", "scene": "settings", "event": "toggle_off", "path": "toggle/toggle_02.ogg", "toggle": "off"},
        {"filename": "06-supply-error.png", "scene": "supply-bay", "event": "error", "path": "error/error_01.ogg"},
        {"filename": "07-reward-screen.png", "scene": "reward", "event": "reward", "path": "reward/reward_05.ogg"},
    ],
}


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Pillow 11 bundles Aileron Regular. No Windows font lookup or external asset.
    return ImageFont.load_default(size=size)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
         size: int, fill: tuple[int, int, int], bold: bool = False,
         anchor: str | None = None) -> tuple[int, int, int, int]:
    f = font(size)
    stroke = max(1, size // 42) if bold else 0
    draw.text(xy, value, font=f, fill=fill, anchor=anchor,
              stroke_width=stroke, stroke_fill=fill)
    return draw.textbbox(xy, value, font=f, anchor=anchor, stroke_width=stroke)


def fit_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str,
             max_width: int, preferred_size: int,
             fill: tuple[int, int, int], bold: bool = False) -> tuple[int, int, int, int]:
    size = preferred_size
    while size > 18:
        f = font(size)
        box = draw.textbbox((0, 0), value, font=f,
                            stroke_width=max(1, size // 42) if bold else 0)
        if box[2] - box[0] <= max_width:
            break
        size -= 2
    return text(draw, xy, value, size, fill, bold)


def gradient(theme: dict, height: int) -> Image.Image:
    top, bottom = theme["top"], theme["bottom"]
    strip = Image.new("RGB", (1, height))
    pix = strip.load()
    for y in range(height):
        t = y / max(1, height - 1)
        pix[0, y] = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
    return strip.resize(SIZE, Image.Resampling.BICUBIC)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
            fill: tuple[int, int, int], outline: tuple[int, int, int],
            radius: int = 18, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def background_detail(draw: ImageDraw.ImageDraw, theme: dict, pack: str) -> None:
    accent = theme["accent"]
    if pack == "sci-fi":
        for i in range(11):
            x = 1120 + i * 115
            y = 245 + (i % 3) * 39
            draw.ellipse((x, y, x + 4, y + 4), fill=theme["muted"])
        for radius in (180, 270, 360):
            draw.arc((1410 - radius, 330 - radius, 1410 + radius, 330 + radius),
                     start=210, end=330, fill=theme["line"], width=2)
        draw.line((1030, 885, 1780, 885), fill=theme["line"], width=2)
    else:
        draw.polygon([(1240, 860), (1300, 390), (1390, 310), (1475, 410),
                      (1530, 860)], fill=(28, 10, 20), outline=theme["line"])
        draw.polygon([(1525, 860), (1570, 470), (1660, 390), (1745, 485),
                      (1795, 860)], fill=(31, 10, 21), outline=theme["line"])
        for x, y in ((1350, 560), (1430, 610), (1645, 560), (1710, 630)):
            draw.rectangle((x, y, x + 22, y + 58), fill=(85, 47, 39))
        draw.line((1110, 890, 1800, 890), fill=theme["line"], width=2)
        draw.arc((1400, 270, 1790, 650), 190, 310, fill=accent, width=2)


def header(draw: ImageDraw.ImageDraw, theme: dict) -> None:
    text(draw, (102, 58), "PULSELITE", 34, theme["accent"], True)
    text(draw, (102, 105), "UI SOUND EFFECTS", 22, theme["paper"], True)
    draw.line((102, 151, 1815, 151), fill=theme["line"], width=2)
    rounded(draw, (1460, 56, 1815, 124), theme["panel"], theme["line"], 18, 2)
    text(draw, (1637, 90), theme["theme_label"], 24, theme["paper"], True, "mm")


def draw_button(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str,
                theme: dict, active: bool = False) -> None:
    fill = theme["accent"] if active else theme["panel2"]
    ink = theme["top"] if active else theme["paper"]
    rounded(draw, box, fill, theme["accent"] if active else theme["line"], 14, 3 if active else 2)
    text(draw, (box[0] + 28, (box[1] + box[3]) // 2), label,
         34, ink, True, "lm")
    if active:
        draw.line((box[0] + 10, box[1] + 17, box[0] + 10, box[3] - 17),
                  fill=theme["paper"], width=5)


def menu_scene(draw: ImageDraw.ImageDraw, theme: dict, pack: str, item: dict) -> None:
    rounded(draw, (110, 215, 1060, 892), theme["panel"], theme["line"], 24, 2)
    text(draw, (165, 266), "01 / MAIN MENU", 21, theme["accent"], True)
    text(draw, (165, 315), theme["game"], 64, theme["paper"], True)
    text(draw, (167, 388), theme["world"], 24, theme["muted"], True)
    draw.line((165, 431, 997, 431), fill=theme["line"], width=2)
    labels = ["PLAY", "SETTINGS", "INVENTORY", "QUIT"]
    y = 470
    for label in labels:
        draw_button(draw, (165, y, 930, y + 76), label, theme,
                    active=(label == item.get("selected")))
        y += 91
    text(draw, (165, 850), "EXAMPLE MENU / STATIC ARTWORK", 20, theme["muted"], True)


def settings_scene(draw: ImageDraw.ImageDraw, theme: dict, pack: str, item: dict) -> None:
    rounded(draw, (110, 215, 1060, 892), theme["panel"], theme["line"], 24, 2)
    text(draw, (165, 266), "02 / AUDIO SETTINGS", 21, theme["accent"], True)
    text(draw, (165, 315), "SOUND OPTIONS", 54, theme["paper"], True)
    rows = [("UI SOUNDS", item.get("toggle") == "on"),
            ("AMBIENCE", False)]
    y = 430
    for label, is_on in rows:
        text(draw, (168, y + 29), label, 32, theme["paper"], True, "lm")
        box = (755, y, 958, y + 62)
        rounded(draw, box, theme["accent"] if is_on else theme["panel2"], theme["line"], 31, 2)
        cx = box[2] - 31 if is_on else box[0] + 31
        draw.ellipse((cx - 21, y + 10, cx + 21, y + 52), fill=theme["paper"])
        text(draw, (982, y + 31), "ON" if is_on else "OFF", 18, theme["muted"], True, "lm")
        y += 112
    text(draw, (168, 663), "MASTER VOLUME", 25, theme["muted"], True)
    draw.rounded_rectangle((168, 714, 955, 728), radius=7, fill=theme["line"])
    draw.rounded_rectangle((168, 714, 690, 728), radius=7, fill=theme["accent"])
    draw.ellipse((666, 698, 714, 746), fill=theme["paper"], outline=theme["accent"])
    draw_button(draw, (168, 786, 438, 850), "BACK", theme)


def inventory_scene(draw: ImageDraw.ImageDraw, theme: dict, pack: str, item: dict) -> None:
    rounded(draw, (110, 215, 1060, 892), theme["panel"], theme["line"], 24, 2)
    text(draw, (165, 266), "03 / INVENTORY PANEL", 21, theme["accent"], True)
    text(draw, (165, 315), "INVENTORY", 56, theme["paper"], True)
    labels = ["PULSE CELL", "NOVA KEY", "FIELD MAP", "EMBER SHARD", "RUNE TOKEN", "CORE CHIP"]
    boxes = []
    for i, label in enumerate(labels):
        col, row = i % 3, i // 3
        x, y = 165 + col * 258, 420 + row * 182
        box = (x, y, x + 230, y + 150)
        boxes.append(box)
        rounded(draw, box, theme["panel2"], theme["line"], 16, 2)
        draw.ellipse((x + 23, y + 26, x + 82, y + 85), outline=theme["accent"], width=4)
        draw.polygon([(x + 52, y + 34), (x + 72, y + 57), (x + 52, y + 79), (x + 33, y + 57)],
                     fill=theme["accent2"])
        fit_text(draw, (x + 98, y + 48), label, 116, 22, theme["paper"], True)
        text(draw, (x + 24, y + 117), "SLOT 0" + str(i + 1), 17, theme["muted"], True)
    # A visible open panel rim illustrates the panel-open scene without implying capture.
    draw.rounded_rectangle(boxes[1], radius=16, outline=theme["accent"], width=5)
    text(draw, (165, 818), "STATIC UI EXAMPLE", 20, theme["muted"], True)


def supply_error_scene(draw: ImageDraw.ImageDraw, theme: dict) -> None:
    rounded(draw, (110, 215, 1060, 892), theme["panel"], theme["line"], 24, 2)
    text(draw, (165, 266), "03 / SUPPLY ERROR", 21, theme["accent"], True)
    text(draw, (165, 315), "SUPPLY TERMINAL", 48, theme["paper"], True)
    text(draw, (168, 383), "FIELD KIT REQUEST", 25, theme["muted"], True)
    rounded(draw, (165, 448, 1000, 633), theme["panel2"], theme["line"], 18, 2)
    text(draw, (203, 482), "COST", 19, theme["muted"], True)
    text(draw, (203, 531), "240 CREDITS", 34, theme["paper"], True)
    draw.line((570, 475, 570, 604), fill=theme["line"], width=2)
    text(draw, (615, 482), "AVAILABLE", 19, theme["muted"], True)
    text(draw, (615, 531), "120 CREDITS", 34, theme["paper"], True)
    rounded(draw, (165, 669, 1000, 767), theme["panel"], theme["accent"], 16, 3)
    message = "PURCHASE DENIED - INSUFFICIENT CREDITS"
    message_size = 28
    while message_size > 18:
        candidate = font(message_size)
        bounds = draw.textbbox((0, 0), message, font=candidate,
                               stroke_width=max(1, message_size // 42))
        if bounds[2] - bounds[0] <= 765:
            break
        message_size -= 2
    text(draw, (582, 718), message, message_size, theme["accent"], True, "mm")
    rounded(draw, (323, 805, 806, 862), theme["panel2"], theme["line"], 14, 2)
    text(draw, (565, 834), "RETURN TO SHOP", 22, theme["muted"], True, "mm")


def reward_scene(draw: ImageDraw.ImageDraw, theme: dict, pack: str, item: dict) -> None:
    rounded(draw, (110, 215, 1060, 892), theme["panel"], theme["line"], 24, 2)
    if item["scene"] == "level-up":
        text(draw, (165, 266), "04 / PROGRESSION", 21, theme["accent"], True)
        title = "LEVEL UP"
        sub = "RANK 06  ->  RANK 07"
        motif = theme["warm"]
    else:
        text(draw, (165, 266), "04 / REWARD", 21, theme["accent"], True)
        title = "REWARD CLAIMED"
        sub = "DAILY DROP / SIGNAL CORE"
        motif = theme["accent"]
    text(draw, (185, 397), title, 62, theme["paper"], True)
    text(draw, (188, 486), sub, 27, theme["muted"], True)
    cx, cy = 564, 664
    for r in (110, 82, 52):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=motif, width=3)
    draw.polygon([(cx, cy - 50), (cx + 42, cy), (cx, cy + 50), (cx - 42, cy)], fill=motif)
    rounded(draw, (323, 817, 806, 864), theme["panel2"], theme["line"], 14, 2)
    text(draw, (565, 841), "CONTINUE", 22, theme["paper"], True, "mm")


def event_card(draw: ImageDraw.ImageDraw, theme: dict, item: dict) -> dict:
    x1, y1, x2, y2 = 1110, 215, 1810, 892
    rounded(draw, (x1, y1, x2, y2), theme["panel"], theme["line"], 24, 2)
    text(draw, (1168, 270), "EXAMPLE EVENT MAPPING", 23, theme["accent"], True)
    text(draw, (1168, 335), "EVENT", 19, theme["muted"], True)
    eventbox = fit_text(draw, (1168, 378), item["event"].upper(), 580, 54, theme["paper"], True)
    text(draw, (1168, 472), "SOURCE FILE LABEL", 19, theme["muted"], True)
    pathbox = fit_text(draw, (1168, 515), item["path"], 580, 36, theme["warm"], True)
    draw.line((1168, 595, 1750, 595), fill=theme["line"], width=2)
    # Folder symbol is purely decorative; no sound is embedded or played.
    rounded(draw, (1168, 635, 1278, 718), theme["panel2"], theme["line"], 12, 2)
    draw.rounded_rectangle((1184, 650, 1227, 664), radius=4, fill=theme["accent"])
    draw.rectangle((1184, 662, 1260, 702), fill=theme["accent"])
    text(draw, (1302, 653), "EVENT + FILE LABEL", 23, theme["paper"], True)
    text(draw, (1302, 692), "Still image only; no audio playback", 20, theme["muted"])
    rounded(draw, (1168, 766, 1750, 831), theme["panel2"], theme["line"], 15, 2)
    text(draw, (1459, 799), "ILLUSTRATIVE EXAMPLE", 21, theme["paper"], True, "mm")
    return {"event_bbox": list(eventbox), "path_bbox": list(pathbox),
            "event_max_width": 580, "path_max_width": 580}


def render(pack: str, item: dict) -> tuple[Image.Image, dict]:
    theme = THEMES[pack]
    image = gradient(theme, SIZE[1])
    draw = ImageDraw.Draw(image)
    background_detail(draw, theme, pack)
    header(draw, theme)
    if item["scene"] == "main-menu":
        menu_scene(draw, theme, pack, item)
    elif item["scene"] == "settings":
        settings_scene(draw, theme, pack, item)
    elif item["scene"] == "inventory":
        inventory_scene(draw, theme, pack, item)
    elif item["scene"] == "supply-bay":
        supply_error_scene(draw, theme)
    else:
        reward_scene(draw, theme, pack, item)
    measurements = event_card(draw, theme, item)
    draw.line((102, 932, 1815, 932), fill=theme["line"], width=2)
    left = text(draw, (102, 957), "ILLUSTRATIVE GAME UI - NOT INCLUDED", 32, theme["paper"], True)
    right = text(draw, (1815, 957), "PROCEDURAL DSP AUDIO / AI-ASSISTED VISUALS", 29,
                 theme["muted"], True, "ra")
    measurements.update({"footer_bbox_left": list(left), "footer_bbox_right": list(right),
                         "canvas": list(SIZE), "font": FONT_NAME})
    return image, measurements


def build(output_dir: Path, preview_dir: Path, sample_only: bool, overwrite: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    tasks = [(pack, item) for pack in ("sci-fi", "horror")
             for item in (SCENES[pack][:1] if sample_only else SCENES[pack])]
    reports = []
    contact = Image.new("RGB", (1280, math.ceil(len(tasks) / 2) * 360), (8, 14, 25))
    for index, (pack, item) in enumerate(tasks):
        pack_dir = output_dir / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        target = pack_dir / item["filename"]
        if target.exists() and not overwrite:
            raise FileExistsError(f"Refusing to replace existing gallery image without --overwrite: {target.name}")
        image, measures = render(pack, item)
        image.save(target, format="PNG", optimize=True, compress_level=9)
        size = target.stat().st_size
        if size >= MAX_BYTES:
            raise ValueError(f"{target.name} exceeds the 3,000,000-byte limit: {size}")
        preview_path = preview_dir / f"{pack}-{item['filename'].removesuffix('.png')}-640x360.png"
        image.resize(SCALE_PREVIEW, Image.Resampling.LANCZOS).save(preview_path, format="PNG", optimize=True)
        with Image.open(preview_path) as preview:
            contact.paste(preview.convert("RGB"), ((index % 2) * 640, (index // 2) * 360))
        reports.append({"pack": pack, "path": f"{pack}/{item['filename']}",
                        "scene": item["scene"], "event": item["event"],
                        "source_label": item["path"], "dimensions": list(SIZE),
                        "bytes": size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "preview": preview_path.name, "measurements": measures})
        print(f"ASSET_OK {pack}/{target.name} {SIZE[0]}x{SIZE[1]} {size} bytes")
    contact_path = preview_dir / "sample-contact-640.png"
    contact.save(contact_path, format="PNG", optimize=True)
    report_path = preview_dir / ("sample-measurements.json" if sample_only else "gallery-measurements.json")
    report_path.write_text(json.dumps({"generator": "build_theme_gallery.py", "font": FONT_NAME,
                                      "sample_only": sample_only, "assets": reports},
                                     indent=2) + "\n", encoding="utf-8")
    print(f"CONTACT_OK {contact_path.name} {contact.size[0]}x{contact.size[1]}")
    print(f"MEASUREMENTS {report_path}")


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=repo / "marketing/gallery")
    parser.add_argument("--preview-dir", type=Path, required=True,
                        help="Private directory for 640x360 reviews and measured text bounds")
    parser.add_argument("--sample-only", action="store_true",
                        help="Render only the first new still for Sci-Fi and Horror for visual review")
    parser.add_argument("--overwrite", action="store_true",
                        help="Allow replacement of the specifically named generated PNGs")
    args = parser.parse_args()
    build(args.output_dir, args.preview_dir, args.sample_only, args.overwrite)


if __name__ == "__main__":
    main()
