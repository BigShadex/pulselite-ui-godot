"""Make 630px menu-kit gallery cards from the merged A027 Godot viewport captures."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 630
HEIGHT = 953
CARD_WIDTH = 594
MENU_BOX = (76, 142, 715, 615)
RECEIPT_BOX = (760, 142, 1204, 420)
MENU_POSITION = (18, 68)
RECEIPT_GAP = 18
FOOTER_GAP = 24
BACKGROUND = "#101b24"
COPPER = "#d38b66"
INK = "#101b24"
PAPER = "#ece8dc"
LABEL = "Illustrative example"
FOOTER = "Illustrative interface only. The sound pack does not include a game UI."
MAX_ASSET_BYTES = 3_000_000
STILL_SOURCES = [
    ("menu-kit-01-confirm.png", "02-confirm-signal.png"),
    ("menu-kit-02-toggle-on.png", "03-options-toggle.png"),
]


def _font(path: Path | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path is None:
        return ImageFont.load_default(size=size)
    if not path.is_file():
        raise SystemExit(f"Font file not found: {path}")
    return ImageFont.truetype(str(path), size=size)


def _compose(source: Image.Image, badge_font: ImageFont.ImageFont, footer_font: ImageFont.ImageFont) -> Image.Image:
    if source.size != (1280, 720):
        raise SystemExit(f"Expected a 1280x720 A027 source frame; got {source.size}")

    source = source.convert("RGB")
    menu = source.crop(MENU_BOX)
    menu_size = (CARD_WIDTH, round(menu.height * CARD_WIDTH / menu.width))
    menu = menu.resize(menu_size, Image.Resampling.LANCZOS)
    receipt = source.crop(RECEIPT_BOX)
    receipt_size = (CARD_WIDTH, round(receipt.height * CARD_WIDTH / receipt.width))
    receipt = receipt.resize(receipt_size, Image.Resampling.LANCZOS)

    receipt_position = (
        MENU_POSITION[0],
        MENU_POSITION[1] + menu.height + RECEIPT_GAP,
    )
    footer_y = receipt_position[1] + receipt.height + FOOTER_GAP
    if footer_y + footer_font.getbbox(FOOTER)[3] > HEIGHT - 12:
        raise SystemExit("The footer does not fit within the gallery card")

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    canvas.paste(menu, MENU_POSITION)
    canvas.paste(receipt, receipt_position)

    draw = ImageDraw.Draw(canvas)
    label_box = draw.textbbox((0, 0), LABEL, font=badge_font)
    badge_width = label_box[2] - label_box[0] + 28
    badge_height = label_box[3] - label_box[1] + 16
    badge = (18, 14, 18 + badge_width, 14 + badge_height)
    draw.rounded_rectangle(badge, radius=7, fill=COPPER)
    draw.text((badge[0] + 14, badge[1] + 7 - label_box[1]), LABEL, font=badge_font, fill=INK)

    draw.text((18, footer_y), FOOTER, font=footer_font, fill=PAPER)
    return canvas


def _check_asset(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Expected gallery output was not created: {path.name}")
    size = path.stat().st_size
    if size >= MAX_ASSET_BYTES:
        raise SystemExit(f"Asset exceeds the strict 3,000,000-byte limit: {path.name} ({size})")


def _load_gif(path: Path) -> tuple[list[Image.Image], list[int]]:
    frames: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(path) as animation:
        for index in range(animation.n_frames):
            animation.seek(index)
            frames.append(animation.convert("RGB").copy())
            durations.append(int(animation.info.get("duration", 0)))
    if len(frames) != 9 or sum(durations) < 6000 or sum(durations) > 10000:
        raise SystemExit(f"Expected the nine-frame, 6-10-second A027 GIF; got {len(frames)} frames / {sum(durations)} ms")
    return frames, durations


def _write_preview_sheets(frames: list[Image.Image], stills: list[Image.Image], preview_dir: Path) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)
    still_contact = Image.new("RGB", (WIDTH, HEIGHT * len(stills)), BACKGROUND)
    for index, still in enumerate(stills):
        still_contact.paste(still, (0, index * HEIGHT))
    still_contact.save(preview_dir / "menu-kit-stills-630-contact.png", optimize=True)

    for sheet_index in range(3):
        contact = Image.new("RGB", (WIDTH, HEIGHT * 3), BACKGROUND)
        for row in range(3):
            frame_index = sheet_index * 3 + row
            contact.paste(frames[frame_index], (0, row * HEIGHT))
        contact.save(preview_dir / f"menu-kit-gif-630-keyframes-{sheet_index + 1:02d}.png", optimize=True)


def build(source_dir: Path, output_dir: Path, preview_dir: Path | None, bold_font_path: Path | None, regular_font_path: Path | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    badge_font = _font(bold_font_path, 20)
    footer_font = _font(regular_font_path, 13)

    stills: list[Image.Image] = []
    for output_name, source_name in STILL_SOURCES:
        source_path = source_dir / source_name
        if not source_path.is_file():
            raise SystemExit(f"Missing merged A027 still: {source_path}")
        with Image.open(source_path) as image:
            still = _compose(image.convert("RGB"), badge_font, footer_font)
        output_path = output_dir / output_name
        still.save(output_path, format="PNG", optimize=True, compress_level=9)
        _check_asset(output_path)
        stills.append(still)

    source_gif = source_dir / "pulselite-menu-demo.gif"
    if not source_gif.is_file():
        raise SystemExit(f"Missing merged A027 animation: {source_gif}")
    source_frames, durations = _load_gif(source_gif)
    frames = [_compose(frame, badge_font, footer_font) for frame in source_frames]

    back_path = output_dir / "menu-kit-03-menu-back.png"
    frames[-1].save(back_path, format="PNG", optimize=True, compress_level=9)
    _check_asset(back_path)
    stills.append(frames[-1])

    # One shared palette keeps the badge and text stable across every silent frame.
    palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed_frames = [frame.quantize(palette=palette) for frame in frames]
    gif_path = output_dir / "menu-kit-gallery.gif"
    indexed_frames[0].save(
        gif_path,
        save_all=True,
        append_images=indexed_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    _check_asset(gif_path)
    with Image.open(gif_path) as check:
        if check.size != (WIDTH, HEIGHT) or check.n_frames != 9:
            raise SystemExit(f"Unexpected output GIF geometry/frame count: {check.size}, {check.n_frames}")
        output_durations: list[int] = []
        for index in range(check.n_frames):
            check.seek(index)
            output_durations.append(int(check.info.get("duration", 0)))
    if sum(output_durations) < 6000 or sum(output_durations) > 10000:
        raise SystemExit(f"Output GIF duration is outside 6-10 seconds: {sum(output_durations)} ms")

    if preview_dir is not None:
        _write_preview_sheets(frames, stills, preview_dir)

    still_paths = [output_dir / name for name, _ in STILL_SOURCES] + [back_path]
    for path in [*still_paths, gif_path]:
        with Image.open(path) as image:
            print(f"ASSET_OK {path.name} size={image.width}x{image.height} bytes={path.stat().st_size}")
    print(f"GIF_OK frames=9 duration_ms={sum(output_durations)} silent=true")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=repo_root / "marketing" / "visuals")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--preview-dir", type=Path, help="Private destination for 630px-wide visual QA contact sheets")
    parser.add_argument("--font-bold", type=Path, help="Installed bold font for the badge; defaults to Pillow's built-in font")
    parser.add_argument("--font-regular", type=Path, help="Installed regular font for the footer; defaults to Pillow's built-in font")
    args = parser.parse_args()
    build(args.source_dir, args.output_dir, args.preview_dir, args.font_bold, args.font_regular)


if __name__ == "__main__":
    main()
