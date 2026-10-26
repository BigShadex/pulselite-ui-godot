# Themed gallery media

The Sci-Fi and Horror gallery folders contain three 630 px wide stills and an 8-frame animated GIF each. The MP4 follows the captured Menu Kit, Sci-Fi, then Horror scenes. Each capture uses the existing Godot demo, synthetic viewport mouse events, and the selected pack's `PulseLiteUI.played(event, path)` signal for its event/file caption. These are illustrative interface examples; the packs do not include a game UI.

The private capture project stages the selected archive's OGG recordings so the real addon can load and trigger them. The gallery and MP4 contain no audio recordings or audio track. Captures were made with Godot 4.7 under WSLg/X11 using Mesa 25.2.8 llvmpipe, with the Dummy audio driver. The signal/resource checks do not demonstrate audible playback or physical mouse input.

## Rebuild

Use the private licensed pack ZIPs as inputs. Keep capture folders and preview frames outside the repository and supply fresh output directories.

```powershell
python marketing/video/capture_pack.py `
  --archive <PRIVATE_PACK_ZIP> `
  --pack-label <MENU_KIT_OR_SCI-FI_OR_HORROR> `
  --output-root <NEW_PRIVATE_CAPTURE_DIRECTORY> `
  --godot <GODOT_EXECUTABLE_PATH_AS_SEEN_BY_WSL>

python marketing/video/build_media.py `
  --menu-archive <PRIVATE_MENU_ZIP> `
  --sci-fi-archive <PRIVATE_SCI-FI_ZIP> `
  --horror-archive <PRIVATE_HORROR_ZIP> `
  --menu-capture <PRIVATE_MENU_CAPTURE> `
  --sci-fi-capture <PRIVATE_SCI-FI_CAPTURE> `
  --horror-capture <PRIVATE_HORROR_CAPTURE> `
  --preview-dir <NEW_PRIVATE_PREVIEW_DIRECTORY>
```

`capture_pack.py` runs Godot through WSL. `build_media.py` creates the gallery assets and uses Windows Media Foundation to encode the silent H.264 MP4. `media-manifest.json` records output hashes, dimensions, durations, capture mode, and audio limitations.
