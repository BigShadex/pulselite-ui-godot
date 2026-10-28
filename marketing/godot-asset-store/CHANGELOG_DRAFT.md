# PulseLite UI Sounds 1.2.2 — changelog draft

**Draft based on the existing v1.2.2 GitHub release/tag, published 2026-10-17. Not submitted as a new release or portal change.**

## Changelog text

- Added `CREDITS.txt` at the repository root and in the add-on folder, with a ready-to-copy attribution line for the 20 CC BY 4.0 sounds.
- When enabled, the plugin prints one line in the editor Output panel with a link to the full kit. The notice is editor-only and does not run in an exported game; it adds no dock or popup.
- Added the browser previewer link to the README.
- Set the plugin metadata version to 1.2.2.
- The 20 free sound files did not change in this release.

## Change-to-source map

| v1.2.2 source | Change |
|---|---|
| Commit [`b6e42b8`](https://github.com/BigShadex/pulselite-ui-godot/commit/b6e42b8), `CREDITS.txt` and `addons/pulselite_ui/CREDITS.txt` | Adds the same ready-to-copy CC BY 4.0 sound credit in the repository and packaged add-on. |
| `b6e42b8`, `addons/pulselite_ui/plugin.gd` | Prints the promotional notice through the editor plugin enable hook; the source comment says it is editor-only and never runs in an exported game. |
| `b6e42b8`, `addons/pulselite_ui/plugin.cfg` | Changes plugin metadata from version `1.2` to `1.2.2`. |
| `b6e42b8`, `README.md` | Adds the browser previewer link and describes its mock menu. |
| `git diff 9a5095d b6e42b8` | Lists only the five files above; no sound files changed between the v1.2.1 baseline and v1.2.2. |

## Release source

- [Existing GitHub release: PulseLite UI Sounds 1.2.2](https://github.com/BigShadex/pulselite-ui-godot/releases/tag/v1.2.2)
- [Release commit b6e42b8](https://github.com/BigShadex/pulselite-ui-godot/commit/b6e42b8)
