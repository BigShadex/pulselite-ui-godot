# PulseLite video drafts

This folder contains three landscape H.264/AAC demo drafts, their 1280×720 thumbnails and YouTube metadata. The paired vertical Short is in `../shorts/`. The files are prepared for review and are not published automatically.

Each video uses code-drawn illustrative game menus, which are not included with the sound packs. The soundtrack is a postproduction composition from the named source-pack OGG recordings, placed at the edit-map times and encoded as AAC. Captions show the event label and exact OGG basename. These videos do not claim a new Godot capture or newly captured `played(event, path)` signal. The Menu Kit cut contains all 14 mapped event types and repeats seven mapped cues in a rapid final montage, for 21 total cue placements. Sci-Fi and Horror each contain 14 mapped cues. The public `cue-manifest.json` lists edit placements, relative source paths and source hashes; licensed audio and absolute source paths stay private.

The sound effects use procedural DSP. Code, video and text were AI-assisted. Encoded-waveform checks do not establish physical listening or human input. Parent review and the later owner/GB watch-through remain separate acceptance steps.

## Rebuild

Use the existing private pack project roots and existing PyAV module. Build into fresh output and evidence folders outside the repository, then promote only after review. The renderer refuses to overwrite MP4s.

```powershell
python marketing/video/youtube-20261028/render_illustrative_demos.py `
  --menu-root <PRIVATE_MENU_KIT_PROJECT_ROOT> `
  --sci-fi-root <PRIVATE_SCI-FI_PROJECT_ROOT> `
  --horror-root <PRIVATE_HORROR_PROJECT_ROOT> `
  --pyav-path <EXISTING_PYAV_MODULE_DIRECTORY> `
  --landscape-output <FRESH_PRIVATE_LANDSCAPE_OUTPUT> `
  --short-output <FRESH_PRIVATE_SHORT_OUTPUT> `
  --private-receipt <PRIVATE_RECEIPT_DIRECTORY> `
  --manifest-output <FRESH_PRIVATE_CUE_MANIFEST_OUTPUT> `
  --review-output <PRIVATE_REVIEW_DIRECTORY>
```

The current replacement media uses `render_illustrative_demos.py`; `capture_godot.py` and `render_media.py` remain from an earlier rejected draft and do not produce these files. Keep source packs, OGG files, capture material and full private render receipts outside Git. A curated set of final encoded frames and sanitized technical results is in `../polish-review-20261028/final-encoded/`; top-level stills there are earlier design checkpoints.
