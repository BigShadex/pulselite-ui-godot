"""Stage a private Godot pack project and capture real played signals plus AudioEffectRecord audio."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from pathlib import Path

sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[3]
VIDEO_SUPPORT = REPO_ROOT / "marketing" / "video"
sys.path.insert(0, str(VIDEO_SUPPORT))
import capture_pack  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Private licensed pack ZIP")
    parser.add_argument("--pack-label", choices=("Menu Kit", "Sci-Fi", "Horror"), required=True)
    parser.add_argument("--mode", choices=("ui", "menu14"), default="ui")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--godot", required=True, help="Godot Linux executable path visible inside WSL")
    parser.add_argument("--output-root", type=Path, required=True, help="Fresh private output folder")
    args = parser.parse_args()
    archive = args.archive.resolve(strict=True)
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise SystemExit("Output root already exists; choose a new private directory to preserve prior evidence")
    if args.mode == "menu14" and (args.pack_label != "Menu Kit" or args.duration != 52.0):
        raise SystemExit("menu14 mode is reserved for a 52-second Menu Kit capture")
    if args.mode == "ui" and (args.pack_label == "Menu Kit" or args.duration != 20.0):
        raise SystemExit("ui mode is reserved for 20-second Sci-Fi or Horror captures")
    output_root.mkdir(parents=True)
    project_dir = output_root / "project"
    frames_dir = output_root / "frames"
    frames_dir.mkdir()
    trace_path = output_root / "played-events.jsonl"
    audio_path = output_root / "audio-effect-record.wav"
    logs_dir = output_root / "logs"
    logs_dir.mkdir()

    archive_manifest, event_map, audio_members, base_path, extension = capture_pack.check_pack_archive(archive)
    with __import__("zipfile").ZipFile(archive) as pack_zip:
        script_member = str(archive_manifest["pulse_lite_script_member"])
        script_bytes = pack_zip.read(script_member)
    deterministic_script = script_bytes.decode("utf-8-sig")
    replacements = {
        "var random_variation: bool = true": "var random_variation: bool = false",
        "var pitch_jitter: float = 0.03": "var pitch_jitter: float = 0.0",
    }
    for old, new in replacements.items():
        if old not in deterministic_script:
            raise SystemExit(f"Selected pack script did not contain expected deterministic setting: {old}")
        deterministic_script = deterministic_script.replace(old, new, 1)
    staged_hashes = capture_pack.copy_project(
        REPO_ROOT, project_dir, deterministic_script.encode("utf-8"), audio_members,
        base_path, extension, args.pack_label,
    )
    if len(staged_hashes) != int(archive_manifest["audio_member_count"]):
        raise SystemExit("Not every archive recording was staged into the private Godot project")

    private_video = project_dir / "marketing" / "video"
    private_video.mkdir(parents=True, exist_ok=True)
    for name in ("capture_driver.gd", "capture_driver.tscn"):
        (private_video / name).write_bytes((Path(__file__).parent / name).read_bytes())
    project_file = project_dir / "project.godot"
    project_text = project_file.read_text(encoding="utf-8")
    default_scene = 'run/main_scene="res://demo/demo.tscn"'
    capture_scene = 'run/main_scene="res://marketing/video/capture_driver.tscn"'
    if project_text.count(default_scene) != 1:
        raise SystemExit("Staged project main scene contract changed; refusing a broad project edit")
    project_file.write_text(project_text.replace(default_scene, capture_scene), encoding="utf-8")

    godot_version = capture_pack.run_godot(args.godot, ["--version"], logs_dir / "godot-version.log", 60).strip()
    project_linux = capture_pack.windows_to_wsl(project_dir)
    import_args = ["--headless", "--editor", "--import", "--path", project_linux, "--quit"]
    capture_pack.run_godot(args.godot, import_args, logs_dir / "godot-import.log", 240)

    args_for_godot = [
        "--path", project_linux,
        "--display-driver", "x11",
        "--rendering-method", "gl_compatibility",
        "--audio-driver", "Dummy",
        "--windowed",
        "--resolution", "1280x720",
        "--position", "5000,1000",
        "--",
        f"--mode={args.mode}",
        f"--pack-label={args.pack_label}",
        f"--duration={args.duration:.1f}",
        f"--yt-frame-dir={capture_pack.windows_to_wsl(frames_dir)}",
        f"--yt-trace-file={capture_pack.windows_to_wsl(trace_path)}",
        f"--yt-audio-file={capture_pack.windows_to_wsl(audio_path)}",
    ]
    output = capture_pack.run_godot(args.godot, args_for_godot, logs_dir / "capture.log", 420)
    capture_pack.require_marker(output, "YOUTUBE_CAPTURE_OK", logs_dir / "capture.log")
    if not audio_path.is_file() or not trace_path.is_file():
        raise SystemExit("Godot exited successfully without the requested audio and signal trace")
    trace_entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    trace_summary = capture_pack.read_trace(trace_path, event_map, staged_hashes, base_path, extension)
    observed_events = {str(row["event"]) for row in trace_entries}
    expected_events = set(event_map)
    if args.mode == "menu14" and observed_events != expected_events:
        raise SystemExit(f"Menu signal trace did not contain the full event map: {sorted(observed_events)}")
    if args.mode == "ui" and not capture_pack.REQUIRED_EVENTS.issubset(observed_events):
        raise SystemExit("UI signal trace omitted one of the required real addon events")
    frames = sorted(frames_dir.glob("frame-*.png"))
    if len(frames) < int(args.duration * 8 * 0.75):
        raise SystemExit(f"Viewport capture yielded only {len(frames)} frames")
    with wave.open(str(audio_path), "rb") as audio_file:
        wave_info = {
            "channels": audio_file.getnchannels(),
            "sample_width_bytes": audio_file.getsampwidth(),
            "sample_rate_hz": audio_file.getframerate(),
            "frames": audio_file.getnframes(),
            "duration_seconds": audio_file.getnframes() / audio_file.getframerate(),
            "compression": audio_file.getcomptype(),
        }
    receipt = {
        "pack_label": args.pack_label,
        "mode": args.mode,
        "godot_version": godot_version,
        "renderer": "WSLg X11 / Godot viewport capture",
        "audio_driver": "Godot Dummy driver with AudioEffectRecord on Master bus",
        "physical_listening_or_input": "NOT CLAIMED; scripted Godot viewport input and recorded waveform",
        "source_archive": {
            "name": archive.name,
            "bytes": archive.stat().st_size,
            "sha256": sha256(archive),
            **archive_manifest,
        },
        "pack_contract": {"base_path": base_path, "extension": extension, "event_map_count": len(event_map)},
        "staged_recording_count": len(staged_hashes),
        "staged_recordings_sha256": staged_hashes,
        "played_signal_trace": {
            "trace_count": len(trace_entries),
            "distinct_events": sorted(observed_events),
            "rows": trace_entries,
            "capture_pack_validation": trace_summary,
            "sha256": sha256(trace_path),
        },
        "audio_recording": {"name": audio_path.name, "bytes": audio_path.stat().st_size, "sha256": sha256(audio_path), **wave_info},
        "viewport_frames": {"count": len(frames), "size": [1280, 720], "fps_target": 8.0, "first": frames[0].name, "last": frames[-1].name},
        "godot_success_marker": "YOUTUBE_CAPTURE_OK",
    }
    (output_root / "capture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"CAPTURE_OK pack={args.pack_label} engine={godot_version} mode={args.mode} frames={len(frames)} events={len(observed_events)} duration={wave_info['duration_seconds']:.3f}s audio_sha256={receipt['audio_recording']['sha256']}")


if __name__ == "__main__":
    main()
