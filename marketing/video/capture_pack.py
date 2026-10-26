"""Stage one licensed sound-pack ZIP privately and capture the existing Godot demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


REQUIRED_EVENTS = {
    "button_hover",
    "button_click",
    "menu_confirm",
    "menu_back",
    "toggle_on",
    "toggle_off",
}
DEMO_STILLS = ["01-main-menu.png", "02-confirm-signal.png", "03-options-toggle.png"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def windows_to_wsl(path: Path) -> str:
    text = str(path.resolve())
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", text)
    if not match:
        raise SystemExit(f"Expected a mounted Windows path, got {text!r}")
    drive, tail = match.groups()
    return f"/mnt/{drive.lower()}/{tail.replace(chr(92), '/') }"


def parse_script_map(source: str) -> dict[str, set[str]]:
    try:
        block = source.split("const EVENTS := {", 1)[1].split("\n\t}", 1)[0]
    except IndexError as error:
        raise SystemExit("Archive PulseLiteUI.gd has no expected EVENTS map") from error
    events: dict[str, set[str]] = {}
    pattern = re.compile(r'&"([^"\n]+)"\s*:\s*\[(?:true|false),\s*\[(.*?)\]\]', re.DOTALL)
    for match in pattern.finditer(block):
        events[match.group(1)] = set(re.findall(r'"([^"\n]+)"', match.group(2)))
    if not events:
        raise SystemExit("Could not parse any paths from archive PulseLiteUI.gd")
    return events


def parse_json_map(data: bytes) -> dict[str, set[str]]:
    root = json.loads(data.decode("utf-8-sig"))
    events: dict[str, set[str]] = {}
    for row in root.get("events", []):
        paths = {str(row["recommended"])}
        paths.update(str(path) for path in row.get("alternates", []))
        events[str(row["event"])] = paths
    return events


def check_pack_archive(archive_path: Path) -> tuple[dict[str, object], dict[str, set[str]], list[tuple[str, bytes]], str, str]:
    archive_hash = sha256_file(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise SystemExit(f"Archive CRC check failed at {corrupt_member}")
        names = archive.namelist()
        script_member = next((name for name in names if name.endswith("/engine/godot/PulseLiteUI.gd")), None)
        json_member = next((name for name in names if name.endswith("/ui_events.json")), None)
        if script_member is None or json_member is None:
            raise SystemExit("Archive must contain engine/godot/PulseLiteUI.gd and ui_events.json")
        pack_root = script_member.removesuffix("engine/godot/PulseLiteUI.gd")
        script_bytes = archive.read(script_member)
        json_bytes = archive.read(json_member)
        script_source = script_bytes.decode("utf-8-sig")
        script_events = parse_script_map(script_source)
        json_events = parse_json_map(json_bytes)
        for event_name, paths in json_events.items():
            if script_events.get(event_name) != paths:
                raise SystemExit(f"Script and JSON audio maps differ for {event_name}")
        for event_name in REQUIRED_EVENTS:
            if event_name not in script_events or not script_events[event_name]:
                raise SystemExit(f"Archive map is missing required event {event_name}")

        base_path_match = re.search(r'^var base_path: String\s*=\s*"([^"]+)"', script_source, re.MULTILINE)
        extension_match = re.search(r'^var extension: String\s*=\s*"([^"]+)"', script_source, re.MULTILINE)
        if base_path_match is None or extension_match is None:
            raise SystemExit("Archive PulseLiteUI.gd must declare base_path and extension defaults")
        base_path = base_path_match.group(1)
        extension = extension_match.group(1).lower()
        if not base_path.startswith("res://") or extension not in {"wav", "ogg"}:
            raise SystemExit(f"Unsupported pack audio path or extension: {base_path!r} / {extension!r}")
        archive_audio_dir = "ogg" if extension == "ogg" else "sounds"
        audio_members: list[tuple[str, bytes]] = []
        audio_prefix = f"{pack_root}{archive_audio_dir}/"
        by_relative_path: dict[str, str] = {}
        for name in names:
            if name.startswith(audio_prefix) and name.lower().endswith(f".{extension}"):
                relative = name[len(audio_prefix) :]
                by_relative_path[relative] = name
                audio_members.append((relative, archive.read(name)))
        if not audio_members:
            raise SystemExit(f"Archive has no {extension.upper()} recordings under its mapped {archive_audio_dir}/ directory")

        referenced_paths = set().union(*script_events.values())
        missing = sorted(f"{relative}.{extension}" for relative in referenced_paths if f"{relative}.{extension}" not in by_relative_path)
        if missing:
            raise SystemExit(f"PulseLiteUI.gd map references missing audio files: {missing[:8]}")

        for event_name, paths in script_events.items():
            if event_name in json_events and paths != json_events[event_name]:
                raise SystemExit(f"Audio map order/content mismatch for {event_name}")
        manifest: dict[str, object] = {
            "archive_name": archive_path.name,
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": archive_hash,
            "archive_crc": "PASS",
            "member_count": len(names),
            "pulse_lite_script_member": script_member,
            "pulse_lite_script_sha256": sha256_bytes(script_bytes),
            "ui_events_member": json_member,
            "ui_events_sha256": sha256_bytes(json_bytes),
            "base_path": base_path,
            "extension": extension,
            "audio_member_directory": archive_audio_dir,
            "audio_member_count": len(audio_members),
            "mapped_recording_count": len(referenced_paths),
            "event_map_count": len(script_events),
        }
        return manifest, script_events, audio_members, base_path, extension


def read_trace(
    trace_path: Path,
    event_map: dict[str, set[str]],
    staged_hashes: dict[str, str],
    base_path: str,
    extension: str,
) -> dict[str, object]:
    entries = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    observed_events: set[str] = set()
    for entry in entries:
        event_name = str(entry.get("event", ""))
        path = str(entry.get("path", ""))
        prefix = base_path if base_path.endswith("/") else base_path + "/"
        if not bool(entry.get("resource_exists")):
            raise SystemExit(f"Trace event {event_name} did not load a resource")
        if not path.startswith(prefix) or not path.endswith(f".{extension}"):
            raise SystemExit(f"Unexpected signal path {path!r}")
        relative = path[len(prefix) : -(len(extension) + 1)]
        if relative not in event_map.get(event_name, set()):
            raise SystemExit(f"Signal path {path} is not listed for event {event_name}")
        if relative + f".{extension}" not in staged_hashes:
            raise SystemExit(f"Signal path {path} was not byte-verified against the selected archive")
        observed_events.add(event_name)
    missing_events = sorted(REQUIRED_EVENTS - observed_events)
    if missing_events:
        raise SystemExit(f"Trace is missing required played events: {missing_events}")
    return {
        "trace_count": len(entries),
        "events": {event: sum(1 for item in entries if item["event"] == event) for event in sorted(observed_events)},
        "all_resources_exist": True,
        "all_paths_match_pack_map": True,
        "all_paths_byte_verified_against_archive": True,
        "trace_sha256": sha256_file(trace_path),
    }


def run_godot(godot: str, args: list[str], log_path: Path, timeout_seconds: int = 300) -> str:
    command = ["wsl.exe", "--exec", godot, *args]
    result = subprocess.run(command, check=False, capture_output=True, text=True, errors="replace", timeout=timeout_seconds)
    log_path.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    combined = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        raise SystemExit(f"Godot command failed with exit {result.returncode}; private log: {log_path.name}")
    return combined


def copy_project(
    repo_root: Path,
    project_dir: Path,
    script_bytes: bytes,
    audio_members: list[tuple[str, bytes]],
    base_path: str,
    extension: str,
    pack_label: str,
) -> dict[str, str]:
    project_dir.mkdir(parents=True)
    shutil.copy2(repo_root / "project.godot", project_dir / "project.godot")
    shutil.copytree(
        repo_root / "addons" / "pulselite_ui",
        project_dir / "addons" / "pulselite_ui",
        ignore=shutil.ignore_patterns("sounds", ".godot", "__pycache__"),
    )
    demo_dir = project_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "demo" / "demo.tscn", demo_dir / "demo.tscn")
    shutil.copy2(repo_root / "demo" / "demo.gd", demo_dir / "demo.gd")

    visuals_dir = project_dir / "marketing" / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("demo.gd", "demo.tscn"):
        shutil.copy2(repo_root / "marketing" / "visuals" / filename, visuals_dir / filename)
    demo_script = visuals_dir / "demo.gd"
    demo_text = demo_script.read_text(encoding="utf-8")
    existing_prefix = "res://addons/pulselite_ui/sounds/"
    if existing_prefix not in demo_text:
        raise SystemExit("The existing demo no longer has the expected playback-path display prefix")
    source_title = "FREE-SAMPLE SOUND MAPPING"
    if demo_text.count(source_title) != 1:
        raise SystemExit("The disposable demo copy no longer has its expected source-scene title")
    themed_title = f"{pack_label.upper()} SOUND MAPPING"
    demo_text = demo_text.replace(existing_prefix, base_path).replace(source_title, themed_title)
    demo_script.write_text(demo_text, encoding="utf-8")
    video_dir = project_dir / "marketing" / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("video_capture_driver.gd", "video_capture_driver.tscn"):
        shutil.copy2(repo_root / "marketing" / "video" / filename, video_dir / filename)

    addon_dir = project_dir / "addons" / "pulselite_ui"
    (addon_dir / "PulseLiteUI.gd").write_bytes(script_bytes)
    resource_root = PurePosixPath(base_path.removeprefix("res://").rstrip("/"))
    audio_root = project_dir.joinpath(*resource_root.parts)
    staged_hashes: dict[str, str] = {}
    for relative, data in audio_members:
        relative_path = PurePosixPath(relative)
        target = audio_root.joinpath(*relative_path.parts).with_suffix(f".{extension}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        digest = sha256_bytes(data)
        if sha256_file(target) != digest:
            raise SystemExit(f"Staged recording hash mismatch for {relative}")
        staged_hashes[relative] = digest
    return staged_hashes


def require_marker(output: str, marker: str, log_path: Path) -> None:
    if marker not in output:
        raise SystemExit(f"Godot did not report {marker}; private log: {log_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="Private licensed menu, Sci-Fi, or Horror ZIP")
    parser.add_argument("--pack-label", required=True, help="Short visible label for this recording pack")
    parser.add_argument("--output-root", required=True, type=Path, help="New private scratch folder outside the repository")
    parser.add_argument("--godot", required=True, help="Godot executable path as seen by WSL, for example /mnt/c/.../Godot_v4.7-stable_linux.x86_64")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--video-seconds", type=float, default=15.0)
    parser.add_argument("--video-fps", type=float, default=10.0)
    args = parser.parse_args()

    if args.pack_label not in {"Menu Kit", "Sci-Fi", "Horror"}:
        raise SystemExit("--pack-label must be Menu Kit, Sci-Fi, or Horror")

    repo_root = args.repo_root.resolve()
    archive_path = args.archive.resolve()
    output_root = args.output_root.resolve()
    if not archive_path.is_file():
        raise SystemExit("The explicitly provided private pack ZIP does not exist")
    if output_root.is_relative_to(repo_root):
        raise SystemExit("Capture outputs must stay outside the repository")
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit("Use a new or empty private output directory; existing contents are preserved")
    output_root.mkdir(parents=True, exist_ok=True)
    logs_dir = output_root / "logs"
    logs_dir.mkdir()
    project_dir = output_root / "project"
    project_linux = windows_to_wsl(project_dir)
    assets_dir = output_root / "assets"
    frames_dir = output_root / "frames"
    trace_file = output_root / "played-events.jsonl"
    video_frames_dir = output_root / "video-frames"
    video_trace_file = output_root / "video-played-events.jsonl"
    assets_dir.mkdir()
    frames_dir.mkdir()
    video_frames_dir.mkdir()

    archive_manifest, event_map, audio_members, base_path, extension = check_pack_archive(archive_path)
    script_member = str(archive_manifest["pulse_lite_script_member"])
    with zipfile.ZipFile(archive_path) as archive:
        script_bytes = archive.read(script_member)
    staged_hashes = copy_project(repo_root, project_dir, script_bytes, audio_members, base_path, extension, args.pack_label)
    if len(staged_hashes) != int(archive_manifest["audio_member_count"]):
        raise SystemExit(f"Not every archive {extension.upper()} was byte-verified in the private stage")

    version_output = subprocess.run(
        ["wsl.exe", "--exec", args.godot, "--version"],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
    )
    (logs_dir / "godot-version.log").write_text(version_output.stdout + version_output.stderr, encoding="utf-8")
    if version_output.returncode != 0:
        raise SystemExit("Could not read the explicitly selected Godot version")
    godot_version = version_output.stdout.strip().splitlines()[0]

    import_output = run_godot(
        args.godot,
        ["--headless", "--path", project_linux, "--editor", "--import", "--quit"],
        logs_dir / "resource-import.log",
    )
    if "ERROR:" in import_output or "SCRIPT ERROR" in import_output:
        raise SystemExit("Godot resource import reported an error; see the private import log")

    assets_linux = windows_to_wsl(assets_dir)
    frames_linux = windows_to_wsl(frames_dir)
    trace_linux = windows_to_wsl(trace_file)
    still_args = [
        "--path",
        project_linux,
        "--display-driver",
        "x11",
        "--rendering-method",
        "gl_compatibility",
        "--audio-driver",
        "Dummy",
        "--windowed",
        "--resolution",
        "1280x720",
        "--position",
        "5000,1000",
        "res://marketing/visuals/demo.tscn",
        "--",
        f"--asset-dir={assets_linux}",
        f"--frame-dir={frames_linux}",
        f"--trace-file={trace_linux}",
    ]
    still_log = logs_dir / "viewport-capture.log"
    still_output = run_godot(args.godot, still_args, still_log, timeout_seconds=180)
    require_marker(still_output, "A027_CAPTURE_OK", still_log)
    still_trace = read_trace(trace_file, event_map, staged_hashes, base_path, extension)
    for name in DEMO_STILLS:
        if not (assets_dir / name).is_file():
            raise SystemExit(f"A027 capture omitted expected still {name}")
    if len(list(frames_dir.glob("frame-*.png"))) != 9:
        raise SystemExit("A027 capture did not produce exactly nine event-sequence frames")

    video_frames_linux = windows_to_wsl(video_frames_dir)
    video_trace_linux = windows_to_wsl(video_trace_file)
    video_args = [
        "--path",
        project_linux,
        "--display-driver",
        "x11",
        "--rendering-method",
        "gl_compatibility",
        "--audio-driver",
        "Dummy",
        "--windowed",
        "--resolution",
        "1280x720",
        "--position",
        "5000,1000",
        "res://marketing/video/video_capture_driver.tscn",
        "--",
        f"--video-output-dir={video_frames_linux}",
        f"--trace-file={video_trace_linux}",
        f"--pack-label={args.pack_label}",
        f"--video-seconds={args.video_seconds}",
        f"--video-fps={args.video_fps}",
    ]
    video_log = logs_dir / "continuous-viewport-capture.log"
    video_output = run_godot(args.godot, video_args, video_log, timeout_seconds=240)
    require_marker(video_output, "VIDEO_CAPTURE_OK", video_log)
    video_trace = read_trace(video_trace_file, event_map, staged_hashes, base_path, extension)
    video_frames = sorted(video_frames_dir.glob("frame-*.png"))
    if len(video_frames) < int(args.video_seconds * args.video_fps * 0.75):
        raise SystemExit(f"Continuous capture produced too few viewport frames: {len(video_frames)}")

    capture_manifest = {
        "pack_label": args.pack_label,
        "capture_scene_title": f"{args.pack_label.upper()} SOUND MAPPING",
        "archive": archive_manifest,
        "godot_version": godot_version,
        "renderer": "WSLg X11 / OpenGL compatibility",
        "input_mode": "synthetic Godot viewport mouse events",
        "audio_driver": "Dummy; loaded stream and played signal only, not audible acceptance",
        "private_stage_audio_files": len(staged_hashes),
        "staged_audio_sha256": staged_hashes,
        "gallery_capture": {
            **still_trace,
            "viewport_frames": len(list(frames_dir.glob("frame-*.png"))),
            "public_stills": DEMO_STILLS,
        },
        "continuous_video_capture": {
            **video_trace,
            "viewport_frames": len(video_frames),
            "requested_seconds": args.video_seconds,
            "requested_fps": args.video_fps,
            "pack_label_in_frame": True,
            "signal_and_file_caption_in_frame": True,
        },
    }
    (output_root / "capture-manifest.json").write_text(json.dumps(capture_manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"CAPTURE_OK pack={args.pack_label!r} godot={godot_version} extension={extension} audio_files={len(staged_hashes)} "
        f"gallery_events={still_trace['trace_count']} video_events={video_trace['trace_count']} video_frames={len(video_frames)}"
    )
    print("AUDIO_NOTE Dummy driver confirms loaded resources and played signals; it does not prove audible playback.")


if __name__ == "__main__":
    main()
