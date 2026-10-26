# Menu Kit gallery exports

These three stills and the silent loop are derived from the merged A027 Godot viewport captures in [`marketing/visuals`](../../visuals/README.md). Each 630-pixel-wide card stacks a crop of the real menu/button area above a separate crop of the playback-receipt panel. The first shows the real `menu_confirm` / `confirm/confirm_06.wav` caption, the second `toggle_on` / `toggle/toggle_01.wav`, and the third the final captured `menu_back` / `back_cancel/back_cancel_01.wav` frame. The GIF uses that same two-part crop across the original nine capture frames. No event, file caption, or menu control was invented.

Every asset has a clearly visible **Illustrative example** badge and the existing caveat that the sound pack does not include a game UI. The cards are not an included UI or game template. They use only existing free-sample sounds also present in the Menu Kit; they do not preview the Sci-Fi or Horror recordings. All output files are below the strict 3,000,000-byte limit.

| Asset | Dimensions | Bytes |
|---|---:|---:|
| `menu-kit-01-confirm.png` | 630 × 953 | 102,988 |
| `menu-kit-02-toggle-on.png` | 630 × 953 | 102,146 |
| `menu-kit-03-menu-back.png` | 630 × 953 | 163,530 |
| `menu-kit-gallery.gif` | 630 × 953; 9 frames; 7.6 seconds; silent loop | 1,004,494 |

The label, full menu/button context, and receipt text were inspected at the assets' native 630-pixel width. The still contact sheet and three keyframe contact sheets (covering all nine GIF frames) were also opened at 630-pixel width; each frame retains its actual event/file caption, the **Illustrative example** badge, and the no-game-UI caveat. The events were exercised through synthetic Godot viewport input in the source capture. This is not physical-pointer testing or an audible playback check.

Sound attribution: **PulseLite UI SFX by Bigshadex** ([free sample](https://bigshadex.itch.io/pulselite-ui-sfx-free)), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [`LICENSE-SOUNDS`](../../../LICENSE-SOUNDS) for the complete attribution terms.

## Rebuild

From the repository root, run the build script with Python and Pillow (verified with Python 3.12.14 / Pillow 12.3.0). Point `--preview-dir` to a private writable folder; on Windows, the installed Arial fonts keep the badge and note legible at 630 pixels.

```powershell
$preview = Join-Path $env:TEMP 'menu-kit-gallery-previews'
python marketing/gallery/menu-kit/build_gallery.py --source-dir marketing/visuals --output-dir marketing/gallery/menu-kit --preview-dir $preview --font-bold C:/Windows/Fonts/arialbd.ttf --font-regular C:/Windows/Fonts/arial.ttf
```

The builder uses only the existing PNG/GIF renders and Pillow. It writes the three labelled stills, the nine-frame GIF, and private 630-pixel contact sheets; Godot does not need to be rerun for this derived export.
