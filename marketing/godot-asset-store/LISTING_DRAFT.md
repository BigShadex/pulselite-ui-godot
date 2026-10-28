# PulseLite UI Sounds — Godot Asset Library listing draft

**Draft for v1.2.2 only. Not submitted.** The current public Godot Asset Store page still shows v1.2.1; see `SOURCE_RECONCILIATION.md` before using portal version fields.

## Existing listing title

PulseLite UI Sounds: Free Button & Menu SFX Autoload

## Short description

A free Godot add-on with a `PulseLiteUI` autoload, 20 UI sounds across 14 event names, and helper methods for wiring button hover, click, and toggle sounds.

## Description

PulseLite UI Sounds is a small Godot add-on for menu and interface audio. Enable the plugin to register the `PulseLiteUI` autoload, then connect buttons under a menu node with `PulseLiteUI.wire_buttons(self)`. Toggle-mode buttons use the matching `toggle_on` and `toggle_off` sounds. Call `PulseLiteUI.play("coin_pickup")` or another event name for one-off feedback.

The free add-on contains 20 WAV sounds across 14 event names, including click, hover, toggle, confirm, back, error, notification, panel open/close, transition, coin, reward, and level-up. The included demo scene shows the event buttons. The standard add-on has no external plugin dependency. Tested on Godot 4.7.2; GDScript only, no dependencies.

**This listing describes the free 20-sound add-on only.** Separately offered sound packs are separate products and are not included in this Asset Library add-on.

### Install

Install from the Godot Asset Library, then enable **PulseLite UI SFX (free sample)** under **Project > Project Settings > Plugins**. Enabling the plugin registers the `PulseLiteUI` autoload. For a manual install, copy `addons/pulselite_ui/` into your project's `addons/` folder, then enable the plugin. You can instead add `res://addons/pulselite_ui/PulseLiteUI.gd` as an autoload named `PulseLiteUI`.

### License

The scripts are MIT licensed. The 20 sounds are CC BY 4.0; attribution is required. Suggested credit:

> Sounds: PulseLite UI SFX by Bigshadex (CC BY 4.0) https://bigshadex.itch.io/pulselite-ui-sfx-free

### AI and audio disclosure (listing text)

The audio is synthesized with procedural DSP, not AI-generated. The GDScript and project documentation were written with AI assistance.

**Draft note for Russ/Grok Bot:** this listing copy was also AI-assisted and needs owner review before use.

## Existing-record fields to preserve or verify before entry

- **Version:** 1.2.2 (verified GitHub release/tag; not verified as uploaded to the Godot Asset Store).
- **Test evidence:** tested on Godot 4.7.2 in the v1.2.2 README.
- **Minimum Godot version for v1.2.2:** **UNVERIFIED**. The live Godot Asset Store page currently displays 4.7 for v1.2.1 only.
- **Price:** keep the free add-on entry distinct from separate paid packs; this draft introduces no price.
- **Stability field for v1.2.2:** **UNVERIFIED**. The live page currently marks its v1.2.1 version unstable; that does not establish the v1.2.2 field.
- **Tags/category:** the current page shows Addon and GDScript, UI, Menu, Audio, Sound Effects, Buttons. Preserve these only if the portal still offers them for v1.2.2.
