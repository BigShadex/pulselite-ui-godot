# ScreenshotSaturday stills — 31 October 2026

Three PNG stills are copied byte-for-byte from the accepted marketing/visuals
captures. They show the illustrative Mirror & Mist menu, its confirm receipt,
and the options toggle. No video or audio file is included.

The menu is illustrative and is not part of the sound pack. The confirm and
toggle captions are taken from the captured PulseLiteUI.played signal after
synthetic viewport input. The capture used Godot's Dummy audio driver; it does
not establish audible playback or physical-pointer behavior. Sound is
procedural DSP. The visuals and accompanying code/docs were AI-assisted.
Attribution for the included free-sample sounds is recorded in
LICENSE-SOUNDS at the repository root.

## Rebuild

From the repository root, use Python 3.13; the script copies the existing PNGs
and regenerates manifest.json with dimensions, byte sizes, hashes, captions,
and alt text:

    C:\Python313\python.exe -X utf8 -B marketing/weekend/screenshot-saturday-20261031/build.py

The source visuals and capture limits are documented in
marketing/visuals/README.md. See manifest.json for per-image source paths,
captions, and truthful alt text.
