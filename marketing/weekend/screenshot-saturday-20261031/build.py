from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
ROOT = OUT_DIR.parents[2]
MAX_BYTES = 5 * 1024 * 1024

ASSETS = (
    {
        "file": "01-main-menu.png",
        "source": "marketing/visuals/01-main-menu.png",
        "label": "Menu overview",
        "caption": (
            "Illustrative Mirror & Mist menu with the playback receipt waiting for "
            "PulseLiteUI.played; this frame shows no event yet."
        ),
        "alt_text": (
            "Wide dark teal fictional Mirror & Mist game menu with Continue, Begin "
            "a New Journey, and Audio Settings buttons. The right playback receipt "
            "says No playback yet and lists example input mappings."
        ),
    },
    {
        "file": "02-confirm-signal.png",
        "source": "marketing/visuals/02-confirm-signal.png",
        "label": "Confirm signal",
        "caption": (
            "Illustrative menu capture with a captured menu_confirm receipt for "
            "confirm/confirm_06.wav after synthetic viewport input; the image has "
            "no audible playback."
        ),
        "alt_text": (
            "Wide dark teal illustrative Mirror & Mist menu beside a playback "
            "receipt showing menu_confirm and confirm/confirm_06.wav. The fictional "
            "game UI is not included."
        ),
    },
    {
        "file": "03-options-toggle.png",
        "source": "marketing/visuals/03-options-toggle.png",
        "label": "Options toggle",
        "caption": (
            "Illustrative settings menu with AMBIENCE / ON highlighted and a "
            "captured toggle_on receipt for toggle/toggle_01.wav after synthetic "
            "viewport input; the image has no audible playback."
        ),
        "alt_text": (
            "Wide dark teal illustrative Mirror & Mist settings menu with "
            "AMBIENCE / ON highlighted. The playback receipt shows toggle_on and "
            "toggle/toggle_01.wav; the fictional game UI is not included."
        ),
    },
)


def png_dimensions(data: bytes, name: str) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"{name} is not a valid PNG with an IHDR header")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise ValueError(f"{name} has invalid dimensions {width}x{height}")
    return width, height


def main() -> None:
    records = []
    for item in ASSETS:
        source = ROOT / item["source"]
        destination = OUT_DIR / item["file"]
        if not source.is_file():
            raise FileNotFoundError(f"Missing source art: {item['source']}")
        data = source.read_bytes()
        if len(data) >= MAX_BYTES:
            raise ValueError(f"{item['source']} is not under 5 MiB")
        width, height = png_dimensions(data, item["source"])
        destination.write_bytes(data)
        records.append(
            {
                **item,
                "format": "PNG",
                "width": width,
                "height": height,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )

    manifest = {
        "task": "W10 ScreenshotSaturday stills",
        "generated_from_existing_art": True,
        "assets": records,
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for record in records:
        print(
            f'{record["file"]}: {record["width"]}x{record["height"]}, '
            f'{record["bytes"]} bytes, sha256 {record["sha256"]}'
        )
    print(f"Manifest: {manifest_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
