# PulseLite video polish review

This folder is the active illustrative renderer and cue-timing map for the four video drafts. It is separate from `redo-review-20261027`, which preserves the rejected-version evidence.

`render_illustrative_demos.py` loads `render_stills.py` and `cue-timeline.json` from this folder. The map records relative OGG paths, source hashes, caption text, and edit timestamps. Video-builder arguments supply the private staged source roots at run time; no licensed recordings or machine-specific paths are stored here.

The stage-one review is generated with `python -B render_stage1_review.py --menu-root <private-menu-project> --sci-fi-root <private-sci-fi-project> --horror-root <private-horror-project>`. It renders code-drawn native-size stills and the requested reduced-size readability views, verifies all mapped source hashes, and writes `stage1-review.json` with relative image paths, bounds, font measurements, and hashes. This checkpoint does not encode video or claim audio playback.

The intended opening is a standalone 2.5-second title card. The first sound and caption are both placed at 2.8 seconds. Endcards retain at least three seconds. The media builder estimates a four-times oversampled PCM true peak and applies one bounded gain per video before AAC encoding; final AAC measurements are recorded separately after encoding.