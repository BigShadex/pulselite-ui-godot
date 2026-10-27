#!/usr/bin/env python3
"""Render review stills for the PulseLite video redo.

All screens are drawn from primitives here. No Godot capture, screenshot, or
third-party game art is used. The generated review frames are separate from the
canonical video files and are intended for internal visual approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


LANDSCAPE = (1920, 1080)
PORTRAIT = (1080, 1920)
REGULAR_FONT = Path("C:/Windows/Fonts/arial.ttf")
BOLD_FONT = Path("C:/Windows/Fonts/arialbd.ttf")

PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "menu-kit": {
        "top": (9, 15, 29), "bottom": (13, 27, 47), "panel": (14, 25, 42),
        "panel2": (19, 34, 54), "stroke": (42, 73, 98), "accent": (47, 218, 245),
        "accent2": (255, 196, 89), "text": (244, 248, 250), "muted": (155, 176, 192),
        "danger": (255, 114, 106), "button": (18, 34, 53), "glow": (13, 78, 109),
    },
    "sci-fi": {
        "top": (5, 13, 25), "bottom": (9, 22, 40), "panel": (10, 24, 42),
        "panel2": (13, 33, 55), "stroke": (32, 79, 111), "accent": (60, 225, 255),
        "accent2": (171, 246, 255), "text": (241, 250, 255), "muted": (142, 179, 198),
        "danger": (255, 111, 91), "button": (11, 30, 50), "glow": (6, 94, 139),
    },
    "horror": {
        "top": (18, 10, 17), "bottom": (30, 13, 20), "panel": (27, 16, 22),
        "panel2": (39, 22, 28), "stroke": (100, 48, 47), "accent": (255, 105, 79),
        "accent2": (242, 192, 112), "text": (249, 241, 229), "muted": (193, 164, 151),
        "danger": (255, 82, 78), "button": (34, 19, 25), "glow": (116, 39, 35),
    },
}

PACK_NAMES = {"menu-kit": "MENU KIT", "sci-fi": "SCI-FI", "horror": "HORROR"}
PRODUCT_PATHS = {
    "menu-kit": "/pulselite-ui-sfx",
    "sci-fi": "/pulselite-scifi-ui",
    "horror": "/pulselite-horror-ui",
}
PREVIEWER_PATH = "/pulselite-previewer/"

EVENTS: dict[str, tuple[str, str]] = {
    "button_click": ("click", "click_03.ogg"),
    "button_hover": ("hover", "hover_01.ogg"),
    "toggle_on": ("toggle", "toggle_01.ogg"),
    "toggle_off": ("toggle", "toggle_02.ogg"),
    "menu_confirm": ("confirm", "confirm_05.ogg"),
    "menu_back": ("back_cancel", "back_cancel_01.ogg"),
    "error": ("error", "error_01.ogg"),
    "notification": ("notify", "notify_02.ogg"),
    "panel_open": ("panel_open", "panel_open_04.ogg"),
    "panel_close": ("panel_close", "panel_close_05.ogg"),
    "transition": ("whoosh", "whoosh_06.ogg"),
    "coin_pickup": ("coin", "coin_01.ogg"),
    "reward": ("reward", "reward_05.ogg"),
    "level_up": ("level_up", "level_up_01.ogg"),
}

# The paid Menu Kit events and filenames are taken in the order of the existing
# played-events receipt. These times give the 60-second edit a deterministic map.
MENU_TIMES = [1989, 6164, 8628, 12118, 16639, 19236, 22804, 26259,
              29846, 34162, 37005, 40431, 44026, 47590]
MENU_ORDER = [
    "button_click", "button_hover", "toggle_on", "toggle_off", "menu_confirm",
    "menu_back", "error", "notification", "panel_open", "panel_close",
    "transition", "coin_pickup", "reward", "level_up",
]

MENU_CUTS = [
    {"start_ms": 0, "end_ms": 8628, "scene": "hook/menu"},
    {"start_ms": 8628, "end_ms": 16639, "scene": "settings"},
    {"start_ms": 16639, "end_ms": 22804, "scene": "menu"},
    {"start_ms": 22804, "end_ms": 29846, "scene": "shop/notification"},
    {"start_ms": 29846, "end_ms": 37005, "scene": "inventory"},
    {"start_ms": 37005, "end_ms": 44026, "scene": "gameplay"},
    {"start_ms": 44026, "end_ms": 47590, "scene": "reward"},
    {"start_ms": 47590, "end_ms": 55000, "scene": "level-up"},
    {"start_ms": 55000, "end_ms": 60000, "scene": "endcard"},
]

THEME_CUTS = [
    {"start_ms": 0, "end_ms": 2700, "scene": "hook/menu"},
    {"start_ms": 2700, "end_ms": 6900, "scene": "menu"},
    {"start_ms": 6900, "end_ms": 8500, "scene": "gameplay"},
    {"start_ms": 8500, "end_ms": 10500, "scene": "inventory"},
    {"start_ms": 10500, "end_ms": 12300, "scene": "gameplay"},
    {"start_ms": 12300, "end_ms": 14000, "scene": "inventory"},
    {"start_ms": 14000, "end_ms": 18400, "scene": "settings"},
    {"start_ms": 18400, "end_ms": 22200, "scene": "shop"},
    {"start_ms": 22200, "end_ms": 24400, "scene": "reward"},
    {"start_ms": 24400, "end_ms": 26000, "scene": "level-up"},
    {"start_ms": 26000, "end_ms": 30000, "scene": "endcard"},
]

THEME_TIMELINE = [
    (2700, "button_hover", "menu", "PLAY"),
    (3500, "button_click", "menu", "PLAY"),
    (4300, "menu_confirm", "menu", "PLAY"),
    (6900, "transition", "gameplay", "HANGAR"),
    (8500, "panel_open", "inventory", "LOADOUT"),
    (10500, "coin_pickup", "gameplay", "SIGNAL CELL"),
    (12300, "panel_close", "inventory", "LOADOUT"),
    (14000, "toggle_on", "settings", "UI SOUND"),
    (15400, "toggle_off", "settings", "AMBIENCE"),
    (16800, "menu_back", "settings", "BACK"),
    (18400, "error", "shop", "LOCKED ITEM"),
    (20100, "notification", "shop", "NEW MESSAGE"),
    (22200, "reward", "reward", "CLAIM REWARD"),
    (24400, "level_up", "level-up", "LEVEL UP"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = BOLD_FONT if bold else REGULAR_FONT
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0], box[3] - box[1]


def centered_text(draw: ImageDraw.ImageDraw, cx: int, y: int, text: str,
                  f: ImageFont.ImageFont, fill: tuple[int, int, int]) -> None:
    w, _ = text_size(draw, text, f)
    draw.text((cx - w // 2, y), text, font=f, fill=fill)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int,
            fill: tuple[int, int, int] | None, outline: tuple[int, int, int] | None = None,
            width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def gradient(size: tuple[int, int], palette: dict[str, tuple[int, int, int]]) -> Image.Image:
    w, h = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    a, b = palette["top"], palette["bottom"]
    for y in range(h):
        t = y / max(1, h - 1)
        color = tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))
        draw.line((0, y, w, y), fill=color)
    return image


def draw_backdrop(image: Image.Image, pack: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    p = PALETTES[pack]
    w, h = image.size
    if pack == "sci-fi":
        rng = random.Random(9917)
        for _ in range(150):
            x, y = rng.randrange(w), rng.randrange(h)
            r = rng.choice((1, 1, 2, 3))
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(185, 229, 247, rng.randrange(50, 150)))
        # A large orbital arc and distant planet create depth without borrowing art.
        draw.ellipse((1370, 190, 1860, 680), fill=(11, 60, 87, 80), outline=(*p["accent"], 75), width=4)
        draw.ellipse((1440, 260, 1790, 610), fill=(9, 32, 51, 170), outline=(*p["accent2"], 42), width=2)
        for x in range(0, w, 160):
            draw.line((x, 700, x + 150, 1080), fill=(*p["accent"], 10), width=1)
    elif pack == "horror":
        # Flat haunted-estate silhouettes are drawn for this concept; no stock art.
        draw.ellipse((1390, 150, 1750, 510), fill=(150, 54, 41, 35))
        draw.polygon([(1270, 650), (1270, 430), (1400, 320), (1500, 430),
                      (1500, 650), (1640, 650), (1640, 470), (1780, 350),
                      (1900, 470), (1900, 740), (1270, 740)],
                     fill=(9, 9, 14, 190), outline=(*p["accent"], 45))
        for wx, wy in ((1365, 500), (1515, 500), (1715, 505), (1810, 505)):
            draw.rectangle((wx, wy, wx + 36, wy + 65), fill=(*p["accent2"], 90))
        rng = random.Random(441)
        for x in range(40, w, 150):
            height = rng.randrange(60, 185)
            draw.line((x, h, x + rng.randrange(-40, 40), h - height), fill=(0, 0, 0, 165), width=15)
    else:
        # A restrained geometric wave motif establishes a neutral Menu Kit world.
        for i in range(6):
            y = 560 + i * 58
            draw.arc((-260, y - 100, 1120, y + 500), 190, 344,
                     fill=(*p["accent"], max(12, 56 - i * 7)), width=3)
        draw.ellipse((1485, 260, 1815, 590), fill=(25, 84, 112, 40), outline=(*p["accent"], 50), width=3)
    # A narrow frame line gives the mock screen a deliberate edge.
    draw.rounded_rectangle((32, 28, w - 32, h - 28), radius=22,
                           outline=(*p["stroke"], 145), width=2)


def draw_header(image: Image.Image, pack: str) -> None:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    draw.rectangle((64, 50, 1856, 138), fill=(*p["top"],))
    draw.line((64, 138, 1856, 138), fill=p["stroke"], width=2)
    rounded(draw, (90, 68, 116, 94), 6, p["accent"])
    draw.text((132, 58), "PULSELITE", font=font(39, True), fill=p["text"])
    draw.text((352, 71), "UI SOUND EFFECTS", font=font(22, True), fill=p["muted"])
    right = f"{PACK_NAMES[pack]}  /  ILLUSTRATIVE GAME UI"
    rw, _ = text_size(draw, right, font(23, True))
    draw.text((1830-rw, 73), right, font=font(23, True), fill=p["muted"])


def caption_for(event: str, filename: str) -> str:
    return f"{event}  →  {filename}"


def draw_footer(image: Image.Image, pack: str, event: str | None,
                filename: str | None, disclosure: bool = True) -> tuple[int, int, int, int]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    draw.rectangle((64, 850, 1856, 1080), fill=(5, 10, 18))
    draw.line((64, 850, 1856, 850), fill=p["stroke"], width=2)
    cue = "" if event is None or filename is None else caption_for(event, filename)
    if cue:
        rounded(draw, (115, 878, 1805, 965), 16, p["panel2"], p["stroke"], 2)
        draw.rectangle((115, 878, 125, 965), fill=p["accent"])
        centered_text(draw, 960, 890, cue, font(52, True), p["text"])
    if disclosure:
        centered_text(draw, 960, 981, "Illustrative menus — not included",
                      font(36, True), p["muted"])
        centered_text(draw, 960, 1026,
                      "SOURCE OGG AUDIO  •  PROCEDURAL DSP  •  AI-ASSISTED CODE, VIDEO & TEXT",
                      font(34, True), p["muted"])
    return (115, 878, 1805, 965) if cue else (64, 850, 1856, 1080)


def draw_hero_title(draw: ImageDraw.ImageDraw, pack: str, title: str = "STARWARD") -> None:
    p = PALETTES[pack]
    centered_text(draw, 960, 163, title, font(65, True), p["text"])
    centered_text(draw, 960, 236, "MAIN MENU  /  BUILD 07", font(23, True), p["muted"])


def draw_button(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str,
                pack: str, selected: bool = False, trailing: str = "",
                label_size: int = 72) -> None:
    p = PALETTES[pack]
    x1, y1, x2, y2 = box
    rounded(draw, box, 14, p["button"], p["text"] if selected else p["stroke"], 4 if selected else 2)
    if selected:
        draw.rounded_rectangle((x1, y1, x1 + 11, y2), radius=5, fill=p["accent"])
    label_font = font(label_size, True)
    _, label_height = text_size(draw, label, label_font)
    draw.text((x1 + 34, y1 + (y2-y1-label_height)//2 - 2), label,
              font=label_font, fill=p["text"])
    if trailing:
        tw, th = text_size(draw, trailing, font(22, True))
        draw.text((x2 - tw - 26, y1 + (y2-y1-th)//2 - 2), trailing,
                  font=font(22, True), fill=p["muted"])


def draw_main_menu(image: Image.Image, pack: str, portrait: bool = False,
                   hook: bool = False) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    if not portrait:
        if hook:
            # Large product name lands immediately while the game menu remains visible.
            centered_text(draw, 960, 146, "PULSELITE", font(94, True), p["text"])
            centered_text(draw, 960, 246, "UI SOUND EFFECTS  /  ILLUSTRATIVE GAME MENU",
                          font(25, True), p["accent"])
        else:
            draw_hero_title(draw, pack, {"menu-kit": "NIGHT MARKET", "sci-fi": "STARWARD",
                                         "horror": "THE HOLLOW"}[pack])
        # The central game menu remains the dominant object, with large active outline.
        panel = (480, 300, 1440, 815)
        rounded(draw, panel, 24, p["panel"], p["stroke"], 2)
        panel_title = ({"menu-kit": "NIGHT MARKET  /  MAIN MENU", "sci-fi": "STARWARD  /  MAIN MENU",
                        "horror": "THE HOLLOW  /  MAIN MENU"}[pack] if hook else "MAIN MENU")
        draw.text((545, 328), panel_title, font=font(26, True), fill=p["accent"])
        btn_boxes = [(610, 390 + i*96, 1310, 480 + i*96) for i in range(4)]
        for i, name in enumerate(("PLAY", "SETTINGS", "INVENTORY", "QUIT")):
            draw_button(draw, btn_boxes[i], name, pack, selected=(i == 0),
                        trailing="ENTER" if i == 0 else "")
        # Small game-world card: visual texture, not a second dashboard.
        rounded(draw, (110, 385, 408, 702), 20, p["panel"], p["stroke"], 2)
        draw.text((144, 420), "MISSION 01", font=font(22, True), fill=p["muted"])
        draw.text((144, 473), "THE", font=font(22, True), fill=p["muted"])
        draw.text((144, 509), {"menu-kit":"NIGHT", "sci-fi":"OUTER", "horror":"OLD"}[pack],
                  font=font(38, True), fill=p["text"])
        draw.text((144, 555), {"menu-kit":"MARKET", "sci-fi":"RIM", "horror":"HOUSE"}[pack],
                  font=font(38, True), fill=p["text"])
        draw.line((144, 620, 365, 620), fill=p["stroke"], width=2)
        draw.text((144, 645), "READY  /  3 ITEMS", font=font(18, True), fill=p["accent2"])
        return {"main_panel": panel, "button_play": btn_boxes[0], "button_settings": btn_boxes[1]}
    # Native 9:16 composition. Content stays inside the central Shorts-safe area.
    draw.rectangle((0, 0, 1080, 1920), fill=(0, 0, 0, 0))
    # Remove landscape-only footer and header; the portrait layout owns its hierarchy.
    draw.rectangle((0, 0, 1080, 1920), fill=p["top"])
    # Keep the motif deliberately simple so stacked controls read at phone size.
    if pack == "sci-fi":
        draw.ellipse((575, 245, 955, 625), outline=(*p["accent"],), width=5)
        draw.ellipse((620, 290, 910, 580), outline=p["stroke"], width=2)
    elif pack == "horror":
        draw.ellipse((620, 230, 930, 540), fill=(103, 35, 34), outline=p["accent"], width=4)
    else:
        for y in (350, 430, 510):
            draw.arc((190, y, 900, y+400), 190, 350, fill=p["stroke"], width=4)
    rounded(draw, (90, 98, 428, 154), 15, p["panel2"], p["stroke"], 2)
    draw.text((116, 111), "PULSELITE  /  UI SOUNDS", font=font(23, True), fill=p["text"])
    rounded(draw, (626, 98, 990, 154), 15, p["panel2"], p["stroke"], 2)
    right = f"{PACK_NAMES[pack]}  •  DEMO"
    tw, _ = text_size(draw, right, font(20, True))
    draw.text((808-tw//2, 116), right, font=font(20, True), fill=p["muted"])
    centered_text(draw, 540, 215, {"menu-kit":"NIGHT MARKET", "sci-fi":"STARWARD",
                                    "horror":"THE HOLLOW"}[pack], font(58, True), p["text"])
    centered_text(draw, 540, 292, "MAIN MENU", font(24, True), p["muted"])
    panel = (90, 690, 990, 1312)
    rounded(draw, panel, 26, p["panel"], p["stroke"], 2)
    labels = ("PLAY", "SETTINGS", "INVENTORY", "QUIT")
    boxes = []
    for i, name in enumerate(labels):
        box = (150, 750 + i*130, 930, 850 + i*130)
        boxes.append(box)
        draw_button(draw, box, name, pack, selected=(i == 0), trailing="ENTER" if i == 0 else "",
                    label_size=50)
    return {"main_panel": panel, "button_play": boxes[0], "button_settings": boxes[1]}


def draw_settings(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    panel = (420, 262, 1500, 820)
    rounded(draw, panel, 24, p["panel"], p["stroke"], 2)
    draw.text((485, 302), "SETTINGS", font=font(55, True), fill=p["text"])
    draw.text((490, 377), "AUDIO", font=font(24, True), fill=p["accent"])
    for idx, (label, state) in enumerate((("UI SOUND", "ON"), ("AMBIENCE", "OFF"))):
        y = 440 + idx*138
        draw.text((500, y+15), label, font=font(34, True), fill=p["text"])
        toggle = (1130, y, 1370, y+76)
        rounded(draw, toggle, 38, p["accent"] if state == "ON" else p["panel2"],
                p["accent"] if state == "ON" else p["stroke"], 3)
        cx = 1323 if state == "ON" else 1176
        draw.ellipse((cx-25, y+13, cx+25, y+63), fill=p["text"])
        draw.text((1390, y+22), state, font=font(22, True), fill=p["muted"])
    draw.text((500, 722), "MASTER VOLUME", font=font(22, True), fill=p["muted"])
    draw.rounded_rectangle((775, 730, 1330, 748), radius=9, fill=p["stroke"])
    draw.rounded_rectangle((775, 730, 1160, 748), radius=9, fill=p["accent"])
    draw.ellipse((1145, 716, 1175, 762), fill=p["text"])
    return {"settings_panel": panel, "toggle_ui": (1130, 440, 1370, 516), "toggle_ambience": (1130, 578, 1370, 654)}


def draw_shop(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    panel = (270, 255, 1650, 820)
    rounded(draw, panel, 24, p["panel"], p["stroke"], 2)
    draw.text((340, 293), "SUPPLY BAY", font=font(54, True), fill=p["text"])
    draw.text((1320, 310), "DAILY DROP  /  1 AVAILABLE", font=font(22, True), fill=p["muted"])
    labels = ["FIELD KIT", "NIGHT LENS", "SIGNAL BOOST"]
    badges = ["OWNED", "LOCKED", "NEW"]
    card_boxes = []
    for i, label in enumerate(labels):
        x = 340 + i*415
        box = (x, 390, x+360, 735)
        card_boxes.append(box)
        rounded(draw, box, 20, p["panel2"], p["stroke"], 2)
        draw.ellipse((x+116, 420, x+244, 548), fill=(*p["glow"],), outline=p["accent"], width=3)
        if i == 0:
            draw.rectangle((x+150, 450, x+210, 520), outline=p["accent2"], width=4)
        elif i == 1:
            draw.polygon([(x+180, 438), (x+223, 496), (x+180, 532), (x+137, 496)], outline=p["accent2"], fill=None)
        else:
            draw.line((x+180, 440, x+180, 530), fill=p["accent2"], width=5)
            draw.line((x+137, 485, x+223, 485), fill=p["accent2"], width=5)
        centered_text(draw, x+180, 575, label, font(25, True), p["text"])
        badge_color = p["danger"] if badges[i] == "LOCKED" else p["accent"]
        rounded(draw, (x+62, 637, x+298, 692), 13, p["button"], badge_color, 2)
        centered_text(draw, x+180, 650, badges[i], font(22, True), badge_color)
    return {"shop_panel": panel, "shop_cards": card_boxes}


def draw_inventory(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    panel = (300, 245, 1620, 820)
    rounded(draw, panel, 24, p["panel"], p["stroke"], 2)
    draw.text((366, 286), "INVENTORY", font=font(52, True), fill=p["text"])
    draw.text((1335, 307), "LOADOUT  /  03 OF 08", font=font(21, True), fill=p["muted"])
    names = ["PULSE CELL", "NOVA KEY", "FIELD MAP", "EMBER SHARD", "RUNE TOKEN", "CORE CHIP"]
    slots = []
    colors = [p["accent"], p["accent2"], p["muted"], p["danger"], p["accent2"], p["accent"]]
    for i, name in enumerate(names):
        col, row = i % 3, i // 3
        x, y = 370 + col*390, 370 + row*205
        box = (x, y, x+340, y+170)
        slots.append(box)
        rounded(draw, box, 16, p["panel2"], p["stroke"], 2)
        draw.rounded_rectangle((x+20, y+20, x+100, y+100), radius=14,
                               fill=p["button"], outline=colors[i], width=3)
        if i % 3 == 0:
            draw.polygon([(x+60, y+35), (x+82, y+60), (x+60, y+85), (x+38, y+60)],
                         fill=colors[i])
        elif i % 3 == 1:
            draw.ellipse((x+40, y+40, x+80, y+80), outline=colors[i], width=5)
            draw.line((x+60, y+37, x+60, y+83), fill=colors[i], width=3)
        else:
            draw.rectangle((x+40, y+40, x+80, y+80), outline=colors[i], width=4)
        draw.text((x+118, y+42), name, font=font(21, True), fill=p["text"])
        draw.text((x+118, y+75), f"SLOT 0{i+1}", font=font(17, True), fill=p["muted"])
    return {"inventory_panel": panel, "inventory_slots": slots}


def draw_level_up(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    # A celebratory screen remains game-like and highly legible.
    cx, cy = 960, 520
    for length, alpha, width in ((440, 95, 3), (330, 75, 2), (220, 65, 2)):
        draw.ellipse((cx-length, cy-length, cx+length, cy+length), outline=(*p["accent2"], alpha), width=width)
    rounded(draw, (390, 255, 1530, 808), 30, p["panel"], p["accent2"], 3)
    centered_text(draw, 960, 340, "LEVEL UP", font(112, True), p["accent2"])
    centered_text(draw, 960, 485, "RANK 06  →  RANK 07", font(38, True), p["text"])
    rounded(draw, (630, 585, 1290, 700), 20, p["panel2"], p["stroke"], 2)
    centered_text(draw, 960, 614, "NEW LOADOUT SLOT", font(33, True), p["accent"])
    return {"level_up_panel": (390, 255, 1530, 808)}


def draw_gameplay(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    viewport = (210, 235, 1710, 820)
    rounded(draw, viewport, 28, p["panel"], p["accent"], 3)
    draw.text((270, 270), "FIELD RUN  /  STAGE 04", font=font(27, True), fill=p["text"])
    # A simple vector play scene conveys a game-state cut rather than a dashboard.
    draw.rectangle((245, 335, 1675, 760), fill=(6, 13, 22))
    draw.ellipse((1180, 365, 1510, 695), fill=(*p["glow"],))
    draw.ellipse((1225, 405, 1465, 645), outline=p["accent2"], width=3)
    if pack == "horror":
        draw.polygon([(245, 760), (245, 560), (475, 390), (710, 560), (710, 760)],
                     fill=(18, 12, 19), outline=p["stroke"])
        for wx in (350, 500, 610):
            draw.rectangle((wx, 590, wx+40, 655), fill=p["accent2"])
    elif pack == "sci-fi":
        draw.polygon([(245, 760), (245, 685), (430, 630), (730, 688),
                      (980, 635), (1260, 686), (1675, 640), (1675, 760)],
                     fill=(9, 28, 45), outline=p["stroke"])
    else:
        draw.polygon([(245, 760), (245, 700), (490, 660), (760, 705),
                      (1060, 650), (1360, 710), (1675, 665), (1675, 760)],
                     fill=(11, 27, 39), outline=p["stroke"])
    # Player marker and pickup target.
    draw.polygon([(880, 655), (960, 510), (1040, 655)], fill=p["accent"], outline=p["text"])
    draw.line((960, 585, 960, 670), fill=p["text"], width=4)
    draw.ellipse((1355, 485, 1425, 555), fill=p["accent2"], outline=p["text"], width=3)
    # Simple HUD: one top bar and one clear item toast.
    rounded(draw, (285, 350, 580, 415), 14, p["panel2"], p["stroke"], 2)
    draw.text((308, 370), "HP  88 / 100", font=font(22, True), fill=p["text"])
    rounded(draw, (1295, 660, 1620, 725), 14, p["panel2"], p["accent2"], 2)
    centered_text(draw, 1457, 678, "+1 SIGNAL CELL", font(20, True), p["accent2"])
    return {"gameplay_viewport": viewport, "pickup_toast": (1295, 660, 1620, 725)}


def draw_reward(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    panel = (450, 245, 1470, 820)
    rounded(draw, panel, 30, p["panel"], p["accent2"], 3)
    centered_text(draw, 960, 295, "REWARD CLAIMED", font(62, True), p["text"])
    centered_text(draw, 960, 378, "DAILY DROP", font(25, True), p["muted"])
    rounded(draw, (765, 440, 1155, 650), 25, p["panel2"], p["accent2"], 3)
    draw.ellipse((885, 466, 1035, 616), fill=(*p["glow"],), outline=p["accent2"], width=4)
    draw.polygon([(960, 482), (1008, 540), (960, 598), (912, 540)],
                 fill=p["accent2"], outline=p["text"])
    centered_text(draw, 960, 682, "SIGNAL CORE  /  ADDED TO INVENTORY", font(23, True), p["accent"])
    return {"reward_panel": panel, "reward_item": (765, 440, 1155, 650)}


def draw_endcard(image: Image.Image, pack: str) -> dict[str, tuple[int, int, int, int]]:
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    centered_text(draw, 960, 128, "PULSELITE", font(108, True), p["text"])
    centered_text(draw, 960, 250, f"{PACK_NAMES[pack]}  /  UI SOUND EFFECTS", font(46, True), p["accent"])
    centered_text(draw, 960, 340, "GET THIS PACK", font(31, True), p["muted"])
    rounded(draw, (280, 396, 1640, 572), 20, p["panel"], p["stroke"], 2)
    centered_text(draw, 960, 410, "bigshadex.itch.io", font(38, True), p["accent"])
    centered_text(draw, 960, 466, PRODUCT_PATHS[pack], font(52, True), p["text"])
    rounded(draw, (280, 602, 1640, 778), 20, p["panel"], p["stroke"], 2)
    centered_text(draw, 960, 614, "bigshadex.github.io", font(36, True), p["accent"])
    centered_text(draw, 960, 666, PREVIEWER_PATH, font(48, True), p["text"])
    centered_text(draw, 960, 845, "Illustrative menus — not included", font(38, True), p["muted"])
    centered_text(draw, 960, 904, "PROCEDURAL DSP AUDIO  •  SOURCE OGG", font(36, True), p["muted"])
    centered_text(draw, 960, 958, "AI-ASSISTED CODE, VIDEO & TEXT", font(36, True), p["muted"])
    return {"product_link": (280, 396, 1640, 572),
            "preview_link": (280, 602, 1640, 778),
            "disclosures": (260, 845, 1660, 1005)}


def draw_portrait_settings(image: Image.Image, pack: str, event: str, filename: str) -> dict[str, tuple[int, int, int, int]]:
    p = PALETTES[pack]
    image.paste(gradient(PORTRAIT, p))
    draw_backdrop_portrait(image, pack)
    draw = ImageDraw.Draw(image)
    rounded(draw, (80, 90, 900, 158), 16, p["panel2"], p["stroke"], 2)
    draw.text((110, 108), f"PULSELITE  /  {PACK_NAMES[pack]}", font=font(27, True), fill=p["text"])
    centered_text(draw, 490, 248, "SETTINGS", font(64, True), p["text"])
    centered_text(draw, 490, 332, "AUDIO", font(28, True), p["accent"])
    panel = (90, 485, 890, 1125)
    rounded(draw, panel, 28, p["panel"], p["stroke"], 2)
    for i, (label, state) in enumerate((("UI SOUND", "ON"), ("AMBIENCE", "OFF"))):
        y = 590 + i*210
        draw.text((130, y+35), label, font=font(35, True), fill=p["text"])
        box = (555, y, 850, y+100)
        rounded(draw, box, 48, p["accent"] if state == "ON" else p["panel2"], p["stroke"], 2)
        cx = 812 if state == "ON" else 593
        draw.ellipse((cx-34, y+16, cx+34, y+84), fill=p["text"])
        draw.text((575, y+112), state, font=font(22, True), fill=p["muted"])
    rounded(draw, (160, 1040, 820, 1120), 16, p["button"], p["accent"], 3)
    centered_text(draw, 490, 1060, "BACK", font(30, True), p["text"])
    cbox = draw_portrait_footer(draw, pack, event, filename)
    return {"settings_panel": panel, "caption": cbox}


def draw_backdrop_portrait(image: Image.Image, pack: str) -> None:
    p = PALETTES[pack]
    draw = ImageDraw.Draw(image, "RGBA")
    if pack == "sci-fi":
        for i in range(50):
            x = (i*173 + 61) % 1080
            y = (i*311 + 180) % 1920
            draw.ellipse((x, y, x+2, y+2), fill=(*p["accent2"], 115))
        draw.ellipse((670, 190, 1030, 550), outline=(*p["accent"], 70), width=4)
    elif pack == "horror":
        draw.ellipse((680, 180, 1010, 510), fill=(142, 49, 38, 42))
        draw.polygon([(695, 650), (715, 430), (830, 340), (940, 430), (965, 690)],
                     fill=(0, 0, 0, 125), outline=(*p["accent"], 50))
    else:
        for y in (320, 410, 500):
            draw.arc((120, y, 940, y+460), 195, 350, fill=(*p["accent"], 40), width=3)
    draw.rounded_rectangle((32, 28, 1048, 1892), radius=25,
                           outline=(*p["stroke"], 140), width=2)


def draw_portrait_footer(draw: ImageDraw.ImageDraw, pack: str, event: str | None,
                         filename: str | None) -> tuple[int, int, int, int] | None:
    p = PALETTES[pack]
    if event is not None and filename is not None:
        draw.line((80, 1196, 900, 1196), fill=p["stroke"], width=2)
        rounded(draw, (80, 1208, 900, 1358), 20, p["panel2"], p["stroke"], 2)
        draw.rectangle((80, 1208, 91, 1358), fill=p["accent"])
        cue = caption_for(event, filename)
        # Two lines keep the exact event and basename clear at 360x640.
        parts = cue.split("  →  ")
        centered_text(draw, 490, 1218, parts[0], font(42, True), p["text"])
        centered_text(draw, 490, 1270, "→  " + parts[1], font(42, True), p["text"])
        notice_y = (1370, 1412, 1454)
        caption = (80, 1208, 900, 1358)
    else:
        # The opening hook has no premature cue caption or empty caption band.
        notice_y = (1300, 1342, 1384)
        caption = None
    centered_text(draw, 490, notice_y[0], "ILLUSTRATIVE MENUS — NOT INCLUDED",
                  font(36, True), p["muted"])
    centered_text(draw, 490, notice_y[1], "PROCEDURAL DSP AUDIO • SOURCE OGG",
                  font(36, True), p["muted"])
    centered_text(draw, 490, notice_y[2], "AI-ASSISTED CODE, VIDEO & TEXT",
                  font(36, True), p["muted"])
    return caption


def draw_portrait_menu(image: Image.Image, pack: str, event: str | None,
                       filename: str | None, hook: bool = False) -> dict[str, tuple[int, int, int, int] | None]:
    image.paste(gradient(PORTRAIT, PALETTES[pack]))
    draw_backdrop_portrait(image, pack)
    draw = ImageDraw.Draw(image)
    p = PALETTES[pack]
    rounded(draw, (80, 90, 900, 158), 16, p["panel2"], p["stroke"], 2)
    draw.text((110, 108), f"PULSELITE  /  {PACK_NAMES[pack]} DEMO", font=font(27, True), fill=p["text"])
    game_title = {"menu-kit":"NIGHT MARKET", "sci-fi":"STARWARD", "horror":"THE HOLLOW"}[pack]
    if hook:
        centered_text(draw, 490, 196, "PULSELITE", font(82, True), p["text"])
        centered_text(draw, 490, 294, "UI SOUND EFFECTS", font(36, True), p["accent"])
        centered_text(draw, 490, 386, game_title, font(48, True), p["text"])
        centered_text(draw, 490, 446, "MAIN MENU", font(24, True), p["muted"])
    else:
        centered_text(draw, 490, 248, game_title, font(62, True), p["text"])
        centered_text(draw, 490, 330, "MAIN MENU", font(28, True), p["muted"])
    # 800px-wide stacked controls sit inside the 820px Shorts-safe area.
    panel = (90, 560, 890, 1190)
    rounded(draw, panel, 28, p["panel"], p["stroke"], 2)
    button_boxes = []
    for i, label in enumerate(("PLAY", "SETTINGS", "INVENTORY", "QUIT")):
        box = (100, 590 + i*145, 880, 730 + i*145)
        button_boxes.append(box)
        draw_button(draw, box, label, pack, selected=(i == 0), trailing="ENTER" if i == 0 else "",
                    label_size=50)
    cbox = draw_portrait_footer(draw, pack, event, filename)
    result = {"main_panel": panel, "button_play": button_boxes[0]}
    if cbox is not None:
        result["caption"] = cbox
    return result


def draw_portrait_endcard(image: Image.Image) -> dict[str, tuple[int, int, int, int] | None]:
    pack = "menu-kit"
    p = PALETTES[pack]
    image.paste(gradient(PORTRAIT, p))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((32, 28, 1048, 1892), radius=25, outline=p["stroke"], width=2)
    rounded(draw, (80, 90, 900, 158), 16, p["panel2"], p["stroke"], 2)
    draw.text((110, 108), "PULSELITE  /  UI SOUND EFFECTS", font=font(27, True), fill=p["text"])
    centered_text(draw, 490, 218, "THREE WORLDS", font(70, True), p["text"])
    centered_text(draw, 490, 310, "MENU KIT  •  SCI-FI  •  HORROR", font(34, True), p["accent"])
    rounded(draw, (90, 424, 890, 750), 24, p["panel"], p["stroke"], 2)
    centered_text(draw, 490, 458, "ALL THREE PACKS", font(38, True), p["muted"])
    centered_text(draw, 490, 526, "bigshadex.itch.io", font(48, True), p["accent"])
    centered_text(draw, 490, 594, "Links in description", font(38, True), p["text"])
    rounded(draw, (90, 790, 890, 1088), 24, p["panel"], p["stroke"], 2)
    centered_text(draw, 490, 824, "SOUND PREVIEWER", font(34, True), p["muted"])
    centered_text(draw, 490, 884, "bigshadex.github.io", font(38, True), p["accent"])
    centered_text(draw, 490, 936, PREVIEWER_PATH, font(38, True), p["text"])
    cbox = draw_portrait_footer(draw, pack, None, None)
    return {"pack_links": (90, 424, 890, 750),
            "preview_link": (90, 790, 890, 1088), "caption": cbox}


def draw_portrait_event(image: Image.Image, pack: str, scene: str,
                        event: str | None, filename: str | None) -> dict[str, Any]:
    if scene == "hook":
        return draw_portrait_menu(image, pack, event, filename, hook=True)
    if scene == "menu":
        return draw_portrait_menu(image, pack, event, filename)
    if scene == "settings":
        if event is None or filename is None:
            raise ValueError("Settings scene requires a cue")
        return draw_portrait_settings(image, pack, event, filename)
    if scene == "endcard":
        return draw_portrait_endcard(image)

    p = PALETTES[pack]
    image.paste(gradient(PORTRAIT, p))
    draw_backdrop_portrait(image, pack)
    draw = ImageDraw.Draw(image)
    game_title = {"menu-kit":"NIGHT MARKET", "sci-fi":"STARWARD", "horror":"THE HOLLOW"}[pack]
    rounded(draw, (80, 90, 900, 158), 16, p["panel2"], p["stroke"], 2)
    draw.text((110, 108), f"PULSELITE  /  {PACK_NAMES[pack]}", font=font(27, True), fill=p["text"])
    centered_text(draw, 490, 212, game_title, font(52, True), p["text"])
    scene_title = {"shop":"SUPPLY BAY", "inventory":"INVENTORY", "gameplay":"FIELD RUN",
                   "reward":"REWARD CLAIMED", "level-up":"LEVEL UP"}.get(scene)
    if scene_title is None:
        raise ValueError(f"Unknown portrait scene: {scene}")
    centered_text(draw, 490, 286, scene_title, font(36, True), p["accent"])
    panel = (90, 380, 890, 1158)
    rounded(draw, panel, 26, p["panel"], p["stroke"], 2)

    if scene == "shop":
        for i, (label, status) in enumerate((("FIELD KIT", "OWNED"),
                                               ("NIGHT LENS", "LOCKED"),
                                               ("SIGNAL BOOST", "NEW"))):
            col, row = i % 2, i // 2
            x, y = 130 + col*390, 454 + row*208
            card = (x, y, x+350, y+184)
            rounded(draw, card, 18, p["panel2"], p["stroke"], 2)
            draw.ellipse((x+132, y+20, x+218, y+106), outline=p["accent2"], width=3)
            centered_text(draw, x+175, y+119, label, font(24, True), p["text"])
            centered_text(draw, x+175, y+151, status, font(19, True), p["accent"])
    elif scene == "inventory":
        for i, label in enumerate(("PULSE CELL", "NOVA KEY", "FIELD MAP", "EMBER SHARD", "RUNE TOKEN", "CORE CHIP")):
            col, row = i % 2, i // 2
            x, y = 128 + col*390, 448 + row*205
            rounded(draw, (x, y, x+354, y+174), 16, p["panel2"], p["stroke"], 2)
            draw.ellipse((x+18, y+42, x+106, y+130), outline=p["accent"] if i%2==0 else p["accent2"], width=4)
            centered_text(draw, x+230, y+67, label, font(22, True), p["text"])
            centered_text(draw, x+230, y+104, f"SLOT 0{i+1}", font(18, True), p["muted"])
    elif scene == "gameplay":
        viewport = (122, 456, 858, 1084)
        rounded(draw, viewport, 18, (6, 13, 22), p["accent"], 2)
        draw.rectangle((144, 522, 836, 1058), fill=(5, 10, 18))
        draw.ellipse((610, 565, 802, 757), fill=p["glow"], outline=p["accent2"], width=3)
        draw.polygon([(144, 1020), (144, 900), (330, 810), (480, 888),
                      (620, 825), (836, 906), (836, 1058)], fill=(11, 30, 44), outline=p["stroke"])
        draw.polygon([(402, 910), (480, 780), (558, 910)], fill=p["accent"], outline=p["text"])
        rounded(draw, (160, 542, 410, 598), 12, p["panel2"], p["stroke"], 2)
        draw.text((182, 557), "HP  88 / 100", font=font(22, True), fill=p["text"])
        rounded(draw, (478, 965, 824, 1024), 12, p["panel2"], p["accent2"], 2)
        centered_text(draw, 651, 982, "+1 SIGNAL CELL", font(20, True), p["accent2"])
    elif scene == "reward":
        centered_text(draw, 490, 470, "DAILY DROP", font(30, True), p["muted"])
        rounded(draw, (258, 556, 722, 942), 26, p["panel2"], p["accent2"], 3)
        draw.ellipse((340, 620, 640, 920), fill=p["glow"], outline=p["accent2"], width=4)
        draw.polygon([(490, 650), (585, 770), (490, 890), (395, 770)], fill=p["accent2"], outline=p["text"])
        centered_text(draw, 490, 1000, "SIGNAL CORE ADDED", font(25, True), p["accent"])
    elif scene == "level-up":
        centered_text(draw, 490, 530, "LEVEL", font(72, True), p["accent2"])
        centered_text(draw, 490, 610, "UP", font(90, True), p["text"])
        centered_text(draw, 490, 760, "RANK 06  →  RANK 07", font(32, True), p["text"])
        rounded(draw, (180, 850, 800, 970), 18, p["panel2"], p["stroke"], 2)
        centered_text(draw, 490, 885, "NEW LOADOUT SLOT", font(30, True), p["accent"])

    caption_box = draw_portrait_footer(draw, pack, event, filename)
    result: dict[str, Any] = {"main_panel": panel}
    if caption_box is not None:
        result["caption"] = caption_box
    return result


def render_frame(pack: str, scene: str, event: str | None,
                 filename: str | None) -> tuple[Image.Image, dict[str, tuple[int, int, int, int]]]:
    image = gradient(LANDSCAPE, PALETTES[pack])
    if scene == "endcard":
        draw = ImageDraw.Draw(image)
        p = PALETTES[pack]
        draw.rounded_rectangle((32, 28, LANDSCAPE[0] - 32, LANDSCAPE[1] - 28),
                               radius=22, outline=(*p["stroke"],), width=2)
    else:
        draw_backdrop(image, pack)
    if scene != "endcard":
        draw_header(image, pack)
    if scene == "menu":
        boxes = draw_main_menu(image, pack)
    elif scene == "hook":
        boxes = draw_main_menu(image, pack, hook=True)
    elif scene == "settings":
        boxes = draw_settings(image, pack)
    elif scene == "shop":
        boxes = draw_shop(image, pack)
    elif scene == "inventory":
        boxes = draw_inventory(image, pack)
    elif scene == "gameplay":
        boxes = draw_gameplay(image, pack)
    elif scene == "reward":
        boxes = draw_reward(image, pack)
    elif scene == "level-up":
        boxes = draw_level_up(image, pack)
    elif scene == "endcard":
        boxes = draw_endcard(image, pack)
    else:
        raise ValueError(f"Unknown scene: {scene}")
    if scene != "endcard" and event is not None and filename is not None:
        boxes["caption"] = draw_footer(image, pack, event, filename)
    return image, boxes


def build_timeline() -> dict[str, Any]:
    result: dict[str, Any] = {"format": 1, "audio_note": "Source OGG cues are composition inputs; this is not a new live capture.",
                              "public_path_rule": "All source paths are relative to the private staged pack root; no local absolute paths are stored."}
    menu_events = []
    for ms, event in zip(MENU_TIMES, MENU_ORDER, strict=True):
        category, filename = EVENTS[event]
        scene = {
            "button_click": "menu", "button_hover": "menu", "toggle_on": "settings",
            "toggle_off": "settings", "menu_confirm": "menu", "menu_back": "settings",
            "error": "shop", "notification": "inventory", "panel_open": "inventory",
            "panel_close": "inventory", "transition": "gameplay", "coin_pickup": "gameplay",
            "reward": "reward", "level_up": "level-up",
        }[event]
        menu_events.append({"time_ms": ms, "source_pack": "menu-kit", "scene": scene, "event": event,
                            "source_relpath": f"audio/pulselite/{category}/{filename}",
                            "caption": caption_for(event, filename)})
    result["menu_kit"] = {"duration_ms": 60000, "closing_card_start_ms": 55000,
                          "source_pack": "menu-kit", "cuts": MENU_CUTS, "events": menu_events}
    for pack in ("sci-fi", "horror"):
        source = "sci-fi-rerun1" if pack == "sci-fi" else "horror"
        events = []
        for ms, event, scene, _focus in THEME_TIMELINE:
            category, filename = EVENTS[event]
            if event in {"button_hover", "button_click", "menu_confirm", "toggle_on", "toggle_off", "menu_back"}:
                filename = {"button_click":"click_01.ogg", "menu_confirm":"confirm_01.ogg"}.get(event, filename)
            events.append({"time_ms": ms, "source_pack": source, "scene": scene, "event": event,
                           "source_relpath": f"audio/pulselite/{category}/{filename}",
                           "caption": caption_for(event, filename)})
        result[pack] = {"duration_ms": 30000, "closing_card_start_ms": 26000,
                        "source_pack": source, "cuts": THEME_CUTS, "events": events}
    short = []
    for ms, pack, event, scene in (
        (1600, "menu-kit", "button_click", "menu"),
        (4200, "menu-kit", "toggle_on", "settings"),
        (7000, "menu-kit", "panel_open", "inventory"),
        (9200, "sci-fi-rerun1", "menu_confirm", "menu"),
        (11600, "sci-fi-rerun1", "coin_pickup", "gameplay"),
        (13700, "sci-fi-rerun1", "level_up", "level-up"),
        (16100, "horror", "error", "shop"),
        (18300, "horror", "reward", "reward"),
        (20400, "horror", "menu_back", "settings"),
    ):
        category, filename = EVENTS[event]
        if pack != "menu-kit" and event == "menu_confirm":
            filename = "confirm_01.ogg"
        short.append({"time_ms": ms, "source_pack": pack, "scene": scene,
                      "event": event, "source_relpath": f"audio/pulselite/{category}/{filename}",
                      "caption": caption_for(event, filename)})
    result["short"] = {
        "duration_ms": 25000,
        "endcard_start_ms": 22000,
        "cuts": [
            {"start_ms": 0, "end_ms": 4200, "scene": "menu-kit menu"},
            {"start_ms": 4200, "end_ms": 7400, "scene": "menu-kit settings/inventory"},
            {"start_ms": 7400, "end_ms": 9200, "scene": "sci-fi menu"},
            {"start_ms": 9200, "end_ms": 14800, "scene": "sci-fi gameplay/level-up"},
            {"start_ms": 14800, "end_ms": 22000, "scene": "horror shop/reward/settings"},
            {"start_ms": 22000, "end_ms": 25000, "scene": "endcard"},
        ],
        "events": short,
    }
    return result


def resolve_asset(pack_root: Path, relative: str) -> Path:
    candidate = (pack_root / relative).resolve()
    root = pack_root.resolve()
    if root not in candidate.parents:
        raise ValueError("Source path escaped the pack root")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--menu-root", type=Path, required=True,
                        help="Private Menu Kit project root that contains audio/pulselite/*.ogg")
    parser.add_argument("--sci-fi-root", type=Path, required=True,
                        help="Private Sci-Fi project root that contains audio/pulselite/*.ogg")
    parser.add_argument("--horror-root", type=Path, required=True,
                        help="Private Horror project root that contains audio/pulselite/*.ogg")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    specs = [
        ("01-title-menu", "sci-fi", "hook", "button_hover", "hover_01.ogg"),
        ("02-menu-kit-main-menu", "menu-kit", "menu", "button_click", "click_03.ogg"),
        ("03-sci-fi-settings", "sci-fi", "settings", "toggle_on", "toggle_01.ogg"),
        ("04-horror-shop", "horror", "shop", "error", "error_01.ogg"),
        ("05-menu-kit-inventory", "menu-kit", "inventory", "panel_open", "panel_open_04.ogg"),
        ("06-sci-fi-gameplay", "sci-fi", "gameplay", "coin_pickup", "coin_01.ogg"),
        ("07-horror-reward", "horror", "reward", "reward", "reward_05.ogg"),
        ("08-sci-fi-rapid-level-up", "sci-fi", "level-up", "level_up", "level_up_01.ogg"),
        ("09-menu-kit-endcard", "menu-kit", "endcard", None, None),
        ("10-sci-fi-endcard", "sci-fi", "endcard", None, None),
        ("11-horror-endcard", "horror", "endcard", None, None),
    ]
    roots = {"menu-kit": args.menu_root, "sci-fi": args.sci_fi_root, "horror": args.horror_root}
    frames = []
    for stem, pack, scene, event, filename in specs:
        image, boxes = render_frame(pack, scene, event, filename)
        path = out / f"{stem}.jpg"
        image.save(path, "JPEG", quality=91, optimize=True, subsampling=0)
        cue = None
        if event and filename:
            category = EVENTS[event][0]
            rel = f"audio/pulselite/{category}/{filename}"
            source = resolve_asset(roots[pack], rel)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            cue = {"event": event, "filename": filename, "source_relpath": rel,
                   "source_sha256": digest}
        frames.append({"file": path.name, "pack": pack, "scene": scene,
                       "cue": cue, "bounds": boxes, "size": list(image.size)})

    # A dedicated portrait screen, plus two scene variants, demonstrates native
    # 9:16 hierarchy instead of deriving it from a landscape crop.
    portrait_specs = [
        ("short-portrait-menu", "menu-kit", "button_click", "click_03.ogg", draw_portrait_menu),
        ("short-portrait-sci-fi-settings", "sci-fi", "toggle_on", "toggle_01.ogg", draw_portrait_settings),
        ("short-portrait-horror-menu", "horror", "error", "error_01.ogg", draw_portrait_menu),
    ]
    portrait_frames = []
    for stem, pack, event, filename, renderer in portrait_specs:
        image = Image.new("RGB", PORTRAIT, PALETTES[pack]["top"])
        if renderer is draw_portrait_menu:
            boxes = renderer(image, pack, event, filename)
        else:
            boxes = renderer(image, pack, event, filename)
        path = out / f"{stem}.jpg"
        image.save(path, "JPEG", quality=91, optimize=True, subsampling=0)
        portrait_frames.append({"file": path.name, "pack": pack, "cue": caption_for(event, filename),
                                "bounds": boxes, "size": list(image.size)})

    portrait_endcard = Image.new("RGB", PORTRAIT, PALETTES["menu-kit"]["top"])
    portrait_endcard_boxes = draw_portrait_endcard(portrait_endcard)
    portrait_endcard_path = out / "short-portrait-endcard.jpg"
    portrait_endcard.save(portrait_endcard_path, "JPEG", quality=91, optimize=True, subsampling=0)
    portrait_frames.append({"file": portrait_endcard_path.name, "pack": "menu-kit", "cue": None,
                            "bounds": portrait_endcard_boxes, "size": list(portrait_endcard.size)})

    # Actual downscaled renders are saved so reviewers can judge legibility at
    # the requested preview sizes.
    landscape = Image.open(out / "02-menu-kit-main-menu.jpg").convert("RGB")
    landscape.resize((640, 360), Image.Resampling.LANCZOS).save(out / "readability-landscape-640x360.png")
    portrait = Image.open(out / "short-portrait-menu.jpg").convert("RGB")
    portrait.resize((360, 640), Image.Resampling.LANCZOS).save(out / "readability-portrait-360x640.png")
    portrait_endcard.resize((360, 640), Image.Resampling.LANCZOS).save(
        out / "readability-portrait-endcard-360x640.png")
    endcard_sheet = Image.new("RGB", (1920, 360), (7, 11, 18))
    for index, stem in enumerate(("09-menu-kit-endcard", "10-sci-fi-endcard", "11-horror-endcard")):
        endcard = Image.open(out / f"{stem}.jpg").convert("RGB")
        endcard_sheet.paste(endcard.resize((640, 360), Image.Resampling.LANCZOS), (index * 640, 0))
    endcard_sheet.save(out / "readability-endcards-640x360.png")

    # A compact sequence sheet shows the actual generated review frames.
    rows = (len(frames) + 1) // 2
    sheet = Image.new("RGB", (1500, 32 + rows * 445), (7, 11, 18))
    sd = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        thumb = Image.open(out / frame["file"]).convert("RGB").resize((720, 405), Image.Resampling.LANCZOS)
        x = 24 + (i % 2) * 752
        y = 32 + (i // 2) * 445
        sheet.paste(thumb, (x, y))
        sd.text((x+8, y+410), f"{frame['file']}  |  {frame['cue']['event'] if frame['cue'] else 'END CARD'}",
                font=font(22, True), fill=(233, 241, 247))
    sheet.save(out / "review-contact-sheet.jpg", "JPEG", quality=84, optimize=True)

    timeline = build_timeline()
    timeline_roots = {
        "menu-kit": args.menu_root,
        "sci-fi-rerun1": args.sci_fi_root,
        "horror": args.horror_root,
    }
    for section in timeline.values():
        if not isinstance(section, dict) or not isinstance(section.get("events"), list):
            continue
        default_pack = section.get("source_pack")
        for cue in section["events"]:
            pack_id = cue.get("source_pack", default_pack)
            source = resolve_asset(timeline_roots[pack_id], cue["source_relpath"])
            cue["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    (out / "cue-timeline.json").write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    manifest = {"format": 1, "creative_note": "Clean illustrative game menus, drawn with Pillow primitives; no prior captures used.",
                "landscape_frames": frames, "portrait_frames": portrait_frames,
                "readability": ["readability-landscape-640x360.png", "readability-portrait-360x640.png",
                                "readability-portrait-endcard-360x640.png", "readability-endcards-640x360.png"],
                "cue_timeline": "cue-timeline.json"}
    (out / "review-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for path in sorted(out.glob("*.jpg")):
        print(f"{path.name}\t{path.stat().st_size}")
    for path in sorted(out.glob("*.png")):
        print(f"{path.name}\t{path.stat().st_size}")
    print(f"Frames rendered: {len(frames)} landscape + {len(portrait_frames)} portrait")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
