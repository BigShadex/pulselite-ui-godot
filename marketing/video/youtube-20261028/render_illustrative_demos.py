#!/usr/bin/env python3
"""Build the current illustrative PulseLite demos from private source OGGs.

Menus are code-drawn by the sibling review renderer. Audio is a deterministic
postproduction mix of the supplied source OGG files at the public edit-map
times. This script does not capture Godot or claim live signal provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
sys.dont_write_bytecode = True
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from PIL import Image, ImageDraw, ImageOps


FPS = 30
RATE = 48_000
BASE_GAIN = 0.55
FADE_MS = 8
TRUE_PEAK_OVERSAMPLE = 4
TARGET_TRUE_PEAK_DBTP = -1.0
TARGET_TRUE_PEAK = 10 ** (TARGET_TRUE_PEAK_DBTP / 20.0)
GLOBAL_GAIN_MIN = 0.25
GLOBAL_GAIN_MAX = 16.0
TITLE_CARD_END_MS = 2500
H_SIZE = (1920, 1080)
V_SIZE = (1080, 1920)
REVIEW_SAMPLES = (0,)
LANDSCAPE_META = {
    "menu_kit": {
        "id": "pulselite-menu-kit-14-events",
        "title": "14 UI Events in 60 Seconds | PulseLite Menu Kit",
        "pack": "menu-kit", "product": "https://bigshadex.itch.io/pulselite-ui-sfx",
        "short_title": "14 UI EVENTS", "sub_title": "MENU KIT | 60 SECONDS",
    },
    "sci-fi": {
        "id": "pulselite-sci-fi-ui-sounds",
        "title": "Sci-Fi UI Sound Effects | PulseLite",
        "pack": "sci-fi", "product": "https://bigshadex.itch.io/pulselite-scifi-ui",
        "short_title": "SCI-FI UI\nSOUNDS", "sub_title": "SCI-FI PACK DEMO",
    },
    "horror": {
        "id": "pulselite-horror-ui-sounds",
        "title": "Horror UI Sound Effects | PulseLite",
        "pack": "horror", "product": "https://bigshadex.itch.io/pulselite-horror-ui",
        "short_title": "HORROR UI\nSOUNDS", "sub_title": "HORROR PACK DEMO",
    },
}
SHORT_ID = "pulselite-menu-scifi-horror-short"
PREVIEW_URL = "https://bigshadex.github.io/pulselite-previewer/"
PACK_ROOT_KEYS = {
    "menu-kit": "menu-kit", "sci-fi-rerun1": "sci-fi", "horror": "horror",
}
PACK_LABELS = {"menu-kit": "Menu Kit", "sci-fi": "Sci-Fi", "horror": "Horror"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_renderer(path: Path):
    spec = importlib.util.spec_from_file_location("pulse_redo_stills", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load sibling renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_av(path: Path):
    sys.path.insert(0, str(path))
    import av  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]
    if not hasattr(av, "AudioResampler"):
        raise RuntimeError("PyAV installation does not expose AudioResampler")
    return av, np


def normalize_pack(source_pack: str) -> str:
    try:
        return PACK_ROOT_KEYS[source_pack]
    except KeyError as exc:
        raise ValueError(f"Unknown source pack in timeline: {source_pack}") from exc


def load_timeline(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("format") != 1:
        raise ValueError(f"Unsupported edit timeline format: {obj.get('format')}")
    expected = {"menu_kit": 21, "sci-fi": 14, "horror": 14, "short": 9}
    for key, count in expected.items():
        data = obj[key]
        entries = data["events"]
        if len(entries) != count:
            raise ValueError(f"{key} has {len(entries)} cues; expected {count}")
        title_end = int(data.get("title_card_end_ms", -1))
        if title_end != TITLE_CARD_END_MS:
            raise ValueError(f"{key} title card ends at {title_end}ms; expected {TITLE_CARD_END_MS}ms")
        previous = -1
        for row in entries:
            ms = int(row["time_ms"])
            if ms <= previous:
                raise ValueError(f"Non-increasing cue timeline in {key}")
            previous = ms
            if not str(row["source_relpath"]).lower().endswith(".ogg"):
                raise ValueError(f"Cue is not mapped to an OGG: {row}")
        if int(entries[0]["time_ms"]) < title_end + 200:
            raise ValueError(f"{key} first cue overlaps or crowds its standalone title card")
        card_start = int(data.get("closing_card_start_ms", data.get("endcard_start_ms", data["duration_ms"])))
        if int(data["duration_ms"]) - card_start < 3000:
            raise ValueError(f"{key} endcard dwell is shorter than 3 seconds")
    return obj

def safe_source(root: Path, relpath: str) -> Path:
    rel = PurePosixPath(relpath)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relpath:
        raise ValueError(f"Unsafe relative source path: {relpath}")
    path = root.joinpath(*rel.parts).resolve()
    resolved_root = root.resolve()
    if path != resolved_root and resolved_root not in path.parents:
        raise ValueError(f"Source escapes staged pack root: {relpath}")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def decode_ogg(av, np, path: Path) -> Any:
    container = av.open(str(path), "r")
    streams = [stream for stream in container.streams if stream.type == "audio"]
    if len(streams) != 1:
        container.close()
        raise ValueError(f"Expected exactly one audio track in {path.name}")
    resampler = av.AudioResampler(format="fltp", layout="stereo", rate=RATE)
    chunks = []
    for frame in container.decode(streams[0]):
        for converted in resampler.resample(frame):
            chunks.append(converted.to_ndarray().T.astype(np.float32, copy=True))
    for converted in resampler.resample(None):
        chunks.append(converted.to_ndarray().T.astype(np.float32, copy=True))
    container.close()
    if not chunks:
        raise ValueError(f"No decoded audio samples in {path.name}")
    return np.concatenate(chunks, axis=0)


def estimate_true_peak(np, audio: Any, factor: int = TRUE_PEAK_OVERSAMPLE) -> float:
    """Estimate inter-sample peak with deterministic polyphase oversampling."""
    from scipy.signal import resample_poly
    if audio.size == 0:
        return 0.0
    signal = np.asarray(audio, dtype=np.float32)
    oversampled = resample_poly(signal, factor, 1, axis=0, window=("kaiser", 8.6), padtype="line")
    return float(np.max(np.abs(oversampled)))


def mix_track(av, np, rows: list[dict[str, Any]], roots: dict[str, Path],
              duration_ms: int) -> tuple[Any, list[dict[str, Any]], float, dict[str, float]]:
    sample_count = duration_ms * RATE // 1000
    mix = np.zeros((sample_count, 2), dtype=np.float32)
    staged: list[tuple[dict[str, Any], Any, dict[str, Any]]] = []
    fade_samples_default = FADE_MS * RATE // 1000
    for row in rows:
        source_pack = str(row["source_pack"])
        root_key = normalize_pack(source_pack)
        source_path = safe_source(roots[root_key], str(row["source_relpath"]))
        source_sha = digest(source_path)
        expected_sha = str(row["source_sha256"]).lower()
        if source_sha != expected_sha:
            raise ValueError(f"Source hash mismatch for {row['source_relpath']}: {source_sha}")
        decoded = decode_ogg(av, np, source_path)
        onset = int(row["time_ms"]) * RATE // 1000
        if onset < 0 or onset >= sample_count:
            raise ValueError(f"Cue onset outside video duration: {row}")
        source_len = len(decoded)
        used = min(source_len, sample_count - onset)
        fade_samples = min(fade_samples_default, used // 2)
        processed = decoded[:used].copy()
        if fade_samples:
            processed[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples, endpoint=True, dtype=np.float32)[:, None]
            processed[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, endpoint=True, dtype=np.float32)[:, None]
        processed *= BASE_GAIN
        mix[onset:onset + used] += processed
        staged.append((row, processed, {
            "source_path": str(source_path), "source_relpath": str(row["source_relpath"]),
            "source_sha256": source_sha, "source_pack": source_pack,
            "normalized_pack": root_key, "event": str(row["event"]),
            "caption": str(row["caption"]), "scene": str(row["scene"]),
            "start_ms": int(row["time_ms"]), "start_sample": onset,
            "source_samples_decoded": source_len, "source_samples_used": used,
            "tail_truncated": used != source_len, "sample_rate": RATE,
            "base_gain": BASE_GAIN, "fade_samples_each_edge": fade_samples,
        }))
    raw_sample_peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    raw_true_peak = estimate_true_peak(np, mix)
    requested_gain = TARGET_TRUE_PEAK / max(raw_true_peak, 1e-12)
    global_gain = min(GLOBAL_GAIN_MAX, max(GLOBAL_GAIN_MIN, requested_gain))
    mix *= global_gain
    final_true_peak = estimate_true_peak(np, mix)
    final_true_peak_db = 20.0 * math.log10(max(final_true_peak, 1e-12))
    if abs(final_true_peak_db - TARGET_TRUE_PEAK_DBTP) > 0.05:
        raise ValueError(f"Bounded global gain cannot reach target true peak: {final_true_peak_db:.3f} dBTP")
    level = {"raw_sample_peak": raw_sample_peak, "raw_oversampled_true_peak": raw_true_peak,
             "requested_global_gain": requested_gain, "global_gain": global_gain,
             "final_pcm_sample_peak": float(np.max(np.abs(mix))),
             "final_pcm_oversampled_true_peak": final_true_peak,
             "final_pcm_oversampled_true_peak_dbtp": final_true_peak_db,
             "target_true_peak_dbtp": TARGET_TRUE_PEAK_DBTP,
             "oversample_factor": TRUE_PEAK_OVERSAMPLE}
    events: list[dict[str, Any]] = []
    for row, processed, data in staged:
        data["global_gain"] = global_gain
        data["effective_gain"] = BASE_GAIN * global_gain
        data["processed_source_pcm_sha256"] = hashlib.sha256(processed.astype("<f4", copy=False).tobytes()).hexdigest()
        data["processed_peak_before_global_gain"] = float(np.max(np.abs(processed))) if processed.size else 0.0
        events.append(data)
    return mix, events, global_gain, level

def event_map_at(events: list[dict[str, Any]], time_ms: int) -> dict[str, Any] | None:
    current = None
    for row in events:
        if int(row["time_ms"]) <= time_ms:
            current = row
        else:
            break
    return current


def frame_state_at(timeline: dict[str, Any], section: str, time_ms: int,
                   portrait: bool = False) -> tuple[str, str, str | None, str | None]:
    data = timeline[section]
    rows = data["events"]
    endcard_ms = int(data.get("endcard_start_ms", data.get("closing_card_start_ms", data["duration_ms"])))
    first_pack = normalize_pack(str(rows[0]["source_pack"])) if rows else "menu-kit"
    title_end = int(data.get("title_card_end_ms", TITLE_CARD_END_MS))
    if time_ms < title_end:
        return first_pack, "title-card", None, None
    if time_ms >= endcard_ms:
        if portrait:
            return "menu-kit", "endcard", None, None
        return first_pack, "endcard", None, None
    latest = event_map_at(rows, time_ms)
    if latest is None:
        return first_pack, "menu", None, None
    return (normalize_pack(str(latest["source_pack"])), str(latest["scene"]),
            str(latest["event"]), PurePosixPath(str(latest["source_relpath"])).name)

def render_frame_state(renderer, state: tuple[str, str, str | None, str | None],
                       portrait: bool = False) -> Image.Image:
    pack, scene, event, filename = state
    if portrait:
        image = Image.new("RGB", renderer.PORTRAIT)
        renderer.draw_portrait_event(image, pack, scene, event, filename)
        return image
    image, _ = renderer.render_frame(pack, scene, event, filename)
    return image


def verify_title_timing(renderer, timeline: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for section in ("menu_kit", "sci-fi", "horror", "short"):
        data = timeline[section]
        first = data["events"][0]
        title_end = int(data["title_card_end_ms"])
        portrait = section == "short"
        before = frame_state_at(timeline, section, title_end - 1, portrait)
        at_end = frame_state_at(timeline, section, title_end, portrait)
        at_cue = frame_state_at(timeline, section, int(first["time_ms"]), portrait)
        if before[1:] != ("title-card", None, None):
            raise AssertionError(f"{section} opening is not a standalone title card")
        if at_end[1:] != ("menu", None, None):
            raise AssertionError(f"{section} has a cue/caption behind its title card")
        if at_cue[2] != first["event"] or int(first["time_ms"]) < title_end + 200:
            raise AssertionError(f"{section} first cue and visual timing are not aligned")
        state = frame_state_at(timeline, section, 0, portrait)
        image = render_frame_state(renderer, state, portrait)
        if image.size != (renderer.PORTRAIT if portrait else renderer.LANDSCAPE):
            raise AssertionError(f"{section} title card dimensions are incorrect")
        checks.append({"section": section, "title_card_end_ms": title_end,
                       "first_cue_ms": int(first["time_ms"]),
                       "first_event": first["event"], "dimensions": list(image.size)})
    return checks


def verify_endcard_routing(renderer, timeline: dict[str, Any]) -> list[dict[str, Any]]:
    expected_packs = {"menu_kit": "menu-kit", "sci-fi": "sci-fi", "horror": "horror"}
    expected_paths = {"menu-kit": "/pulselite-ui-sfx", "sci-fi": "/pulselite-scifi-ui",
                      "horror": "/pulselite-horror-ui"}
    checks = []
    for section, expected_pack in expected_packs.items():
        endcard_ms = int(timeline[section]["closing_card_start_ms"])
        state = frame_state_at(timeline, section, endcard_ms, portrait=False)
        if state != (expected_pack, "endcard", None, None):
            raise AssertionError(f"{section} endcard routed to {state[0]}; expected {expected_pack}")
        product_path = renderer.PRODUCT_PATHS[expected_pack]
        if product_path != expected_paths[expected_pack]:
            raise AssertionError(f"{section} points to {product_path}; expected {expected_paths[expected_pack]}")
        image = render_frame_state(renderer, state)
        direct, _ = renderer.render_frame(expected_pack, "endcard", None, None)
        if image.size != renderer.LANDSCAPE or image.tobytes() != direct.tobytes():
            raise AssertionError(f"{section} did not render its direct {expected_pack} endcard")
        checks.append({"section": section, "endcard_pack": expected_pack,
                       "product_path": product_path, "dimensions": list(image.size),
                       "render_sha256": hashlib.sha256(image.tobytes()).hexdigest()})
    if len({item["render_sha256"] for item in checks}) != 3:
        raise AssertionError("Landscape endcards did not render as three distinct pack cards")
    short_state = frame_state_at(timeline, "short", int(timeline["short"]["endcard_start_ms"]), portrait=True)
    if short_state != ("menu-kit", "endcard", None, None):
        raise AssertionError("Combined portrait endcard routing changed unexpectedly")
    return checks


def render_sequence(renderer, timeline: dict[str, Any], section: str,
                    duration_ms: int, portrait: bool = False) -> Iterator[Image.Image]:
    cache: dict[tuple[Any, ...], Image.Image] = {}
    for frame_index in range(duration_ms * FPS // 1000):
        time_ms = frame_index * 1000 // FPS
        pack, scene, event, filename = frame_state_at(timeline, section, time_ms, portrait)
        key = (pack, scene, event, filename)
        if key not in cache:
            cache[key] = render_frame_state(renderer, (pack, scene, event, filename), portrait)
        yield cache[key]


def encode_mp4(av, np, out_path: Path, title: str, duration_ms: int,
               frames: Iterator[Image.Image], audio: Any, size: tuple[int, int]) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        raise FileExistsError(f"Refusing to overwrite staged output: {out_path}")
    container = av.open(str(out_path), "w", format="mp4", options={"movflags": "+faststart"})
    video = container.add_stream("libx264", rate=FPS)
    video.width, video.height = size
    video.pix_fmt = "yuv420p"
    video.bit_rate = 1_850_000 if size == H_SIZE else 1_000_000
    video.options = {"preset": "veryfast", "crf": "20", "profile": "high", "bf": "0"}
    audio_stream = container.add_stream("aac", rate=RATE)
    audio_stream.layout = "stereo"
    audio_stream.bit_rate = 112_000
    container.metadata.update({
        "title": title,
        "comment": "Code-drawn illustrative menus; source OGG audio composition; AI-assisted video and text.",
    })
    packets: list[tuple[float, Any]] = []
    expected_frames = duration_ms * FPS // 1000
    seen = 0
    for index, image in enumerate(frames):
        if index >= expected_frames:
            raise RuntimeError("Frame generator exceeded the requested duration")
        if image.size != size:
            raise ValueError(f"Wrong frame dimensions {image.size}; expected {size}")
        frame = av.VideoFrame.from_image(image.convert("RGB"))
        frame.pts = index
        frame.time_base = Fraction(1, FPS)
        for packet in video.encode(frame):
            stamp = packet.dts if packet.dts is not None else packet.pts
            packets.append((float(stamp * packet.time_base), packet))
        seen += 1
    if seen != expected_frames:
        raise RuntimeError(f"Encoded {seen} frames, expected {expected_frames}")
    for packet in video.encode(None):
        stamp = packet.dts if packet.dts is not None else packet.pts
        packets.append((float(stamp * packet.time_base), packet))
    for start in range(0, len(audio), 1024):
        chunk = audio[start:start + 1024]
        if len(chunk) < 1024:
            padded = np.zeros((1024, 2), dtype=np.float32)
            padded[:len(chunk)] = chunk
            chunk = padded
        frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(chunk.T), format="fltp", layout="stereo")
        frame.sample_rate = RATE
        frame.pts = start
        frame.time_base = Fraction(1, RATE)
        for packet in audio_stream.encode(frame):
            stamp = packet.dts if packet.dts is not None else packet.pts
            packets.append((float(stamp * packet.time_base), packet))
    for packet in audio_stream.encode(None):
        stamp = packet.dts if packet.dts is not None else packet.pts
        packets.append((float(stamp * packet.time_base), packet))
    packets.sort(key=lambda item: (item[0], 0 if item[1].stream.type == "video" else 1))
    for _, packet in packets:
        container.mux(packet)
    container.close()
    return {"path": str(out_path), "bytes": out_path.stat().st_size,
            "sha256": digest(out_path), "video_frames_expected": expected_frames,
            "audio_samples_expected": len(audio)}


def normalized_cross_correlation(np, decoded: Any, template: Any, expected_sample: int,
                                 tolerance_samples: int) -> dict[str, Any]:
    signal = decoded.astype(np.float32, copy=False)
    cue = template.astype(np.float32, copy=False)
    if signal.ndim == 2:
        signal = signal.mean(axis=1)
    if cue.ndim == 2:
        cue = cue.mean(axis=1)
    if not len(cue):
        raise ValueError("Empty correlation template")
    low = max(0, expected_sample - tolerance_samples)
    high = min(len(signal), expected_sample + tolerance_samples + len(cue))
    candidate = signal[low:high]
    if len(candidate) < len(cue):
        raise ValueError("Decoded AAC is shorter than a cue correlation window")
    valid = len(candidate) - len(cue) + 1
    nfft = 1 << (len(candidate) + len(cue) - 2).bit_length()
    convolution = np.fft.irfft(np.fft.rfft(candidate, nfft) * np.fft.rfft(cue[::-1], nfft), nfft)
    corr = convolution[len(cue) - 1:len(cue) - 1 + valid]
    energy = np.concatenate(([0.0], np.cumsum(candidate.astype(np.float64) ** 2)))
    windows = energy[len(cue):len(cue) + valid] - energy[:valid]
    cue_energy = float(np.sum(cue.astype(np.float64) ** 2))
    denom = np.sqrt(np.maximum(windows * cue_energy, 1e-24))
    scores = np.clip(corr / denom, -1.0, 1.0)
    scores[windows < max(cue_energy * 1e-6, 1e-12)] = 0.0
    best = int(np.argmax(np.abs(scores)))
    found = low + best
    delta = found - expected_sample
    return {"expected_sample": expected_sample, "matched_sample": found,
            "delta_samples": delta, "delta_ms": delta * 1000.0 / RATE,
            "absolute_correlation": float(abs(scores[best])),
            "within_80ms": abs(delta) <= tolerance_samples}


def verify_mp4(av, np, path: Path, duration_ms: int, size: tuple[int, int],
               events: list[dict[str, Any]], templates: list[Any],
               allow_overpeak: bool = False) -> tuple[dict[str, Any], Any, list[Any]]:
    container = av.open(str(path), "r")
    videos = [stream for stream in container.streams if stream.type == "video"]
    audios = [stream for stream in container.streams if stream.type == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        container.close()
        raise ValueError(f"Expected one video and one AAC track: {path}")
    video, audio = videos[0], audios[0]
    if (video.codec_context.name, video.codec_context.width, video.codec_context.height,
            video.codec_context.format.name) != ("h264", size[0], size[1], "yuv420p"):
        container.close()
        raise ValueError(f"Unexpected video encoding in {path.name}")
    if audio.codec_context.name != "aac" or audio.codec_context.sample_rate != RATE:
        container.close()
        raise ValueError(f"Unexpected audio encoding in {path.name}")
    frames = 0
    audio_parts = []
    resampler = av.AudioResampler(format="fltp", layout="stereo", rate=RATE)
    sample_peak = 0.0
    square_sum = 0.0
    sample_values = 0
    for packet in container.demux(video, audio):
        for frame in packet.decode():
            if packet.stream.type == "video":
                frames += 1
            else:
                for converted in resampler.resample(frame):
                    data = converted.to_ndarray().T.astype(np.float32, copy=True)
                    audio_parts.append(data)
                    sample_peak = max(sample_peak, float(np.max(np.abs(data))))
                    square_sum += float(np.sum(data.astype(np.float64) ** 2))
                    sample_values += data.size
    for converted in resampler.resample(None):
        data = converted.to_ndarray().T.astype(np.float32, copy=True)
        audio_parts.append(data)
        sample_peak = max(sample_peak, float(np.max(np.abs(data))))
        square_sum += float(np.sum(data.astype(np.float64) ** 2))
        sample_values += data.size
    container.close()
    expected_frames = duration_ms * FPS // 1000
    if frames != expected_frames:
        raise ValueError(f"{path.name}: {frames} decoded video frames; expected {expected_frames}")
    decoded_audio = np.concatenate(audio_parts, axis=0) if audio_parts else np.zeros((0, 2), np.float32)
    expected_samples = duration_ms * RATE // 1000
    if len(decoded_audio) < int(expected_samples * 0.97) or len(decoded_audio) > expected_samples + RATE // 4:
        raise ValueError(f"{path.name}: decoded audio length {len(decoded_audio)} unexpected for {expected_samples}")
    rms = math.sqrt(square_sum / max(sample_values, 1))
    aac_true_peak = estimate_true_peak(np, decoded_audio)
    aac_true_peak_dbtp = 20.0 * math.log10(max(aac_true_peak, 1e-12))
    if sample_peak < 0.01 or rms < 0.0001 or (not allow_overpeak and (sample_peak > 1.0 or aac_true_peak > 1.0)):
        raise ValueError(f"{path.name}: AAC waveform invalid sample_peak={sample_peak:.6f}, true_peak={aac_true_peak_dbtp:.3f} dBTP, RMS={rms:.6f}")
    correlations = []
    for event, template in zip(events, templates, strict=True):
        correlations.append(normalized_cross_correlation(np, decoded_audio, template,
                               int(event["start_sample"]), RATE * 80 // 1000))
    if any(not row["within_80ms"] or row["absolute_correlation"] < 0.15 for row in correlations):
        raise ValueError(f"{path.name}: cue correlation outside tolerance or too weak: {correlations}")
    return ({"container": "MP4", "video_codec": "H.264", "video_pixel_format": "yuv420p",
             "dimensions": list(size), "fps": FPS, "video_frames_decoded": frames,
             "duration_seconds_from_frames": frames / FPS, "audio_codec": "AAC",
             "audio_rate_hz": RATE, "audio_samples_decoded": len(decoded_audio),
             "decoded_audio_sample_peak": sample_peak,
             "decoded_audio_oversampled_true_peak": aac_true_peak,
             "decoded_audio_oversampled_true_peak_dbtp": aac_true_peak_dbtp,
             "true_peak_oversample_factor": TRUE_PEAK_OVERSAMPLE,
             "decoded_audio_rms": rms, "cue_correlations": correlations,
             "bytes": path.stat().st_size, "sha256": digest(path)}, decoded_audio, [])


def video_packet_sha256(av, path: Path) -> str:
    container = av.open(str(path), "r")
    streams = [stream for stream in container.streams if stream.type == "video"]
    if len(streams) != 1:
        container.close()
        raise ValueError(f"Expected one video stream in {path.name}")
    digestor = hashlib.sha256()
    packet_count = 0
    for packet in container.demux(streams[0]):
        if packet.size:
            digestor.update(bytes(packet))
            packet_count += 1
    container.close()
    if not packet_count:
        raise ValueError(f"No video packets in {path.name}")
    return digestor.hexdigest()


def remux_aac_gain(av, np, source_path: Path, temp_path: Path, gain: float) -> dict[str, Any]:
    """Scale decoded AAC and re-encode only audio, preserving H.264 packets."""
    if temp_path.exists():
        raise FileExistsError(f"Refusing to overwrite AAC correction output: {temp_path}")
    source_video_hash = video_packet_sha256(av, source_path)
    input_container = av.open(str(source_path), "r")
    videos = [stream for stream in input_container.streams if stream.type == "video"]
    audios = [stream for stream in input_container.streams if stream.type == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        input_container.close()
        raise ValueError(f"Expected one video and one audio track in {source_path.name}")
    output_container = av.open(str(temp_path), "w", format="mp4", options={"movflags": "+faststart"})
    output_video = output_container.add_stream_from_template(videos[0])
    output_audio = output_container.add_stream("aac", rate=RATE)
    output_audio.layout = "stereo"
    output_audio.bit_rate = 112_000
    output_container.metadata.update(input_container.metadata)
    resampler = av.AudioResampler(format="fltp", layout="stereo", rate=RATE)
    audio_chunks = []
    mux_packets: list[tuple[float, int, Any]] = []
    try:
        for packet in input_container.demux(videos[0], audios[0]):
            if packet.stream.type == "video":
                if packet.size and packet.dts is not None:
                    timestamp = float(packet.dts * packet.time_base)
                    packet.stream = output_video
                    mux_packets.append((timestamp, 0, packet))
            elif packet.stream.type == "audio":
                for frame in packet.decode():
                    for converted in resampler.resample(frame):
                        audio_chunks.append(converted.to_ndarray().T.astype(np.float32, copy=True))
        for converted in resampler.resample(None):
            audio_chunks.append(converted.to_ndarray().T.astype(np.float32, copy=True))
        if not audio_chunks:
            raise ValueError(f"No decoded AAC to correct in {source_path.name}")
        decoded = np.concatenate(audio_chunks, axis=0)
        if len(decoded) < RATE:
            raise ValueError("Decoded audio unexpectedly short during AAC correction")
        decoded *= float(gain)
        for start in range(0, len(decoded), 1024):
            chunk = decoded[start:start + 1024]
            if len(chunk) < 1024:
                padded = np.zeros((1024, 2), dtype=np.float32)
                padded[:len(chunk)] = chunk
                chunk = padded
            frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(chunk.T), format="fltp", layout="stereo")
            frame.sample_rate = RATE
            frame.pts = start
            frame.time_base = Fraction(1, RATE)
            for packet in output_audio.encode(frame):
                stamp = packet.dts if packet.dts is not None else packet.pts
                mux_packets.append((float(stamp * packet.time_base), 1, packet))
        for packet in output_audio.encode(None):
            stamp = packet.dts if packet.dts is not None else packet.pts
            mux_packets.append((float(stamp * packet.time_base), 1, packet))
        mux_packets.sort(key=lambda item: (item[0], item[1]))
        for _, _, packet in mux_packets:
            output_container.mux(packet)
    except Exception:
        output_container.close()
        input_container.close()
        raise
    output_container.close()
    input_container.close()
    corrected_video_hash = video_packet_sha256(av, temp_path)
    if corrected_video_hash != source_video_hash:
        raise ValueError("AAC-only correction changed the H.264 video packet stream")
    return {"source_video_packets_sha256": source_video_hash,
            "corrected_video_packets_sha256": corrected_video_hash,
            "video_packets_identical": True,
            "audio_gain": float(gain), "output_bytes": temp_path.stat().st_size,
            "output_sha256": digest(temp_path)}


def ensure_aac_target(av, np, path: Path, duration_ms: int, size: tuple[int, int],
                      events: list[dict[str, Any]], templates: list[Any]) -> tuple[dict[str, Any], Any, list[dict[str, Any]]]:
    """Bound AAC-only correction to two passes, then enforce level and clipping."""
    corrections = []
    verified, decoded, _ = verify_mp4(av, np, path, duration_ms, size, events, templates,
                                      allow_overpeak=True)
    for attempt in range(2):
        peak_db = float(verified["decoded_audio_oversampled_true_peak_dbtp"])
        if -1.3 <= peak_db <= -0.7 and verified["decoded_audio_sample_peak"] <= 1.0:
            break
        desired_gain = TARGET_TRUE_PEAK / max(float(verified["decoded_audio_oversampled_true_peak"]), 1e-12)
        correction_gain = min(2.0, max(0.5, desired_gain))
        temp_path = path.with_name(f"{path.stem}.aac-correction-{attempt + 1}.tmp.mp4")
        before_sha = digest(path)
        correction = remux_aac_gain(av, np, path, temp_path, correction_gain)
        os.replace(temp_path, path)
        correction.update({"attempt": attempt + 1, "before_sha256": before_sha,
                          "after_sha256": digest(path), "before_true_peak_dbtp": peak_db})
        corrections.append(correction)
        verified, decoded, _ = verify_mp4(av, np, path, duration_ms, size, events, templates,
                                          allow_overpeak=True)
    final_db = float(verified["decoded_audio_oversampled_true_peak_dbtp"])
    final_sample_peak = float(verified["decoded_audio_sample_peak"])
    if not (-1.3 <= final_db <= -0.7) or final_sample_peak > 1.0 or float(verified["decoded_audio_oversampled_true_peak"]) > 1.0:
        raise ValueError(f"AAC true peak/sample clipping remains outside target after {len(corrections)} correction(s): {final_db:.3f} dBTP, sample peak {final_sample_peak:.6f}")
    return verified, decoded, corrections

def save_thumbnails(renderer, out_landscape: Path, out_short: Path) -> list[dict[str, Any]]:
    out_landscape.mkdir(parents=True, exist_ok=True)
    out_short.mkdir(parents=True, exist_ok=True)
    reports = []
    for key, data in LANDSCAPE_META.items():
        base, _ = renderer.render_frame(data["pack"], "menu", None, None)
        image = base.resize((1280, 720), Image.Resampling.LANCZOS).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle((34, 40, 635, 682), radius=28, fill=(5, 11, 21, 228), outline=(80, 110, 132, 235), width=3)
        pack_name = PACK_LABELS[data["pack"]].upper()
        draw.text((76, 86), "PULSELITE", font=renderer.font(36, True), fill=(95, 224, 244, 255))
        draw.text((76, 150), pack_name, font=renderer.font(36, True), fill=(198, 217, 229, 255))
        title_lines = data["short_title"].split("\n")
        y = 242
        title_font = renderer.font(84 if len(title_lines) == 1 else 78, True)
        for line in title_lines:
            draw.text((72, y), line, font=title_font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(5, 10, 17, 255))
            y += 92
        draw.text((78, y + 9), data["sub_title"], font=renderer.font(31, True), fill=(244, 199, 110, 255))
        draw.text((78, 626), "ILLUSTRATIVE UI | AUDIO DEMO", font=renderer.font(22, True), fill=(177, 196, 207, 255))
        image = Image.alpha_composite(image, overlay).convert("RGB")
        path = out_landscape / f"{data['id']}.png"
        image.save(path, format="PNG", optimize=True)
        reports.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path), "dimensions": list(image.size)})

    image = Image.new("RGB", (1280, 720), (7, 14, 27))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 38, 526, 682), radius=28, fill=(9, 19, 33), outline=(45, 95, 123), width=3)
    draw.text((64, 93), "PULSELITE", font=renderer.font(40, True), fill=(95, 224, 244))
    draw.text((64, 184), "3 WORLDS", font=renderer.font(84, True), fill=(255, 255, 255))
    draw.text((66, 290), "UI SOUND", font=renderer.font(74, True), fill=(255, 255, 255))
    draw.text((66, 384), "EFFECTS", font=renderer.font(74, True), fill=(255, 255, 255))
    draw.text((66, 498), "MENU KIT / SCI-FI / HORROR", font=renderer.font(26, True), fill=(244, 199, 110))
    draw.text((66, 621), "ILLUSTRATIVE UI | AUDIO DEMO", font=renderer.font(21, True), fill=(177, 196, 207))
    cards = [("menu-kit", "menu", "button_click", "click_03.ogg"),
             ("sci-fi", "gameplay", "level_up", "level_up_01.ogg"),
             ("horror", "shop", "error", "error_01.ogg")]
    for i, (pack, scene, event, filename) in enumerate(cards):
        card = Image.new("RGB", renderer.PORTRAIT)
        renderer.draw_portrait_event(card, pack, scene, event, filename)
        card = ImageOps.fit(card, (214, 565), method=Image.Resampling.LANCZOS)
        x = 548 + i * 238
        image.paste(card, (x, 78))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((x - 2, 76, x + 216, 645), radius=8, outline=renderer.PALETTES[pack]["accent"], width=3)
        draw.text((x + 8, 654), PACK_LABELS[pack].upper(), font=renderer.font(19, True), fill=renderer.PALETTES[pack]["accent"])
    path = out_short / f"{SHORT_ID}.png"
    image.save(path, format="PNG", optimize=True)
    reports.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path), "dimensions": list(image.size)})
    if any(row["bytes"] > 3 * 1024 * 1024 for row in reports):
        raise ValueError("A thumbnail exceeds the 3 MB limit")
    return reports


def public_manifest(timeline: dict[str, Any]) -> dict[str, Any]:
    manifests = []
    for key in ("menu_kit", "sci-fi", "horror", "short"):
        section = timeline[key]
        events = []
        for row in section["events"]:
            events.append({
                "time_ms": int(row["time_ms"]), "source_pack": row["source_pack"],
                "scene": row["scene"], "event": row["event"],
                "caption": row["caption"], "source_relpath": row["source_relpath"],
                "source_sha256": row["source_sha256"],
            })
        video_id = SHORT_ID if key == "short" else LANDSCAPE_META[key]["id"]
        duration_ms = int(section["duration_ms"])
        manifests.append({"video": video_id, "duration_ms": duration_ms,
                          "title_card_end_ms": int(section["title_card_end_ms"]),
                          "audio_note": "The timestamps are edit placements for source OGG composition, not newly captured live signal events.",
                          "events": events})
    return {"format": 1, "title": "PulseLite illustrative video cue manifest",
            "source_path_policy": "Relative paths and source hashes only; raw licensed audio and absolute paths are not included.",
            "videos": manifests}


def ids_for_review() -> dict[str, str]:
    return {"menu_kit": LANDSCAPE_META["menu_kit"]["id"],
            "sci-fi": LANDSCAPE_META["sci-fi"]["id"],
            "horror": LANDSCAPE_META["horror"]["id"], "short": SHORT_ID}


def write_metadata(output_dirs: dict[str, Path]) -> None:
    preview = f"Preview the mapped sound effects: {PREVIEW_URL}"
    for key, data in LANDSCAPE_META.items():
        product_name = PACK_LABELS[data["pack"]]
        desc = (
            f"A {product_name} sound demonstration with one on-screen caption per cue. "
            "The interface scenes are code-drawn illustrations and are not included with the sound pack. "
            "The audio is a postproduction composition from the named source-pack OGG recordings, placed on an edit timeline. "
            "The sound effects use procedural DSP. Code, video, and text were AI-assisted.\n\n"
            f"{preview}\n{product_name} pack: {data['product']}"
        )
        tags = ["PulseLite", "UI sound effects", "game UI audio", "illustrative menu demo",
                f"{product_name} UI sounds", "procedural DSP audio", "sound design"]
        p = output_dirs["landscape"] / f"{data['id']}.metadata.md"
        p.write_text(f"# YouTube metadata\n\nTitle: {data['title']}\n\nDescription:\n{desc}\n\nTags:\n" + ", ".join(tags) + "\n", encoding="utf-8")
    short_title = "Menu Kit to Sci-Fi to Horror UI Sounds | PulseLite #Shorts"
    short_desc = (
        "Three packs, three illustrated game-menu themes, and nine individually captioned sound cues. "
        "Screens are code-drawn illustrations and are not included with the sound packs. "
        "The soundtrack is a postproduction composition from the named source-pack OGG recordings, placed on an edit timeline. "
        "The sound effects use procedural DSP. Code, video, and text were AI-assisted.\n\n"
        f"Previewer: {PREVIEW_URL}\n"
        f"Menu Kit: {LANDSCAPE_META['menu_kit']['product']}\n"
        f"Sci-Fi: {LANDSCAPE_META['sci-fi']['product']}\n"
        f"Horror: {LANDSCAPE_META['horror']['product']}"
    )
    tags = ["PulseLite", "YouTube Shorts", "UI sound effects", "illustrative menu demo",
            "Menu Kit", "Sci-Fi UI sounds", "Horror UI sounds", "procedural DSP audio"]
    p = output_dirs["short"] / f"{SHORT_ID}.metadata.md"
    p.write_text(f"# YouTube metadata\n\nTitle: {short_title}\n\nDescription:\n{short_desc}\n\nTags:\n" + ", ".join(tags) + "\n", encoding="utf-8")


def extract_review_frames(av, path: Path, rows: list[dict[str, Any]], duration_ms: int,
                          out_dir: Path, name: str, portrait: bool,
                          expected_endcard: Image.Image, np) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    desired: dict[int, str] = {0: "opening"}
    for row in rows:
        frame = int(int(row["time_ms"]) * FPS / 1000)
        desired[frame] = f"cue-{row['event']}-{PurePosixPath(str(row['source_relpath'])).stem}"
    endcard_ms = 22_000 if portrait else (55_000 if "menu-kit" in name else 26_000)
    desired[int(endcard_ms * FPS / 1000)] = "endcard"
    desired[duration_ms * FPS // 1000 - 1] = "last-frame"
    container = av.open(str(path), "r")
    videos = [stream for stream in container.streams if stream.type == "video"]
    if len(videos) != 1:
        container.close()
        raise ValueError(f"Could not extract frames from {path.name}")
    stream = videos[0]
    saved = []
    for index, frame in enumerate(container.decode(stream)):
        label = desired.get(index)
        if label is None:
            continue
        image = frame.to_image().convert("RGB")
        if portrait != (image.size == V_SIZE):
            raise ValueError(f"Decoded frame orientation mismatch in {path.name} at {index}")
        output = out_dir / f"{name}-{index:04d}-{label}.jpg"
        image.save(output, format="JPEG", quality=86, optimize=True)
        record = {"path": str(output), "frame": index, "time_seconds": index / FPS,
                      "label": label, "bytes": output.stat().st_size, "sha256": digest(output),
                      "dimensions": list(image.size)}
        if label == "endcard":
            expected = np.asarray(expected_endcard.convert("RGB"), dtype=np.int16)
            actual = np.asarray(image, dtype=np.int16)
            mean_abs_error = float(np.mean(np.abs(actual - expected)))
            if mean_abs_error > 8.0:
                raise ValueError(f"Encoded {name} endcard differs from its selected pack render (MAE {mean_abs_error:.3f})")
            record["mean_abs_error_to_expected_pack_endcard"] = mean_abs_error
        saved.append(record)
    container.close()
    missing = set(desired) - {row["frame"] for row in saved}
    if missing:
        raise ValueError(f"Missing decoded review frames from {path.name}: {sorted(missing)}")
    if any(row["bytes"] > 500 * 1024 for row in saved):
        raise ValueError(f"Oversized review JPEG for {path.name}")
    return saved


def make_review_sheets(av, final_frames: list[dict[str, Any]], thumbnail_reports: list[dict[str, Any]],
                       review_dir: Path) -> None:
    review_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for row in final_frames:
        im = Image.open(row["path"]).convert("RGB")
        im.thumbnail((420, 236), Image.Resampling.LANCZOS)
        items.append((im.copy(), f"{Path(row['path']).name}  {row['time_seconds']:.2f}s"))
    columns = 4
    cell_w, cell_h = 440, 270
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (15, 22, 32))
    draw = ImageDraw.Draw(sheet)
    for i, (image, label) in enumerate(items):
        x, y = (i % columns) * cell_w, (i // columns) * cell_h
        sheet.paste(image, (x + 8, y + 4))
        draw.text((x + 8, y + 244), label[:68], fill=(230, 237, 242))
    sheet.save(review_dir / "final-encoded-contact-sheet.jpg", format="JPEG", quality=88, optimize=True)
    thumb_items = []
    for row in thumbnail_reports:
        im = Image.open(row["path"]).convert("RGB").resize((320, 180), Image.Resampling.LANCZOS)
        thumb_items.append((im, Path(row["path"]).name))
    thumbsheet = Image.new("RGB", (640, math.ceil(len(thumb_items) / 2) * 210), (15, 22, 32))
    draw = ImageDraw.Draw(thumbsheet)
    for i, (image, label) in enumerate(thumb_items):
        x, y = (i % 2) * 320, (i // 2) * 210
        thumbsheet.paste(image, (x, y))
        draw.text((x + 3, y + 182), label, fill=(230, 237, 242))
    thumbsheet.save(review_dir / "thumbnails-320-contact-sheet.jpg", format="JPEG", quality=90, optimize=True)


def build_one(av, np, renderer, timeline: dict[str, Any], section: str,
              output_dir: Path, roots: dict[str, Path], private_dir: Path,
              stage_label: str) -> tuple[dict[str, Any], list[Any]]:
    data = timeline[section]
    duration_ms = int(data["duration_ms"])
    portrait = section == "short"
    size = V_SIZE if portrait else H_SIZE
    rows = list(data["events"])
    audio, events, global_gain, audio_level = mix_track(av, np, rows, roots, duration_ms)
    pcm_hash = hashlib.sha256(audio.astype("<f4", copy=False).tobytes()).hexdigest()
    if section == "short":
        name, title = SHORT_ID, "Menu Kit to Sci-Fi to Horror UI Sounds | PulseLite Shorts"
    else:
        name = LANDSCAPE_META[section]["id"]
        title = LANDSCAPE_META[section]["title"]
    target = output_dir / f"{name}.mp4"
    frame_iter = render_sequence(renderer, timeline, section, duration_ms, portrait=portrait)
    encoded = encode_mp4(av, np, target, title, duration_ms, frame_iter, audio, size)
    expected_templates = []
    for event in events:
        source = safe_source(roots[event["normalized_pack"]], event["source_relpath"])
        decoded = decode_ogg(av, np, source)
        used = int(event["source_samples_used"])
        onset = int(event["start_sample"])
        fade = int(event["fade_samples_each_edge"])
        processed = decoded[:used].copy()
        if fade:
            processed[:fade] *= np.linspace(0.0, 1.0, fade, endpoint=True, dtype=np.float32)[:, None]
            processed[-fade:] *= np.linspace(1.0, 0.0, fade, endpoint=True, dtype=np.float32)[:, None]
        processed *= float(event["effective_gain"])
        expected_templates.append(processed)
    verified, decoded, aac_corrections = ensure_aac_target(av, np, target, duration_ms, size, events, expected_templates)
    if aac_corrections:
        encoded["initial_encode_sha256"] = aac_corrections[0]["before_sha256"]
    encoded.update({"bytes": verified["bytes"], "sha256": verified["sha256"],
                    "final_path": verified["path"], "aac_correction_count": len(aac_corrections)})
    report = {"video": name, "section": section, "duration_ms": duration_ms,
              "dimensions": list(size), "fps": FPS, "source_event_count": len(events),
              "base_gain": BASE_GAIN, "fade_ms": FADE_MS,
              "audio_level": audio_level, "global_gain": global_gain,
              "mix_pcm_sha256": pcm_hash, "encoded": encoded, "verified": verified,
              "aac_corrections": aac_corrections,
              "events": events}
    return report, expected_templates


def smoke_test(av, np, renderer, roots: dict[str, Path], out: Path) -> dict[str, Any]:
    row = {"time_ms": 1000, "source_pack": "menu-kit", "scene": "menu", "event": "button_click",
           "caption": "button_click  →  click_03.ogg", "source_relpath": "audio/pulselite/click/click_03.ogg",
           "source_sha256": "83327998a360d3aed6682e526333bd2739cd1ae37d6fc6b7059f9400db3008ef"}
    path = safe_source(roots["menu-kit"], row["source_relpath"])
    if digest(path) != row["source_sha256"]:
        raise ValueError("Smoke source hash did not match the accepted edit map")
    samples = decode_ogg(av, np, path)
    audio = np.zeros((4 * RATE, 2), np.float32)
    fade = min(FADE_MS * RATE // 1000, len(samples) // 2)
    processed = samples.copy()
    if fade:
        processed[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        processed[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
    processed *= BASE_GAIN
    onset = RATE
    audio[onset:onset + len(processed)] += processed
    raw_true_peak = estimate_true_peak(np, audio)
    requested_gain = TARGET_TRUE_PEAK / max(raw_true_peak, 1e-12)
    global_gain = min(GLOBAL_GAIN_MAX, max(GLOBAL_GAIN_MIN, requested_gain))
    audio *= global_gain
    pcm_true_peak = estimate_true_peak(np, audio)
    pcm_db = 20.0 * math.log10(max(pcm_true_peak, 1e-12))
    if abs(pcm_db - TARGET_TRUE_PEAK_DBTP) > 0.05:
        raise ValueError(f"Smoke bounded gain misses true-peak target: {pcm_db:.3f} dBTP (raw={raw_true_peak:.6f}, requested={requested_gain:.4f}, bounded={global_gain:.4f})")
    def frames():
        image, _ = renderer.render_frame("menu-kit", "menu", None, None)
        yield from [image] * 30
        image, _ = renderer.render_frame("menu-kit", "menu", "button_click", "click_03.ogg")
        yield from [image] * 90
    output = out / "codec-smoke.mp4"
    encoded = encode_mp4(av, np, output, "Codec smoke only", 4000, frames(), audio, H_SIZE)
    event = {"start_sample": onset}
    verified, _, corrections = ensure_aac_target(av, np, output, 4000, H_SIZE,
                                                  [event], [processed * global_gain])
    if corrections:
        encoded["initial_encode_sha256"] = corrections[0]["before_sha256"]
    encoded.update({"bytes": verified["bytes"], "sha256": verified["sha256"],
                    "final_path": verified["path"], "aac_correction_count": len(corrections)})
    return {"encoded": encoded, "verified": verified,
            "aac_corrections": corrections,
            "audio_level": {"raw_pcm_true_peak": raw_true_peak,
                            "requested_global_gain": requested_gain,
                            "global_gain": global_gain,
                            "pcm_true_peak": pcm_true_peak,
                            "pcm_true_peak_dbtp": pcm_db,
                            "target_true_peak_dbtp": TARGET_TRUE_PEAK_DBTP,
                            "global_gain_max": GLOBAL_GAIN_MAX}}

def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--menu-root", type=Path, required=True)
    parser.add_argument("--sci-fi-root", type=Path, required=True)
    parser.add_argument("--horror-root", type=Path, required=True)
    parser.add_argument("--pyav-path", type=Path, required=True)
    parser.add_argument("--landscape-output", type=Path, required=True)
    parser.add_argument("--short-output", type=Path, required=True)
    parser.add_argument("--private-receipt", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path,
                        help="Write the generated public cue manifest to a staging path instead of the repository file")
    parser.add_argument("--only", choices=["menu_kit", "sci-fi", "horror", "short"], action="append")
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    review_root = repo / "marketing/video/polish-review-20261028"
    renderer_path = review_root / "render_stills.py"
    timeline_path = review_root / "cue-timeline.json"
    renderer = load_renderer(renderer_path)
    timeline = load_timeline(timeline_path)
    title_checks = verify_title_timing(renderer, timeline)
    print("TITLE_TIMING_PASS " + json.dumps(title_checks, ensure_ascii=False))
    endcard_checks = verify_endcard_routing(renderer, timeline)
    print("ENDCARD_ROUTING_PASS " + json.dumps(endcard_checks, ensure_ascii=False))
    av, np = load_av(args.pyav_path)
    roots = {"menu-kit": args.menu_root.resolve(), "sci-fi": args.sci_fi_root.resolve(),
             "horror": args.horror_root.resolve()}
    args.landscape_output.mkdir(parents=True, exist_ok=True)
    args.short_output.mkdir(parents=True, exist_ok=True)
    args.private_receipt.mkdir(parents=True, exist_ok=True)
    args.review_output.mkdir(parents=True, exist_ok=True)
    if args.smoke_only:
        result = smoke_test(av, np, renderer, roots, args.private_receipt)
        result["endcard_routing_checks"] = endcard_checks
        path = args.private_receipt / "codec-smoke-receipt.json"
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"smoke": result["verified"], "receipt": str(path)}, indent=2))
        return 0
    selected = args.only or ["menu_kit", "sci-fi", "horror", "short"]
    reports = []
    all_final_frames = []
    for section in selected:
        out_dir = args.short_output if section == "short" else args.landscape_output
        report, _ = build_one(av, np, renderer, timeline, section, out_dir, roots, args.private_receipt, "final")
        rows = timeline[section]["events"]
        frames_dir = args.review_output / "final-encoded-frames"
        endcard_time = int(timeline[section].get("endcard_start_ms", timeline[section].get("closing_card_start_ms", report["duration_ms"])))
        expected_card = render_frame_state(renderer, frame_state_at(timeline, section, endcard_time, section == "short"), section == "short")
        captured = extract_review_frames(av, Path(report["encoded"]["path"]), rows,
                    report["duration_ms"], frames_dir, report["video"], section == "short", expected_card, np)
        report["review_frames"] = captured
        all_final_frames.extend(captured)
        reports.append(report)
        print(f"ENCODED {section}: {report['encoded']['bytes']} bytes, SHA256 {report['encoded']['sha256']}")
        if report["encoded"]["bytes"] > 20 * 1024 * 1024:
            print(f"WARNING: {section} exceeds the preferred 20 MB size")
    if not args.only:
        thumbnail_reports = save_thumbnails(renderer, args.landscape_output, args.short_output)
        write_metadata({"landscape": args.landscape_output, "short": args.short_output})
        manifest_path = args.manifest_output or (repo / "marketing/video/youtube-20261028/cue-manifest.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(public_manifest(timeline), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        make_review_sheets(av, all_final_frames, thumbnail_reports, args.review_output)
    else:
        thumbnail_reports = []
        for section, ident in ids_for_review().items():
            public_dir = repo / ("marketing/video/shorts" if section == "short" else "marketing/video/youtube-20261028")
            thumb_path = public_dir / f"{ident}.png"
            with Image.open(thumb_path) as thumbnail:
                thumbnail_reports.append({"path": str(thumb_path), "bytes": thumb_path.stat().st_size,
                                          "sha256": digest(thumb_path), "dimensions": list(thumbnail.size)})
        make_review_sheets(av, all_final_frames, thumbnail_reports, args.review_output)
    receipt = {
        "task": "CDX media redo: source OGG composition into code-drawn illustrative demos",
        "captured_live_godot_signal_claim": False,
        "fps": FPS, "sample_rate_hz": RATE, "codec": "H.264 yuv420p + AAC",
        "base_gain": BASE_GAIN, "fade_ms_each_edge": FADE_MS,
        "true_peak_target_dbtp": TARGET_TRUE_PEAK_DBTP,
        "true_peak_oversample_factor": TRUE_PEAK_OVERSAMPLE,
        "aac_correction_method": "Decode AAC, apply bounded constant scalar gain, re-encode AAC; H.264 packet stream must remain byte-identical.",
        "aac_correction_max_passes": 2,
        "global_gain_bounds": [GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX],
        "source_roots": {key: str(value) for key, value in roots.items()},
        "timeline_sha256": digest(timeline_path),
        "renderer_sha256": digest(renderer_path),
        "manifest_sha256": digest(args.manifest_output or (repo / "marketing/video/youtube-20261028/cue-manifest.json")),
        "title_timing_checks": title_checks,
        "endcard_routing_checks": endcard_checks,
        "pyav_version": av.__version__, "numpy_version": np.__version__,
        "videos": reports, "thumbnails": thumbnail_reports,
    }
    receipt_path = args.private_receipt / "final-media-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"videos": [{"id": x["video"], "sha256": x["encoded"]["sha256"],
             "bytes": x["encoded"]["bytes"], "correlations": len(x["verified"]["cue_correlations"])} for x in reports],
             "thumbnails": thumbnail_reports, "receipt": str(receipt_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
