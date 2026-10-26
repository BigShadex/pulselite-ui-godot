# PulseLite UI SFX for Defold (draft)

A small Lua module that maps 14 UI events (click, hover, toggle on/off, confirm, back, error, notification, panel open/close, transition, coin, reward, level up) to the PulseLite free-sample sounds, with optional random alternates and light pitch variation.

Status: first draft, AI-assisted, **not yet tested inside Defold**. Issues and PRs welcome.

```lua
local sfx = require "pulselite_ui"

function init(self)
    sfx.init("/ui_sfx")   -- game object with one Sound component per file, named like "click_03"
end

-- later
sfx.play("button_click")
sfx.toggle(true)
sfx.play("reward", { gain = 0.8 })
```

Sounds: [free 20-sound sample](https://bigshadex.itch.io/pulselite-ui-sfx-free) (CC BY 4.0). Full 200-sound kit: [PulseLite Menu Kit](https://bigshadex.itch.io/pulselite-ui-sfx). Sounds are procedural DSP synthesis, not generative-AI audio. Script licence: MIT.
