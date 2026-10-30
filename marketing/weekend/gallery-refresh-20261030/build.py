from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent
ROOT = OUT_DIR.parents[2]
CANVAS = (1920, 1080)
COLORS = {
    "bg": "#101b24",
    "panel": "#182b35",
    "panel_alt": "#1d343f",
    "line": "#39525b",
    "text": "#f2eee4",
    "muted": "#9aaead",
    "accent": "#d98b64",
    "teal": "#58c8d1",
    "ink": "#10202a",
}
EVENT_SOURCE = "addons/pulselite_ui/ui_events.json"
DEMO_SOURCE = "marketing/visuals/demo.gd"
HELPER_SOURCE = "addons/pulselite_ui/PulseLiteUI.gd"
VERIFICATION_SOURCE = "marketing/sound-lists/verification.md"
COMPLETE_SOURCE = "marketing/copy/2026-10-26/README.md"


def font(size: int):
    return ImageFont.load_default(size=size)


def open_canvas():
    image = Image.new("RGB", CANVAS, COLORS["bg"])
    return image, ImageDraw.Draw(image)


def draw_event_table() -> None:
    source = ROOT / EVENT_SOURCE
    event_doc = json.loads(source.read_text(encoding="utf-8"))
    events = event_doc["events"]
    categories = {event["category"] for event in events}
    if len(events) != 14 or len(categories) != 13:
        raise ValueError(
            f"Expected the shared 14-event / 13-category map; got "
            f"{len(events)} events and {len(categories)} categories"
        )

    image, draw = open_canvas()
    draw.text((104, 64), "PULSELITE  /  SHARED EVENT MAP", font=font(32), fill=COLORS["teal"])
    draw.text(
        (104, 112),
        "13 categories  /  14 shared event names",
        font=font(64),
        fill=COLORS["text"],
    )
    draw.text(
        (106, 202),
        "The three packs keep the same event names and category layout.",
        font=font(30),
        fill=COLORS["muted"],
    )

    counts = [
        ("MENU KIT", 200),
        ("SCI-FI", 104),
        ("HORROR", 104),
        ("COMPLETE", 408),
    ]
    x0, card_y, card_w, card_h, gap = 104, 272, 398, 142, 28
    for index, (label, amount) in enumerate(counts):
        x = x0 + index * (card_w + gap)
        draw.rounded_rectangle(
            (x, card_y, x + card_w, card_y + card_h),
            radius=22,
            fill=COLORS["panel"],
            outline=COLORS["line"],
            width=2,
        )
        draw.text((x + 26, card_y + 18), label, font=font(28), fill=COLORS["muted"])
        draw.text((x + 26, card_y + 54), f"{amount} unique sounds", font=font(40), fill=COLORS["text"])

    table_y = 468
    columns = ((104, events[:7]), (986, events[7:]))
    for col_x, rows in columns:
        draw.text((col_x + 16, table_y), "EVENT", font=font(24), fill=COLORS["teal"])
        draw.text((col_x + 510, table_y), "CATEGORY FOLDER", font=font(24), fill=COLORS["teal"])
        draw.line((col_x, table_y + 40, col_x + 820, table_y + 40), fill=COLORS["line"], width=2)
        for row_index, item in enumerate(rows):
            y = table_y + 53 + row_index * 56
            draw.text((col_x + 16, y), item["event"], font=font(28), fill=COLORS["text"])
            draw.text((col_x + 510, y), item["category"], font=font(28), fill=COLORS["muted"])
            draw.line((col_x, y + 43, col_x + 820, y + 43), fill=COLORS["line"], width=1)

    draw.text(
        (106, 946),
        "The public add-on's 20 free sounds are inside Menu Kit's 200. Matching OGG files are alternate encodings, not extra sounds.",
        font=font(24),
        fill=COLORS["muted"],
    )
    image.save(OUT_DIR / "14-shared-events-and-counts.png", format="PNG", optimize=False)


def find_source_snippet() -> tuple[int, str, int, str]:
    path = ROOT / DEMO_SOURCE
    lines = path.read_text(encoding="utf-8").splitlines()
    call_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "PulseLiteUI.wire_buttons(self)"),
        None,
    )
    if call_index is None:
        raise ValueError(f"Actual add-on call not found in {DEMO_SOURCE}")
    preceding = lines[call_index - 1].strip() if call_index > 0 else ""
    function_index = next(
        (index for index, line in enumerate(lines[:call_index]) if line.strip() == "func _ready() -> void:"),
        None,
    )
    if function_index is None or preceding != "_build_interface()":
        raise ValueError("Expected the actual call after _build_interface() inside _ready()")
    helper_text = (ROOT / HELPER_SOURCE).read_text(encoding="utf-8")
    if "func wire_buttons(root: Node" not in helper_text:
        raise ValueError(f"Expected wire_buttons helper not found in {HELPER_SOURCE}")
    return call_index, lines[call_index - 1], call_index + 1, lines[call_index]


def draw_code_panel() -> None:
    first_number, first_line, call_number, call_line = find_source_snippet()
    image, draw = open_canvas()
    draw.text((104, 72), "PULSELITE  /  GODOT BUTTON WIRING", font=font(32), fill=COLORS["teal"])
    draw.text((104, 126), "Connect the add-on from your own scene", font=font(64), fill=COLORS["text"])
    draw.text(
        (106, 218),
        "Example source: marketing/visuals/demo.gd, inside _ready().",
        font=font(30),
        fill=COLORS["muted"],
    )

    card = (104, 342, 1816, 762)
    draw.rounded_rectangle(card, radius=24, fill=COLORS["panel"], outline=COLORS["line"], width=2)
    draw.text((150, 390), "SOURCE EXCERPT", font=font(24), fill=COLORS["teal"])
    draw.text((150, 456), "func _ready() -> void:", font=font(42), fill=COLORS["muted"])
    draw.text((177, 522), "...", font=font(42), fill=COLORS["muted"])
    draw.text((150, 588), f"{first_number:>2}  {first_line.expandtabs(4)}", font=font(42), fill=COLORS["text"])
    draw.rounded_rectangle(
        (132, 656, 1788, 726),
        radius=12,
        fill=COLORS["panel_alt"],
        outline=COLORS["teal"],
        width=2,
    )
    draw.text(
        (150, 668),
        f"{call_number:>2}  {call_line.expandtabs(4)}",
        font=font(42),
        fill=COLORS["text"],
    )

    draw.text(
        (106, 810),
        "PulseLiteUI.wire_buttons(self) wires buttons beneath this scene node.",
        font=font(32),
        fill=COLORS["text"],
    )
    draw.text(
        (106, 868),
        "Bring your own game UI; the sound pack does not include this demo menu or a game template.",
        font=font(28),
        fill=COLORS["muted"],
    )
    draw.text(
        (106, 972),
        f"Excerpt lines {first_number}-{call_number} from {DEMO_SOURCE}; helper implementation in {HELPER_SOURCE}.",
        font=font(24),
        fill=COLORS["muted"],
    )
    image.save(OUT_DIR / "godot-wire-buttons-call.png", format="PNG", optimize=False)


def image_details(path: Path) -> dict:
    data = path.read_bytes()
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


def item(
    order: int,
    role: str,
    path: str,
    caption: str,
    alt_text: str,
    source_paths: list[str],
) -> dict:
    return {
        "order": order,
        "role": role,
        "asset_path": path,
        "caption": caption,
        "alt_text": alt_text,
        "source_paths": source_paths,
    }


def build_review_previews() -> None:
    sources = (
        (
            ".review-half-menu-kit.png",
            "marketing/visuals/02-confirm-signal.png",
        ),
        (
            ".review-half-sci-fi.png",
            "marketing/gallery/sci-fi/02-confirm.png",
        ),
        (
            ".review-half-horror.png",
            "marketing/gallery/horror/02-confirm.png",
        ),
        (
            ".review-half-events.png",
            "marketing/weekend/gallery-refresh-20261030/14-shared-events-and-counts.png",
        ),
        (
            ".review-half-code.png",
            "marketing/weekend/gallery-refresh-20261030/godot-wire-buttons-call.png",
        ),
    )
    for name, source_path in sources:
        source = ROOT / source_path
        with Image.open(source) as image:
            preview = image.resize(
                (image.width // 2, image.height // 2),
                Image.Resampling.LANCZOS,
            )
            preview.save(OUT_DIR / name, format="PNG", optimize=False)


def build_gallery_order() -> None:
    event_art = "marketing/weekend/gallery-refresh-20261030/14-shared-events-and-counts.png"
    code_art = "marketing/weekend/gallery-refresh-20261030/godot-wire-buttons-call.png"
    event_sources = [
        event_art,
        EVENT_SOURCE,
        VERIFICATION_SOURCE,
        COMPLETE_SOURCE,
        "marketing/visuals/README.md",
    ]
    code_sources = [code_art, DEMO_SOURCE, HELPER_SOURCE]

    menu_kit_shot = "marketing/visuals/02-confirm-signal.png"
    scifi_shot = "marketing/gallery/sci-fi/02-confirm.png"
    horror_shot = "marketing/gallery/horror/02-confirm.png"

    event_caption = (
        "Shared map: 14 event names across 13 category folders. Counts are unique "
        "sound files; matching OGG encodings are not counted again."
    )
    event_alt = (
        "Table mapping fourteen shared UI events to thirteen category folders, "
        "with counts of 200 Menu Kit, 104 Sci-Fi, 104 Horror, and 408 Complete "
        "unique sounds. Matching OGG encodings are alternate formats."
    )
    code_caption = (
        "Godot helper call from the existing demo source. It wires buttons under "
        "a scene node; the sound pack does not include the demo UI or a game template."
    )
    code_alt = (
        "Code panel showing the Godot demo call PulseLiteUI.wire_buttons(self) "
        "inside _ready, after building the sample interface. This code is a helper "
        "example, not an included game UI."
    )

    pages = [
        {
            "page": "Menu Kit",
            "unique_sound_count": 200,
            "count_basis": "Unique WAV sound files; matching OGG files are alternate encodings.",
            "items": [
                item(
                    1,
                    "menu shot with captured signal",
                    menu_kit_shot,
                    (
                        "Illustrative Mirror & Mist menu with the captured Menu Kit "
                        "free-sample menu_confirm receipt for confirm/confirm_06.wav. "
                        "The Godot capture used synthetic viewport input and the "
                        "Dummy audio driver; it does not demonstrate audible playback."
                    ),
                    (
                        "Wide dark teal illustrative Mirror & Mist menu beside a "
                        "playback receipt showing menu_confirm and "
                        "confirm/confirm_06.wav. The frame is labelled free-sample "
                        "mapping; the menu is not included with the sound pack."
                    ),
                    [menu_kit_shot, "marketing/visuals/README.md"],
                ),
                item(2, "shared event table", event_art, event_caption, event_alt, event_sources),
                item(3, "Godot call snippet", code_art, code_caption, code_alt, code_sources),
            ],
        },
        {
            "page": "Sci-Fi",
            "unique_sound_count": 104,
            "count_basis": "Unique WAV sound files; matching OGG files are alternate encodings.",
            "items": [
                item(
                    1,
                    "illustrative menu and static event example",
                    scifi_shot,
                    (
                        "Illustrative Mirror & Mist menu labelled for Sci-Fi sounds, "
                        "with a static menu_confirm / confirm/confirm_07.ogg example. "
                        "This is not a game capture or an audible playback test."
                    ),
                    (
                        "Illustrative Mirror & Mist menu mockup with a Sci-Fi sounds "
                        "badge and a separate receipt card displaying menu_confirm "
                        "and confirm/confirm_07.ogg as a static example. No game UI is included."
                    ),
                    [scifi_shot, "marketing/gallery/ALT_TEXT.md", "marketing/gallery/README.md"],
                ),
                item(2, "shared event table", event_art, event_caption, event_alt, event_sources),
                item(3, "Godot call snippet", code_art, code_caption, code_alt, code_sources),
            ],
        },
        {
            "page": "Horror",
            "unique_sound_count": 104,
            "count_basis": "Unique WAV sound files; matching OGG files are alternate encodings.",
            "items": [
                item(
                    1,
                    "illustrative menu and static event example",
                    horror_shot,
                    (
                        "Illustrative Mirror & Mist menu labelled for Horror sounds, "
                        "with a static menu_confirm / confirm/confirm_02.ogg example. "
                        "This is not a game capture or an audible playback test."
                    ),
                    (
                        "Illustrative Mirror & Mist menu mockup with a Horror sounds "
                        "badge and a separate receipt card displaying menu_confirm "
                        "and confirm/confirm_02.ogg as a static example. No game UI is included."
                    ),
                    [horror_shot, "marketing/gallery/ALT_TEXT.md", "marketing/gallery/README.md"],
                ),
                item(2, "shared event table", event_art, event_caption, event_alt, event_sources),
                item(3, "Godot call snippet", code_art, code_caption, code_alt, code_sources),
            ],
        },
        {
            "page": "Complete",
            "unique_sound_count": 408,
            "count_basis": "200 Menu Kit + 104 Sci-Fi + 104 Horror unique WAV files; OGG encodings are not added again.",
            "items": [
                item(
                    1,
                    "menu shot with captured signal",
                    menu_kit_shot,
                    (
                        "Illustrative menu with a captured Menu Kit free-sample "
                        "menu_confirm / confirm/confirm_06.wav receipt. This included "
                        "Menu Kit sound is one part of Complete; the image does not "
                        "show Sci-Fi or Horror recordings."
                    ),
                    (
                        "Wide dark teal illustrative Mirror & Mist menu beside a "
                        "captured menu_confirm receipt for confirm/confirm_06.wav, "
                        "a Menu Kit sound included in Complete. The UI is not included."
                    ),
                    [menu_kit_shot, "marketing/visuals/README.md", COMPLETE_SOURCE],
                ),
                item(2, "shared event table", event_art, event_caption, event_alt, event_sources),
                item(3, "Godot call snippet", code_art, code_caption, code_alt, code_sources),
            ],
        },
    ]

    for page in pages:
        for asset in page["items"]:
            if not asset["alt_text"].strip() or not asset["caption"].strip():
                raise ValueError(f"Missing alt text or caption: {page['page']} order {asset['order']}")
            for source_path in asset["source_paths"]:
                absolute = ROOT / source_path
                if not absolute.is_file():
                    raise FileNotFoundError(f"Missing listed source: {source_path}")
            details = image_details(ROOT / asset["asset_path"])
            asset["image"] = details

    out = {
        "task": "W11 paid-page gallery refresh recommendation",
        "read_only_listing_recommendation": True,
        "new_live_tests": False,
        "shared_category_count": 13,
        "shared_event_count": 14,
        "public_addon_free_sounds_are_subset_of_menu_kit": 20,
        "sound_counts_are_unique_files_not_wav_plus_ogg": True,
        "disclosures": [
            "Menu UI illustrations and demo code are not included game templates.",
            "Sci-Fi and Horror event receipts are static example labels, not captured sound playback.",
            "The Menu Kit signal capture used synthetic viewport input and Godot Dummy audio; it is not an audible playback or physical-pointer test.",
            "Sound is procedural DSP; visual assets and code/docs were AI-assisted.",
            "The public add-on's 20 free sounds are a subset of Menu Kit.",
            "Matching WAV and OGG encodings are not counted as separate sounds.",
        ],

        "pages": pages,
    }
    (OUT_DIR / "gallery-order.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    draw_event_table()
    draw_code_panel()
    build_review_previews()
    build_gallery_order()
    for name in ("14-shared-events-and-counts.png", "godot-wire-buttons-call.png"):
        details = image_details(OUT_DIR / name)
        print(
            f"{name}: {details['width']}x{details['height']}, "
            f"{details['bytes']} bytes, sha256 {details['sha256']}"
        )
    print("Wrote gallery-order.json for Menu Kit, Sci-Fi, Horror, and Complete.")


if __name__ == "__main__":
    main()
