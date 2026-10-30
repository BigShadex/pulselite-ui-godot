# Paid-page gallery refresh — W11

gallery-order.json specifies three assets per listing in order: a menu shot,
the shared event/category table, and the Godot wiring snippet. It includes
captions, alt text, image dimensions, byte sizes, hashes, and source paths.
The existing menu/gallery stills are referenced in place. The two new
1920 × 1080 information panels are generated in this folder. The generator
also creates hidden 50% QA previews. The scoped .gitignore keeps them out of
the PR, and gallery-order.json contains no QA-preview paths or metadata.

## Rebuild

From the repository root, using Python 3.13 with Pillow:

    C:\Python313\python.exe -X utf8 -B marketing/weekend/gallery-refresh-20261030/build.py

The script reads the existing event map and the exact call from
marketing/visuals/demo.gd. It writes only the two panels and gallery-order.json
inside this folder. The panels use Pillow's bundled default font, so no font
files are copied or downloaded.

## Count and disclosure notes

The displayed counts are Menu Kit 200, Sci-Fi 104, Horror 104, Complete 408.
The Complete count is 200 + 104 + 104 unique WAV files. Matching OGG files are
alternate encodings, not extra sounds. The public add-on's 20 free sounds are
a subset of Menu Kit. Fourteen shared event names map to thirteen categories.

The Menu Kit capture shows the existing demo's captured played signal after
synthetic viewport input, rendered with Godot's Dummy audio driver. It is not
an audible playback or physical-pointer check. The Sci-Fi and Horror menu
receipts are static illustrative labels, not live audio. The illustrated menu
and demo scene are examples; the packs do not include a game UI or template.
Sound is procedural DSP; visuals and code/docs were AI-assisted.

Counts and their scope are grounded in
[verification.md](../../sound-lists/verification.md),
[the 26 October inventory](../../copy/2026-10-26/README.md),
[the gallery alt text](../../gallery/ALT_TEXT.md), and
[the capture notes](../../visuals/README.md). This package is a file-only
recommendation. It does not change a listing, test a new build, or claim new
live acceptance.
