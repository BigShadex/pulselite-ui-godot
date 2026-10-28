# Vertical Short overlays and storyboard

These PNGs are draft transparent graphics for a future 1080 × 1920 Short.
They are not video frames or a final platform-safe composition. The standalone
safe-zone guide is a conservative proposal and must be checked in the intended
app preview.

## Rebuild

Use Python with Pillow from the repository root. `ImageFont.load_default()`
uses Pillow's bundled Aileron Regular; there is no downloaded or proprietary
Windows font dependency. The builder writes native-size RGBA overlay PNGs plus
private 360 × 640 review images and text-bound measurements.

```powershell
python -B marketing/storyboard/vertical-short-20261029/build_storyboard.py `
  --output-dir marketing/storyboard/vertical-short-20261029 `
  --preview-dir <PRIVATE_PREVIEW_DIRECTORY> `
  --sample-only
```

After visual review, omit `--sample-only` and add `--overwrite` to build all
five overlays and the separate safe-zone guide. The storyboard source map names
events and files; this draft does not render or embed audio, GIF, or video.
