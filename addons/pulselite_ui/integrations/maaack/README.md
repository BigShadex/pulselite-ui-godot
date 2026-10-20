# PulseLite Free preset for Maaack's UI Sound Controller

`PulseLiteFree.tscn` assigns five of this addon's 20 CC BY 4.0 WAVs to
Maaack's button, tab, slider, text-entry, item-list and tree events. The remaining
sounds are still available through the normal PulseLite API. Original names and
audio are unchanged. No upstream controller code is bundled or modified.

## Install

1. Install [Maaack's UI Sound Controller](https://github.com/Maaack/Godot-UI-Sound-Controller)
   (also included in Maaack's Game Template). Keep its normal folder name:
   `addons/maaacks_ui_sound_controller/`.
2. Copy the whole `addons/pulselite_ui/` folder into the project.
3. For project-wide sounds, change the existing `ProjectUISoundController`
   autoload's path in Project Settings > Globals > Autoload to
   `res://addons/pulselite_ui/integrations/maaack/PulseLiteFree.tscn`.
   Keep that autoload name. Re-enabling Maaack's plugin may restore its original
   autoload path, so recheck it after doing that.
   Alternatively, remove/disable that autoload and instance this preset as a child
   of a UI scene's root. It scans its parent and, by default, connects newly added
   controls throughout the tree (`persistent = true`, Maaack's normal behaviour).
   Set `persistent` off for a fixed scene-only scan.
4. Use one UI wiring controller. Do not also call `PulseLiteUI.wire_buttons()` or
   `enable_auto_wire()` on those controls; that would play two sounds. Ordinary
   `PulseLiteUI.play()` calls for gameplay events can still be used.

The preset uses the always-available `Master` bus and processes while paused.
Select its root node to change `audio_bus` to your own `SFX` or `UI` bus.
Change stream assignments in the Inspector as usual. It is an optional scene;
the original addon and demo still work without Maaack installed.

| UI events | Free WAV |
| --- | --- |
| Hover and focus (button, tab, slider, text field) | `hover/hover_01.wav` |
| Press/select, tab change, slider drag start | `click/click_03.wav` |
| Text changed | `click/click_09.wav` |
| Text submitted, slider drag end, item/tree activated | `confirm/confirm_05.wav` |
| Text change rejected | `error/error_01.wav` |

`tab_selected` is left empty: Godot can also emit `tab_changed` for a new tab,
so assigning both would double the feedback. Only signals supported by Maaack's
controller are wired; for example, its button branch covers `Button` subclasses,
not every `BaseButton`. Text changes play a click per change; clear that stream
if your interface should stay quiet while typing.

## Compatibility and reproducible QA

This integration targets the standalone UI Sound Controller at
[`4ae5fd97b363b8236abfe616179226aa03ded0cd`](https://github.com/Maaack/Godot-UI-Sound-Controller/tree/4ae5fd97b363b8236abfe616179226aa03ded0cd).
The current full Game Template advertises Godot 4.4+, whereas the standalone
controller advertises 4.3+. Testing this preset on 4.3 does not certify the entire
template on 4.3.

From the repo root, with Python 3.11+ and Linux x86-64:

```sh
python tests/fetch_maaack_qa.py --godot-version 4.3 --output /tmp/pulselite-qa-4.3
python tests/run_maaack_checks.py \
  --godot /tmp/pulselite-qa-4.3/Godot_v4.3-stable_linux.x86_64 \
  --controller-source /tmp/pulselite-qa-4.3/maaack/ui_sound_controller.gd
```

Repeat with `4.7` in place of `4.3`. Dependencies are pinned by commit/checksum,
including the official Godot release SHA-512; nothing is installed into your
project or global autoload settings. The tests import all 20 real free WAVs, load
the preset with Maaack's real script, check stream assignments and signal-driven
playback, late controls, repeat scanning, pause and cleanup. They also run the
standalone addon without Maaack. Runs are headless with dummy audio: audible
quality, mouse/keyboard interaction, exports and the full template's other systems
need separate checks. Paid presets require the actual pack manifests; they are
not included in this free addon.

## Attribution

Code/preset: MIT (the addon's `LICENSE_SCRIPTS.txt`). The five referenced sounds
retain the addon's CC BY 4.0 licence (`LICENSE_SOUNDS.txt`); give the normal credit:

> PulseLite UI SFX by Bigshadex (https://bigshadex.itch.io/pulselite-ui-sfx-free), CC BY 4.0

Maaack's controller is a separate MIT dependency; keep its licence when copying
it. This is an independent integration, with no endorsement or outreach implied.
Sounds are procedural DSP; scripts and documentation were AI-assisted.
