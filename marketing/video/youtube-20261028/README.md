# YouTube demo assets

This folder holds three ready-to-review H.264/AAC demos, 1280x720 PNG thumbnails, per-video metadata drafts, and generic capture/render scripts. The paired vertical short and its metadata are in `../shorts/`.

The videos use exact source-pack recordings staged privately from the selected licensed ZIPs. `capture_godot.py` imports those recordings into a disposable Godot project, captures the illustrative UI, records the addon's `played(event, path)` signal, and preserves the Godot `AudioEffectRecord` mix as private QA evidence. The UI replay is scripted. A disposable copy disables random variation and pitch jitter so each event uses the deterministic recommended-file route; the source pack ZIP and repository addon remain untouched.

The final soundtrack is postproduced from the exact staged OGG named by each `played` trace row. Each clip is placed at that row's captured `elapsed_ms`, so the displayed signal and sound start together without Dummy-driver clock drift. Repeated signal rows are all mixed, with an 8 ms edge fade and a deterministic per-event gain; a single global gain is applied only if needed to keep the mix peak at or below 0.90. The original captured Godot WAV is not used as the final soundtrack. Private receipts record each source hash, signal time, placement, gain, fades, PCM hash, and encoded checks. This demonstrates encoded waveform and trace alignment, not physical listening or human input. The sound effects are procedurally DSP-generated; video preparation used AI assistance. The illustrative Godot UI is not included with the sound packs.

Each video ends with the applicable itch.io product link and the public sound previewer. Metadata drafts are separate `.metadata.md` files so titles, descriptions, and tags can be copied into a future YouTube upload. Nothing in this folder is published automatically.

## Rebuild

Use private, licensed pack ZIPs and fresh directories outside the repository. The capture script takes a Godot Linux executable path as WSL sees it; the Python and archive/output paths remain native Windows paths.

```powershell
$godot = '/mnt/c/path/to/Godot_v4.7-stable_linux.x86_64'
python marketing/video/youtube-20261028/capture_godot.py `
  --archive <PRIVATE_MENU_KIT_ZIP> --pack-label 'Menu Kit' --mode menu14 --duration 52 `
  --godot $godot --output-root <FRESH_PRIVATE_MENU_CAPTURE>
python marketing/video/youtube-20261028/capture_godot.py `
  --archive <PRIVATE_SCI-FI_ZIP> --pack-label Sci-Fi --mode ui --duration 20 `
  --godot $godot --output-root <FRESH_PRIVATE_SCI-FI_CAPTURE>
python marketing/video/youtube-20261028/capture_godot.py `
  --archive <PRIVATE_HORROR_ZIP> --pack-label Horror --mode ui --duration 20 `
  --godot $godot --output-root <FRESH_PRIVATE_HORROR_CAPTURE>
python marketing/video/youtube-20261028/render_media.py `
  --menu-capture <PRIVATE_MENU_CAPTURE> --sci-fi-capture <PRIVATE_SCI-FI_CAPTURE> `
  --horror-capture <PRIVATE_HORROR_CAPTURE> `
  --youtube-output marketing/video/youtube-20261028 `
  --shorts-output marketing/video/shorts `
  --pyav-path <EXISTING_PYAV_MODULE_DIRECTORY> --private-output <PRIVATE_RECEIPT_DIRECTORY>
```

The render script expects Pillow, NumPy, SciPy, and PyAV in the selected Python environment. Capture receipts, WAVs, private frame sequences, staged OGG files, and pack ZIPs should stay outside Git. Thumbnails and metadata can be regenerated alongside fresh output files; the scripts refuse to overwrite existing MP4s.
