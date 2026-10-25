"""Build the silent marketing GIF from nine captured Godot viewport frames."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


FRAME_NAMES = [
    "frame-01-idle.png",
    "frame-02-hover.png",
    "frame-03-click.png",
    "frame-04-confirm.png",
    "frame-05-options.png",
    "frame-06-toggle-on.png",
    "frame-07-toggle-off.png",
    "frame-08-save.png",
    "frame-09-back.png",
]
DURATIONS_MS = [900, 800, 800, 900, 800, 900, 800, 900, 800]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, required=True, help="Private directory containing the Godot-captured PNG frames")
    parser.add_argument("--output", type=Path, required=True, help="Destination for the silent GIF")
    args = parser.parse_args()

    source_frames = []
    for filename in FRAME_NAMES:
        path = args.frames / filename
        if not path.is_file():
            raise SystemExit(f"Missing captured Godot frame: {filename}")
        image = Image.open(path).convert("RGB")
        if image.size != (1280, 720):
            raise SystemExit(f"Unexpected frame size for {filename}: {image.size}")
        source_frames.append(image)

    # A shared palette avoids color shifts between otherwise identical UI frames.
    palette = source_frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    frames = [image.quantize(palette=palette) for image in source_frames]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=DURATIONS_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    duration_ms = sum(DURATIONS_MS)
    print(f"GIF_OK frames={len(frames)} duration_ms={duration_ms} size={frames[0].size} bytes={args.output.stat().st_size}")


if __name__ == "__main__":
    main()
