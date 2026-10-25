# PulseLite listing copy from shipped files

Prepared for the existing product pages on 26 October 2026 (Australia/Adelaide), in response to COS-A028. These are drafts for GrokBot to review and publish.

- [Sci-Fi: What's in the box](scifi-whats-in-the-box.md)
- [Horror: What's in the box](horror-whats-in-the-box.md)
- [Verification, source ZIP identities and theme-swap limits](verification.md)

The tables count **104 distinct sounds per theme**. Each sound has a WAV master and an OGG copy: 208 audio files, not 208 different sounds. The single toggle category contains four on/off pairs and supplies two UI events, so there are 13 categories and 14 events.

## Recommended theme-swap wording

> In Godot, keep your existing PulseLite event calls. With the game stopped, replace the audio folder at the same path, using the same audio format, then reimport and restart. The shipped scripts retain the same 14 event names. Each theme supplies eight sounds per category; it does not add the Menu Kit's larger variation set. Moving the folder or changing WAV/OGG requires the matching path/format setting before first playback.

Avoid an unqualified promise of live theme switching: the scripts cache paths and loaded audio. See the verification notes for the exact runtime checks and Unity limitation. This change supplies listing copy and evidence; it does not change the addon, any product download, price or licence.

Audio descriptions follow the shipped manifests. This documentation was prepared with AI assistance; no audio was generated or changed for this task.
