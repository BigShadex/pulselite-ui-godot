# PulseLite Sci-Fi and Horror gallery stills

The new `sci-fi/04-*.png` through `07-*.png` and `horror/04-*.png` through
`07-*.png` files are original code-drawn game-menu illustrations at 1920 x
1080. They use theme colors, typography, and simple geometric shapes. No game
capture, source audio, stock art, or third-party illustration is embedded.
Event and OGG names are static example labels, not a claim that the sound was
played in the pictured UI. The illustrated interface is not included with the
sound packs. Sound descriptions remain procedural DSP; these illustrations
were AI-assisted.

## Build and preview

From the repository root, use Python with Pillow. `ImageFont.load_default()`
uses Pillow's bundled Aileron Regular; no Windows font lookup or font download
is needed. The font source and terms are recorded in the repository's
[`CREDITS.txt`](../../CREDITS.txt).

```powershell
python -B marketing/gallery/build_theme_gallery.py `
  --output-dir marketing/gallery `
  --preview-dir <PRIVATE_PREVIEW_DIRECTORY> `
  --sample-only
```

The sample option renders the first new image for each theme. After review,
omit `--sample-only` and add `--overwrite` to rebuild all eight new images,
including the two reviewed samples. The private preview folder receives
640 x 360 reductions, a contact sheet, and measured text bounds. PNGs are
deterministic for a fixed Pillow/Python version and use no random content.
