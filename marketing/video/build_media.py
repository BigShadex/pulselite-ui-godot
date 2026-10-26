"""Build themed gallery cards and a silent reel from verified Godot captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

import capture_pack


WIDTH = 630
HEIGHT = 953
CARD_WIDTH = 594
MENU_BOX = (76, 142, 715, 615)
RECEIPT_BOX = (760, 142, 1204, 420)
MENU_POSITION = (18, 68)
RECEIPT_GAP = 18
FOOTER_GAP = 24
MAX_GALLERY_BYTES = 3_000_000
MAX_VIDEO_BYTES = 20_000_000
VIDEO_FPS = 10
VIDEO_BITRATE = 1_200_000
GIF_FRAMES = [
    ("frame-02-hover.png", 900),
    ("frame-03-click.png", 900),
    ("frame-04-confirm.png", 1000),
    ("frame-05-options.png", 1000),
    ("frame-06-toggle-on.png", 1000),
    ("frame-07-toggle-off.png", 1000),
    ("frame-08-save.png", 900),
    ("frame-09-back.png", 900),
]
STILLS = [
    ("01-hover", "frame-02-hover.png", "button_hover"),
    ("02-confirm", "frame-04-confirm.png", "menu_confirm"),
    ("03-toggle-on", "frame-06-toggle-on.png", "toggle_on"),
]
PALETTES = {
    "sci-fi": {"background": "#0b1926", "badge": "#64b8c3", "ink": "#12222b", "paper": "#eef3ef"},
    "horror": {"background": "#1b1018", "badge": "#c06b4d", "ink": "#201119", "paper": "#f3e9df"},
}
FOOTER = "Illustrative interface only; this sound pack includes no game UI."
VIDEO_NAME = "pulselite-ui-themes-demo.mp4"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(path: Path | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path is not None:
        if not path.is_file():
            raise SystemExit(f"Requested font does not exist: {path}")
        return ImageFont.truetype(str(path), size=size)
    if Path("C:/Windows/Fonts/arial.ttf").is_file():
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size=size)
    return ImageFont.load_default(size=size)


def compose_card(
    source_path: Path,
    pack_label: str,
    palette: dict[str, str],
    badge_font: ImageFont.ImageFont,
    footer_font: ImageFont.ImageFont,
) -> Image.Image:
    with Image.open(source_path) as opened:
        if opened.size != (1280, 720):
            raise SystemExit(f"Expected a 1280x720 Godot capture, got {opened.size} in {source_path.name}")
        source = opened.convert("RGB")

    menu = source.crop(MENU_BOX)
    menu_size = (CARD_WIDTH, round(menu.height * CARD_WIDTH / menu.width))
    menu = menu.resize(menu_size, Image.Resampling.LANCZOS)
    receipt = source.crop(RECEIPT_BOX)
    receipt_size = (CARD_WIDTH, round(receipt.height * CARD_WIDTH / receipt.width))
    receipt = receipt.resize(receipt_size, Image.Resampling.LANCZOS)
    receipt_position = (MENU_POSITION[0], MENU_POSITION[1] + menu.height + RECEIPT_GAP)
    footer_y = receipt_position[1] + receipt.height + FOOTER_GAP
    footer_bounds = footer_font.getbbox(FOOTER)
    if footer_y + footer_bounds[3] > HEIGHT - 12:
        raise SystemExit("Gallery footer does not fit the 630px card")

    canvas = Image.new("RGB", (WIDTH, HEIGHT), palette["background"])
    canvas.paste(menu, MENU_POSITION)
    canvas.paste(receipt, receipt_position)
    draw = ImageDraw.Draw(canvas)
    badge_text = f"Illustrative example | {pack_label} sounds"
    badge_bounds = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_width = badge_bounds[2] - badge_bounds[0] + 26
    badge_height = badge_bounds[3] - badge_bounds[1] + 14
    if badge_width > WIDTH - 36:
        raise SystemExit(f"The {pack_label} badge does not fit at 630px")
    badge_box = (18, 14, 18 + badge_width, 14 + badge_height)
    draw.rounded_rectangle(badge_box, radius=7, fill=palette["badge"])
    draw.text((badge_box[0] + 13, badge_box[1] + 6 - badge_bounds[1]), badge_text, font=badge_font, fill=palette["ink"])
    draw.text((18, footer_y), FOOTER, font=footer_font, fill=palette["paper"])
    return canvas


def check_capture(archive_path: Path, capture_dir: Path, pack_label: str) -> tuple[dict[str, object], dict[str, set[str]], list[dict[str, object]]]:
    if not capture_dir.is_dir():
        raise SystemExit(f"Missing private capture directory for {pack_label}")
    manifest_path = capture_dir / "capture-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing capture manifest for {pack_label}")
    capture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_manifest, event_map, audio_members, base_path, extension = capture_pack.check_pack_archive(archive_path)
    if capture_manifest["archive"]["archive_sha256"] != archive_manifest["archive_sha256"]:
        raise SystemExit(f"Private capture source ZIP does not match the explicitly supplied {pack_label} ZIP")
    if capture_manifest.get("pack_label") != pack_label:
        raise SystemExit(f"Private capture label mismatch: {capture_manifest.get('pack_label')!r}")
    if capture_manifest["archive"].get("base_path") != base_path or capture_manifest["archive"].get("extension") != extension:
        raise SystemExit(f"Private capture uses different audio path settings for {pack_label}")

    stage_root = capture_dir / "project" / Path(base_path.removeprefix("res://"))
    staged_hashes: dict[str, str] = {}
    for relative, audio_bytes in audio_members:
        audio_path = stage_root.joinpath(*Path(relative).parts).with_suffix(f".{extension}")
        if not audio_path.is_file():
            raise SystemExit(f"Private staged recording is missing: {relative}.{extension}")
        expected = hashlib.sha256(audio_bytes).hexdigest()
        if sha256_file(audio_path) != expected:
            raise SystemExit(f"Private staged recording differs from the explicitly supplied archive: {relative}.{extension}")
        staged_hashes[relative] = expected

    gallery_trace = capture_pack.read_trace(capture_dir / "played-events.jsonl", event_map, staged_hashes, base_path, extension)
    video_trace_path = capture_dir / "video-played-events.jsonl"
    video_trace = capture_pack.read_trace(video_trace_path, event_map, staged_hashes, base_path, extension)
    gallery_frames = sorted((capture_dir / "frames").glob("frame-*.png"))
    if len(gallery_frames) != 9:
        raise SystemExit(f"Expected nine A027 viewport captures for {pack_label}; found {len(gallery_frames)}")
    for _, frame_name, required_event in STILLS:
        frame_path = capture_dir / "frames" / frame_name
        if not frame_path.is_file():
            raise SystemExit(f"Missing {pack_label} event frame {frame_name}")
    trace_entries = [json.loads(line) for line in (capture_dir / "played-events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for _, frame_name, required_event in STILLS:
        if not any(entry["event"] == required_event for entry in trace_entries):
            raise SystemExit(f"The {pack_label} capture trace has no {required_event} event for {frame_name}")

    video_frames = sorted((capture_dir / "video-frames").glob("frame-*.png"))
    expected_video_frames = int(capture_manifest["continuous_video_capture"]["viewport_frames"])
    if len(video_frames) != expected_video_frames or not video_frames:
        raise SystemExit(f"Video frame count differs from {pack_label} capture manifest")
    return capture_manifest, event_map, trace_entries


def asset_record(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        return {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "dimensions": [image.width, image.height],
            "format": image.format,
        }


def check_asset(path: Path, maximum: int) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing expected output asset {path.name}")
    if path.stat().st_size >= maximum:
        raise SystemExit(f"Asset exceeds the strict {maximum:,}-byte limit: {path.name} ({path.stat().st_size})")


def build_gallery(
    pack_dir: Path,
    capture_dir: Path,
    pack_label: str,
    palette: dict[str, str],
    badge_font: ImageFont.ImageFont,
    footer_font: ImageFont.ImageFont,
    preview_dir: Path,
) -> list[dict[str, object]]:
    pack_dir.mkdir(parents=True, exist_ok=True)
    still_records: list[dict[str, object]] = []
    source_frames = capture_dir / "frames"
    for still_name, frame_name, _event in STILLS:
        output_path = pack_dir / f"{still_name}.png"
        image = compose_card(source_frames / frame_name, pack_label, palette, badge_font, footer_font)
        image.save(output_path, format="PNG", optimize=True, compress_level=9)
        check_asset(output_path, MAX_GALLERY_BYTES)
        still_records.append(asset_record(output_path))

    gallery_frames: list[Image.Image] = []
    durations: list[int] = []
    for frame_name, duration in GIF_FRAMES:
        gallery_frames.append(compose_card(source_frames / frame_name, pack_label, palette, badge_font, footer_font))
        durations.append(duration)
    gif_path = pack_dir / f"{pack_dir.name}-gallery.gif"
    palette_image = gallery_frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed_frames = [frame.quantize(palette=palette_image) for frame in gallery_frames]
    indexed_frames[0].save(
        gif_path,
        format="GIF",
        save_all=True,
        append_images=indexed_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    check_asset(gif_path, MAX_GALLERY_BYTES)
    with Image.open(gif_path) as animation:
        output_durations: list[int] = []
        if animation.size != (WIDTH, HEIGHT) or animation.n_frames != len(GIF_FRAMES):
            raise SystemExit(f"Unexpected {pack_label} GIF geometry/frame count: {animation.size} / {animation.n_frames}")
        for index in range(animation.n_frames):
            animation.seek(index)
            output_durations.append(int(animation.info.get("duration", 0)))
    total_duration = sum(output_durations)
    if not 6000 <= total_duration <= 10000:
        raise SystemExit(f"{pack_label} GIF duration is outside 6–10 seconds: {total_duration} ms")
    still_records.append(asset_record(gif_path) | {"frames": len(GIF_FRAMES), "duration_ms": total_duration, "silent": True})

    preview_dir.mkdir(parents=True, exist_ok=True)
    contact = Image.new("RGB", (WIDTH, HEIGHT * 3), palette["background"])
    for index, record in enumerate(still_records[:3]):
        with Image.open(pack_dir / str(record["name"])) as image:
            contact.paste(image.convert("RGB"), (0, index * HEIGHT))
    contact.save(preview_dir / f"{pack_dir.name}-stills-contact.png", optimize=True)
    gif_contact = Image.new("RGB", (WIDTH * 2, HEIGHT * 4), palette["background"])
    for index, frame in enumerate(gallery_frames):
        gif_contact.paste(frame, ((index % 2) * WIDTH, (index // 2) * HEIGHT))
    gif_contact.save(preview_dir / f"{pack_dir.name}-gif-keyframes.png", optimize=True)
    return still_records


def iter_boxes(data: bytes, start: int, end: int) -> Iterable[tuple[bytes, int, int]]:
    offset = start
    while offset + 8 <= end:
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        header_size = 8
        if size == 1:
            if offset + 16 > end:
                raise SystemExit("Truncated 64-bit MP4 box size")
            size = struct.unpack_from(">Q", data, offset + 8)[0]
            header_size = 16
        elif size == 0:
            size = end - offset
        if size < header_size or offset + size > end:
            raise SystemExit(f"Invalid MP4 box {kind!r}")
        yield kind, offset + header_size, offset + size
        offset += size
    if offset != end:
        raise SystemExit("MP4 box layout has trailing bytes")


def find_child(data: bytes, start: int, end: int, kind: bytes) -> tuple[int, int] | None:
    return next(((payload, box_end) for box_kind, payload, box_end in iter_boxes(data, start, end) if box_kind == kind), None)


def parse_duration(data: bytes, payload: int, end: int) -> tuple[int, int]:
    version = data[payload]
    if version == 0:
        timescale = struct.unpack_from(">I", data, payload + 12)[0]
        duration = struct.unpack_from(">I", data, payload + 16)[0]
    elif version == 1:
        timescale = struct.unpack_from(">I", data, payload + 20)[0]
        duration = struct.unpack_from(">Q", data, payload + 24)[0]
    else:
        raise SystemExit(f"Unsupported MP4 duration version {version}")
    if payload + (20 if version == 0 else 32) > end or timescale == 0:
        raise SystemExit("Invalid MP4 duration metadata")
    return timescale, duration


def inspect_mp4(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    top = list(iter_boxes(data, 0, len(data)))
    if not any(kind == b"ftyp" for kind, _, _ in top) or not any(kind == b"mdat" for kind, _, _ in top):
        raise SystemExit("The output is not a complete ISO MP4 file")
    moov = next(((payload, box_end) for kind, payload, box_end in top if kind == b"moov"), None)
    if moov is None:
        raise SystemExit("The MP4 has no moov metadata box")
    moov_start, moov_end = moov
    video_tracks: list[dict[str, object]] = []
    handlers: list[str] = []
    for kind, trak_start, trak_end in iter_boxes(data, moov_start, moov_end):
        if kind != b"trak":
            continue
        mdia = find_child(data, trak_start, trak_end, b"mdia")
        if mdia is None:
            continue
        mdia_start, mdia_end = mdia
        hdlr = find_child(data, mdia_start, mdia_end, b"hdlr")
        mdhd = find_child(data, mdia_start, mdia_end, b"mdhd")
        if hdlr is None or mdhd is None:
            continue
        handler = data[hdlr[0] + 8 : hdlr[0] + 12].decode("ascii", errors="replace")
        handlers.append(handler)
        timescale, duration = parse_duration(data, mdhd[0], mdhd[1])
        if handler == "vide":
            minf = find_child(data, mdia_start, mdia_end, b"minf")
            if minf is None:
                raise SystemExit("The MP4 video track has no media information box")
            stbl = find_child(data, minf[0], minf[1], b"stbl")
            stsd = find_child(data, stbl[0], stbl[1], b"stsd") if stbl is not None else None
            if stsd is None or stsd[0] + 8 > stsd[1]:
                raise SystemExit("The MP4 video track has no sample description")
            entry_count = struct.unpack_from(">I", data, stsd[0] + 4)[0]
            descriptions = list(iter_boxes(data, stsd[0] + 8, stsd[1]))
            if len(descriptions) != entry_count:
                raise SystemExit("The MP4 sample-description count is inconsistent")
            sample = next((entry for entry in descriptions if entry[0] in {b"avc1", b"hvc1", b"hev1"}), None)
            if sample is None or sample[1] + 28 > sample[2]:
                raise SystemExit("The MP4 video track has no recognized H.264/H.265 sample entry")
            width, height = struct.unpack_from(">HH", data, sample[1] + 24)
            video_tracks.append({
                "duration_seconds": duration / timescale,
                "timescale": timescale,
                "codec": sample[0].decode("ascii"),
                "dimensions": [width, height],
            })
    if len(video_tracks) != 1 or "soun" in handlers:
        raise SystemExit(f"Expected one video-only MP4 track, found handlers={handlers}")
    seconds = float(video_tracks[0]["duration_seconds"])
    if video_tracks[0]["dimensions"] != [1280, 720]:
        raise SystemExit(f"Expected a 1280x720 video track, got {video_tracks[0]['dimensions']}")
    if not 30.0 <= seconds <= 60.0:
        raise SystemExit(f"MP4 duration is outside 30–60 seconds: {seconds:.3f}s")
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "duration_seconds": round(seconds, 3),
        "video_tracks": 1,
        "audio_tracks": 0,
        "codec": video_tracks[0]["codec"],
        "dimensions": video_tracks[0]["dimensions"],
        "handlers": handlers,
    }


def build_video(
    captures: list[tuple[str, Path]],
    combined_frames_dir: Path,
    output_path: Path,
    repo_root: Path,
    preview_dir: Path,
) -> dict[str, object]:
    if combined_frames_dir.exists() and any(combined_frames_dir.iterdir()):
        raise SystemExit("Use a new private combined-video frame directory; existing contents are preserved")
    combined_frames_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for pack_label, capture_dir in captures:
        event_contact = Image.new("RGB", (1280 * 2, 720 * 3), "#101b24")
        event_contact_index = 0
        video_frames_dir = capture_dir / "video-frames"
        video_frames = sorted(video_frames_dir.glob("frame-*.png"))
        trace_path = capture_dir / "video-played-events.jsonl"
        entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not entries:
            raise SystemExit(f"Missing {pack_label} played-signal timeline")
        first_signal_ms = int(entries[0]["elapsed_ms"])
        selected_for_pack: set[str] = set()
        for entry in entries:
            event_name = str(entry["event"])
            if event_name not in capture_pack.REQUIRED_EVENTS or event_name in selected_for_pack:
                continue
            relative_ms = max(0, int(entry["elapsed_ms"]) - first_signal_ms - 160)
            frame_index = min(len(video_frames) - 1, max(0, round(relative_ms * VIDEO_FPS / 1000.0) + 1))
            with Image.open(video_frames[frame_index]) as image:
                keyframe = image.convert("RGB").copy()
            if keyframe.size != (1280, 720):
                raise SystemExit(f"Unexpected {pack_label} key event frame size {keyframe.size}")
            event_contact.paste(keyframe, ((event_contact_index % 2) * 1280, (event_contact_index // 2) * 720))
            event_contact_index += 1
            selected_for_pack.add(event_name)
        if selected_for_pack != capture_pack.REQUIRED_EVENTS:
            missing = sorted(capture_pack.REQUIRED_EVENTS - selected_for_pack)
            raise SystemExit(f"{pack_label} video key states are missing events: {missing}")
        if event_contact_index != len(capture_pack.REQUIRED_EVENTS):
            raise SystemExit(f"Expected six distinct video event keyframes for {pack_label}")
        preview_dir.mkdir(parents=True, exist_ok=True)
        safe_label = pack_label.lower().replace(" ", "-")
        event_contact.save(preview_dir / f"video-event-keyframes-{safe_label}.png", optimize=True)

        for frame in video_frames:
            with Image.open(frame) as opened:
                if opened.size != (1280, 720):
                    raise SystemExit(f"Unexpected {pack_label} video viewport frame {opened.size}")
            destination = combined_frames_dir / f"frame-{total:05d}.png"
            shutil.copyfile(frame, destination)
            total += 1
    encoder = repo_root / "marketing" / "video" / "encode_frames.ps1"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-File",
            str(encoder),
            "-FrameDirectory",
            str(combined_frames_dir),
            "-OutputFile",
            str(output_path),
            "-Fps",
            str(VIDEO_FPS),
            "-Bitrate",
            str(VIDEO_BITRATE),
        ],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=900,
    )
    if result.returncode != 0:
        raise SystemExit(f"Media Foundation encoding failed; private output: {result.stderr.strip()[-800:]}")
    print(result.stdout.strip())
    metadata = inspect_mp4(output_path)
    if metadata["bytes"] >= MAX_VIDEO_BYTES:
        raise SystemExit(f"Video exceeds the strict {MAX_VIDEO_BYTES:,}-byte limit")
    metadata["frames"] = total
    metadata["fps"] = VIDEO_FPS
    metadata["segment_order"] = [label for label, _ in captures]
    metadata["silent"] = True
    return metadata


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--menu-archive", required=True, type=Path, help="Private licensed Menu Kit ZIP; read for verification only")
    parser.add_argument("--sci-fi-archive", required=True, type=Path, help="Private licensed Sci-Fi ZIP; read for verification only")
    parser.add_argument("--horror-archive", required=True, type=Path, help="Private licensed Horror ZIP; read for verification only")
    parser.add_argument("--menu-capture", required=True, type=Path, help="Private Menu Kit Godot capture directory")
    parser.add_argument("--sci-fi-capture", required=True, type=Path, help="Private Sci-Fi Godot capture directory")
    parser.add_argument("--horror-capture", required=True, type=Path, help="Private Horror Godot capture directory")
    parser.add_argument("--preview-dir", required=True, type=Path, help="Private contact-sheet and combined-frame directory outside the repository")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--font-bold", type=Path, help="Installed bold font for badges")
    parser.add_argument("--font-regular", type=Path, help="Installed regular font for notes")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if repo_root != Path(__file__).resolve().parents[2]:
        raise SystemExit("Only the current checkout can be an output destination")
    preview_dir = args.preview_dir.resolve()
    if preview_dir.is_relative_to(repo_root):
        raise SystemExit("Preview sheets and intermediate video frames must stay outside the repository")

    pack_inputs = [
        ("Menu Kit", args.menu_archive.resolve(), args.menu_capture.resolve()),
        ("Sci-Fi", args.sci_fi_archive.resolve(), args.sci_fi_capture.resolve()),
        ("Horror", args.horror_archive.resolve(), args.horror_capture.resolve()),
    ]
    captures: dict[str, Path] = {}
    capture_manifests: dict[str, dict[str, object]] = {}
    for label, archive, capture_dir in pack_inputs:
        manifest, _event_map, _trace_entries = check_capture(archive, capture_dir, label)
        captures[label] = capture_dir
        capture_manifests[label] = manifest
    badge_font = font(args.font_bold, 17)
    footer_font = font(args.font_regular, 13)

    outputs: dict[str, list[dict[str, object]]] = {}
    for slug, label in (("sci-fi", "Sci-Fi"), ("horror", "Horror")):
        target = repo_root / "marketing" / "gallery" / slug
        outputs[label] = build_gallery(target, captures[label], label, PALETTES[slug], badge_font, footer_font, preview_dir)

    combined_frames_dir = preview_dir / "combined-video-frames"
    video_path = repo_root / "marketing" / "video" / VIDEO_NAME
    video_record = build_video(
        [("Menu Kit", captures["Menu Kit"]), ("Sci-Fi", captures["Sci-Fi"]), ("Horror", captures["Horror"])],
        combined_frames_dir,
        video_path,
        repo_root,
        preview_dir,
    )

    for output_list in outputs.values():
        for item in output_list:
            if item["bytes"] >= MAX_GALLERY_BYTES:
                raise SystemExit(f"Gallery item exceeded the byte limit: {item['name']}")
    public_manifest = {
        "godot_version": capture_manifests["Menu Kit"]["godot_version"],
        "display_renderer": "WSLg X11 / OpenGL compatibility; Mesa 25.2.8 llvmpipe software renderer",
        "input_method": "Synthetic Godot viewport mouse events",
        "audio_driver": "Dummy; event/resource loads verified, audible playback not tested",
        "gallery_assets": outputs,
        "video": video_record,
        "source_audio_included": False,
        "video_segment_order": ["Menu Kit", "Sci-Fi", "Horror"],
    }
    manifest_path = repo_root / "marketing" / "video" / "media-manifest.json"
    manifest_path.write_text(json.dumps(public_manifest, indent=2) + "\n", encoding="utf-8")
    for label, items in outputs.items():
        for item in items:
            print(f"ASSET_OK pack={label} name={item['name']} size={item['dimensions']} bytes={item['bytes']} sha256={item['sha256']}")
    print(
        f"VIDEO_OK name={video_record['name']} duration={video_record['duration_seconds']}s "
        f"frames={video_record['frames']} audio_tracks={video_record['audio_tracks']} bytes={video_record['bytes']}"
    )
    print(f"MANIFEST_OK {manifest_path.name}")


if __name__ == "__main__":
    main()
