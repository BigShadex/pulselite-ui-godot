#!/usr/bin/env python3
"""Render deterministic native-size and platform-size visual review frames."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--menu-root", type=Path, required=True)
    parser.add_argument("--sci-fi-root", type=Path, required=True)
    parser.add_argument("--horror-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    review = Path(__file__).resolve().parent
    out = review / "stage1"
    out.mkdir(parents=True, exist_ok=True)
    active = load_module("pulse_polish_builder", repo / "marketing/video/youtube-20261028/render_illustrative_demos.py")
    renderer = load_module("pulse_polish_stills", review / "render_stills.py")
    timeline_path = review / "cue-timeline.json"
    timeline = active.load_timeline(timeline_path)
    title_checks = active.verify_title_timing(renderer, timeline)
    endcard_checks = active.verify_endcard_routing(renderer, timeline)
    old_timeline = json.loads((repo / "marketing/video/redo-review-20261027/cue-timeline.json").read_text(encoding="utf-8"))
    mapping_keys = ("event", "source_pack", "scene", "source_relpath", "caption", "source_sha256")
    retiming_changes = []
    preserved_map_count = 0
    for section in ("menu_kit", "sci-fi", "horror", "short"):
        before_rows = old_timeline[section]["events"]
        after_rows = timeline[section]["events"]
        if len(before_rows) != len(after_rows):
            raise ValueError(f"Cue count changed in {section}")
        for before, after in zip(before_rows, after_rows, strict=True):
            if any(before.get(k) != after.get(k) for k in mapping_keys):
                raise ValueError(f"Source/event mapping changed in {section}: {before} / {after}")
            preserved_map_count += 1
            if int(before["time_ms"]) != int(after["time_ms"]):
                retiming_changes.append({"section": section, "event": after["event"],
                                         "old_time_ms": before["time_ms"], "new_time_ms": after["time_ms"]})
    if preserved_map_count != 58 or len(retiming_changes) != 4:
        raise ValueError(f"Expected 58 preserved maps and 4 intro retimes; got {preserved_map_count}/{len(retiming_changes)}")
    rapid = [int(e["time_ms"]) for e in timeline["menu_kit"]["events"]
             if 47590 <= int(e["time_ms"]) < 55000]
    if len(rapid) != 8 or any(b-a != 860 for a,b in zip(rapid,rapid[1:])):
        raise ValueError(f"Menu rapid sequence changed: {rapid}")
    rapid_check = {"count": len(rapid), "times_ms": rapid,
                   "cadence_ms": 860, "start_ms": rapid[0], "end_ms": rapid[-1]}

    roots = {
        "menu-kit": args.menu_root,
        "sci-fi-rerun1": args.sci_fi_root,
        "horror": args.horror_root,
    }
    source_rows = []
    for section in ("menu_kit", "sci-fi", "horror", "short"):
        for row in timeline[section]["events"]:
            root = roots[row["source_pack"]]
            rel = PurePosixPath(row["source_relpath"])
            if rel.is_absolute() or ".." in rel.parts or "\\" in str(row["source_relpath"]):
                raise ValueError(f"Unsafe relative audio path: {row['source_relpath']}")
            source = root.joinpath(*rel.parts).resolve()
            if root.resolve() not in source.parents:
                raise ValueError(f"Audio path escaped pack: {row['source_relpath']}")
            actual = sha(source)
            if actual != row["source_sha256"]:
                raise ValueError(f"Source OGG hash mismatch for {row['source_relpath']}")
            source_rows.append({"section": section, "event": row["event"],
                                "source_relpath": row["source_relpath"],
                                "source_sha256": actual, "time_ms": row["time_ms"]})
    if len(source_rows) != 58:
        raise ValueError(f"Expected 58 source cues; found {len(source_rows)}")

    frames = []
    def save(name: str, image: Image.Image, boxes: dict, section: str,
             time_ms: int | None = None) -> dict:
        path = out / f"{name}.jpg"
        image.convert("RGB").save(path, "JPEG", quality=93, optimize=True, subsampling=0)
        row = {"path": f"stage1/{path.name}", "sha256": sha(path),
               "bytes": path.stat().st_size, "dimensions": list(image.size),
               "section": section, "time_ms": time_ms, "bounds": boxes}
        frames.append(row)
        return row

    title_states = {
        "title-menu-kit": ("menu_kit", False), "title-sci-fi": ("sci-fi", False),
        "title-horror": ("horror", False), "title-short-three-packs": ("short", True),
    }
    for name, (section, portrait) in title_states.items():
        state = active.frame_state_at(timeline, section, 0, portrait)
        if state[1:] != ("title-card", None, None):
            raise AssertionError(f"Opening is not standalone: {name} -> {state}")
        if portrait:
            image = Image.new("RGB", renderer.PORTRAIT)
            boxes = renderer.draw_portrait_event(image, state[0], state[1], None, None)
        else:
            image, boxes = renderer.render_frame(state[0], state[1], None, None)
        save(name, image, boxes, section, 0)

    menu_state = active.frame_state_at(timeline, "menu_kit", 2800)
    main_image, main_boxes = renderer.render_frame(*menu_state)
    save("main-menu-first-cue", main_image, main_boxes, "menu_kit", 2800)
    settings_state = active.frame_state_at(timeline, "sci-fi", 14000)
    settings_image, settings_boxes = renderer.render_frame(*settings_state)
    save("settings-toggle-on", settings_image, settings_boxes, "sci-fi", 14000)
    portrait_main_state = active.frame_state_at(timeline, "short", 2800, True)
    portrait_main = Image.new("RGB", renderer.PORTRAIT)
    portrait_main_boxes = renderer.draw_portrait_event(portrait_main, *portrait_main_state)
    save("short-main-menu-first-cue", portrait_main, portrait_main_boxes, "short", 2800)
    endcard_rows = []
    for section, pack in (("menu_kit", "menu-kit"), ("sci-fi", "sci-fi"), ("horror", "horror")):
        when = int(timeline[section]["closing_card_start_ms"])
        state = active.frame_state_at(timeline, section, when)
        image, boxes = renderer.render_frame(*state)
        endcard_rows.append(save(f"endcard-{pack}", image, boxes, section, when))
    portrait_endcard = Image.new("RGB", renderer.PORTRAIT)
    portrait_endcard_boxes = renderer.draw_portrait_event(portrait_endcard, "menu-kit", "endcard", None, None)
    portrait_endcard_row = save("endcard-short-three-packs", portrait_endcard,
                                portrait_endcard_boxes, "short", 22000)

    def resize_save(name: str, image: Image.Image, size: tuple[int, int]) -> str:
        path = out / name
        image.resize(size, Image.Resampling.LANCZOS).save(path, "PNG", optimize=True)
        return f"stage1/{path.name}"
    readability = {
        "landscape_main_640x360": resize_save("readability-landscape-main-640x360.png", main_image, (640, 360)),
        "landscape_settings_640x360": resize_save("readability-landscape-settings-640x360.png", settings_image, (640, 360)),
        "portrait_main_360x640": resize_save("readability-portrait-main-360x640.png", portrait_main, (360, 640)),
        "portrait_title_360x640": resize_save("readability-portrait-title-360x640.png", Image.open(out / "title-short-three-packs.jpg"), (360, 640)),
        "portrait_endcard_360x640": resize_save("readability-portrait-endcard-360x640.png", portrait_endcard, (360, 640)),
    }
    for pack, section in (("menu-kit", "menu_kit"), ("sci-fi", "sci-fi"), ("horror", "horror")):
        path = out / f"endcard-{pack}.jpg"
        with Image.open(path) as img:
            resized = img.resize((640, 360), Image.Resampling.LANCZOS)
            target = out / f"readability-endcard-{pack}-640x360.png"
            resized.save(target, "PNG", optimize=True)
            readability[f"landscape_endcard_{pack}_640x360"] = f"stage1/{target.name}"
    title_sheet = Image.new("RGB", (1920, 360), (5, 10, 18))
    for i, name in enumerate(("title-menu-kit", "title-sci-fi", "title-horror")):
        with Image.open(out / f"{name}.jpg") as im:
            title_sheet.paste(im.resize((640, 360), Image.Resampling.LANCZOS), (i * 640, 0))
    title_sheet_path = out / "readability-opening-landscape-640x360-strip.png"
    title_sheet.save(title_sheet_path, "PNG", optimize=True)
    readability["opening_landscape_strip"] = f"stage1/{title_sheet_path.name}"
    readability["opening_portrait"] = "stage1/readability-portrait-title-360x640.png"

    draw = ImageDraw.Draw(Image.new("RGB", (2, 2)))
    checks = []
    texts = [
        ("landscape_disclosure", "Illustrative UI · procedural DSP · AI-assisted", 36, 1792, 640/1920),
        ("portrait_disclosure", "Illustrative UI · procedural DSP · AI-assisted", 36, 820, 360/1080),
        ("portrait_header", "PULSELITE  /  MENU KIT", 54, 820, 360/1080),
        ("portrait_short_title", "MENU KIT · SCI-FI · HORROR", 52, 820, 360/1080),
        ("portrait_endcard_not_included", "ILLUSTRATIVE UI — NOT INCLUDED", 36, 920, 360/1080),
        ("portrait_endcard_source_note", "SOURCE OGG · PROCEDURAL DSP · AI-ASSISTED", 36, 920, 360/1080),
        ("portrait_caption_event", "menu_confirm", 48, 820, 360/1080),
        ("portrait_caption_filename", "→  confirm_01.ogg", 48, 820, 360/1080),
    ]
    for label, text, size, max_width, scale in texts:
        font = renderer.font(size, True)
        width, height = renderer.text_size(draw, text, font)
        if width > max_width:
            raise ValueError(f"Typography overflow: {label} width={width}>{max_width}")
        checks.append({"label": label, "text": text, "font": "Arial Bold",
                       "font_size_px": size, "measured_width_px": width,
                       "measured_height_px": height, "container_width_px": max_width,
                       "rendered_width_at_target_px": round(width*scale, 1),
                       "fits": True})

    landscape_caption_widths = []
    portrait_caption_widths = []
    caption_draw = ImageDraw.Draw(Image.new("RGB", (2, 2)))
    for section in ("menu_kit", "sci-fi", "horror", "short"):
        for row in timeline[section]["events"]:
            filename = PurePosixPath(row["source_relpath"]).name
            if section == "short":
                parts = (str(row["event"]), "→  " + filename)
                widths = [renderer.text_size(caption_draw, part, renderer.font(48, True))[0] for part in parts]
                portrait_caption_widths.append({"event": row["event"], "filename": filename,
                                                "line_widths_px": widths})
                if max(widths) > 820:
                    raise ValueError(f"Portrait cue caption exceeds safe width: {row}")
            else:
                text = renderer.caption_for(str(row["event"]), filename)
                width = renderer.text_size(caption_draw, text, renderer.font(52, True))[0]
                landscape_caption_widths.append({"event": row["event"], "filename": filename,
                                                 "width_px": width})
                if width > 1690:
                    raise ValueError(f"Landscape cue caption exceeds safe width: {row}")
    caption_metrics = {
        "landscape_count": len(landscape_caption_widths),
        "landscape_max": max(landscape_caption_widths, key=lambda x: x["width_px"]),
        "landscape_container_width_px": 1690,
        "portrait_count": len(portrait_caption_widths),
        "portrait_max": max(portrait_caption_widths,
                             key=lambda x: max(x["line_widths_px"])),
        "portrait_container_width_px": 820,
        "all_captions_fit": True,
    }

    # Write the public relative-path cue manifest from the exact stage-one map.
    manifest_path = repo / "marketing/video/youtube-20261028/cue-manifest.json"
    manifest_path.write_text(json.dumps(active.public_manifest(timeline), indent=2,
                                        ensure_ascii=False) + "\n", encoding="utf-8")
    report = {
        "stage": "visual-checkpoint-1",
        "opening_title_duration_ms": 2500,
        "frame_rate_fps": 30,
        "source_cue_count": len(source_rows),
        "source_hashes_verified": len(source_rows),
        "source_event_maps_preserved_from_prior_timeline": preserved_map_count,
        "intro_retiming_only": retiming_changes,
        "menu_rapid_sequence": rapid_check,
        "source_cues": source_rows,
        "title_checks": title_checks,
        "endcard_checks": endcard_checks,
        "frames": frames,
        "readability_files": readability,
        "typography_checks": checks,
        "caption_width_checks": caption_metrics,
        "cue_timeline_sha256": sha(timeline_path),
        "renderer_sha256": sha(review / "render_stills.py"),
        "active_builder_sha256": sha(repo / "marketing/video/youtube-20261028/render_illustrative_demos.py"),
        "cue_manifest_sha256": sha(manifest_path),
        "content_notice": "No video encode or audio playback was performed for this visual checkpoint.",
    }
    (review / "stage1-review.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"frames": len(frames), "source_hashes_verified": len(source_rows),
                      "title_checks": title_checks, "endcard_checks": endcard_checks,
                      "typography_checks": checks, "caption_width_checks": caption_metrics,
                      "report": "stage1-review.json"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())