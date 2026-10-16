# PulseLite UI Sounds for Godot 4

A small Godot 4 addon that gives your menus consistent interface sounds in one line of code.
It ships an autoload (`PulseLiteUI`) and 20 matching UI sounds: click, hover, toggle,
confirm, back, error, notification, panel open/close, transition, coin, reward and level up.

![Demo scene: buttons for every PulseLite UI event](docs/screenshot.png)

Tested on Godot 4.7.2. GDScript only, no dependencies.

## Install

**From the Godot Asset Store:** search for "PulseLite UI Sounds" and install it into your project.

**Manually:** copy the `addons/pulselite_ui/` folder from this repository into your project's
`addons/` folder.

Then enable the plugin in *Project > Project Settings > Plugins*. Enabling it registers the
`PulseLiteUI` autoload. (You can also add `res://addons/pulselite_ui/PulseLiteUI.gd` as an
autoload named `PulseLiteUI` yourself.)

## Usage

```gdscript
func _ready() -> void:
	# Hover + click sounds for every Button under this node,
	# on/off sounds for CheckBox, CheckButton and toggle-mode buttons.
	PulseLiteUI.wire_buttons(self)

func _on_coin_collected() -> void:
	PulseLiteUI.play("coin_pickup")
```

- Per-button overrides with node metadata: `pulselite_event` (e.g. `"menu_back"`) replaces the
  click sound, `pulselite_ignore = true` skips the button.
- `PulseLiteUI.enable_auto_wire()` also wires buttons created later.
- Random variation without immediate repeats, gentle pitch jitter (melodic sounds are never
  pitch-shifted), 8 overlapping voices, hover cooldown, keeps working while the game is paused.
- Settings: `bus` (defaults to `UI`, falls back to `Master`), `volume_db`, `pitch_jitter`,
  `random_variation`, `no_repeat`, `hover_cooldown_ms`. Signal `played(event, path)`.

## Events

| Event | Sound category |
|---|---|
| `button_click` | click |
| `button_hover` | hover |
| `toggle_on` | toggle |
| `toggle_off` | toggle |
| `menu_confirm` | confirm |
| `menu_back` | back/cancel |
| `error` | error |
| `notification` | notify |
| `panel_open` | panel open |
| `panel_close` | panel close |
| `transition` | whoosh |
| `coin_pickup` | coin |
| `reward` | reward |
| `level_up` | level up |

`addons/pulselite_ui/ui_events.json` has the same map for use outside the autoload.
Sounds: 44.1 kHz, 16-bit, mono WAV, loudness-matched, peaks at or below -1 dBFS.

## Demo

Open this repository as a Godot project and run it. `demo/demo.tscn` shows one button per
event, wired with a single `PulseLiteUI.wire_buttons(self)` call. Only `addons/pulselite_ui/`
is needed in your own project.

## Licenses

- **Code** (`plugin.gd`, `PulseLiteUI.gd`, `ui_events.json`, the demo): MIT, see [LICENSE](LICENSE).
- **Sounds** (`addons/pulselite_ui/sounds/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  see [LICENSE-SOUNDS](LICENSE-SOUNDS). Attribution is required, for example in your credits:

  > PulseLite UI SFX by Bigshadex (https://bigshadex.itch.io/pulselite-ui-sfx-free), CC BY 4.0

Copies of both licenses are also inside `addons/pulselite_ui/` so they travel with the addon.

## How it was made

The audio is synthesized from code (procedural DSP: oscillators, FM, filtered noise,
envelopes). No recorded samples, sample libraries or AI-generated audio. The GDScript and the
documentation were written with AI assistance, then tested and reviewed.

## Links

- Free sample with a playable browser demo: https://bigshadex.itch.io/pulselite-ui-sfx-free
- Need more variations? The paid 200-sound PulseLite kit (15-16 variations per event, OGG copies,
  Unity script) uses the same file names and API: https://bigshadex.itch.io/pulselite-ui-sfx
  (40% off until 30 Oct 2026)
- Themed packs with the same 14 event names, so this autoload works unchanged:
  [Sci-Fi UI](https://bigshadex.itch.io/pulselite-scifi-ui) (104 holographic sounds) and
  [Horror UI](https://bigshadex.itch.io/pulselite-horror-ui) (104 eerie sounds), or all three in
  [PulseLite Complete](https://bigshadex.itch.io/pulselite-complete)
