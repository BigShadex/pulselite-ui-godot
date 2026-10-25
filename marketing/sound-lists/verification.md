# Shipped-file verification and theme-swap qualification

COS-A028; checked 26 October 2026 (Australia/Adelaide). COS acting under owner delegation. These are product-copy checks, not a release, a new compatibility certification or a change to the live listings.

## Exact artifacts

The signed-in creator interface's **More > Download** backup action supplied each file exactly as uploaded. ZIP CRC checks passed. Paid ZIPs and raw paid audio remain private and are not part of this repository.

| Existing product | Uploaded ZIP | Bytes | SHA-256 |
|---|---|---:|---|
| [Sci-Fi](https://bigshadex.itch.io/pulselite-scifi-ui) | `PulseLite-SciFi-UI-with-extras.zip` | 3,837,179 | `e654163414cb8f795a0f518295530e7892679a3993b1aec352830a24c379dab3` |
| [Horror](https://bigshadex.itch.io/pulselite-horror-ui) | `PulseLite-Horror-UI-with-extras.zip` | 5,426,935 | `60be9dc5d9901b52c399027e34d61a96b0d5779cb3bc6d24b037adbdcc021b06` |
| [Menu Kit](https://bigshadex.itch.io/pulselite-ui-sfx) | `PulseLite-UI-SFX-Pack-with-extras.zip` | 7,593,842 | `4bb96826023999de8109df45ef222c10d990947ae2071c004fb3ab8e00445b73` |

Each archive has one pack-root `index.csv`, `ui_events.json` and `ui_events.csv`; the shipped Godot and Unity helpers are under `engine/`. The theme event-map version is 1.0; Menu Kit is 1.2.

Both themed ZIP inventories also confirm `QC_REPORT.md`, `PROVENANCE.md`, `LICENSE.txt`, `README.md`, `ucs-rename-map.csv`, plus `engine/godot/maaack/README.md`, `REFERENCES.json` and the theme-named `.tscn` scene. These checks establish that the extras exist; the Maaack integration was not executed for this task.

## Checks completed

- Each themed `index.csv` contains 104 unique WAV rows. Its file set exactly matches the 104 shipped `sounds/**/*.wav` members. Each of the 13 category folders has eight sounds.
- All listed per-file SHA-256 prefixes match the actual WAV bytes. Every themed WAV header reports 44,100 Hz, one channel, 16 bits.
- Each theme has 104 corresponding `ogg/**/*.ogg` paths with the same stems. These are alternate encodings of the same 104 sounds. OGG quality and audibility were not assessed by this inventory check.
- Both shipped helpers' 14 event lists exactly match `ui_events.json`, and every recommended/alternate reference resolves to a shipped WAV path. Toggle on uses four odd-numbered files; toggle off uses four even-numbered files. They share one eight-file category.
- Menu Kit independently matches 200 WAV rows and 200 OGG paths. All 20 public addon WAVs at [base commit d40df7f](https://github.com/BigShadex/pulselite-ui-godot/tree/d40df7f98000d70a8870eb43246817c7b2bfe517/addons/pulselite_ui/sounds) are byte-identical to their counterparts in this current paid Menu Kit ZIP.

The copy's sound descriptions are paraphrases of the shipped manifest descriptions and provenance, not a new listening review. Included technical reports are not independent proof of every acoustic claim.

## Does one-folder theme replacement work?

**Qualified yes for a stopped project using the same path and format; not a runtime hot-swap promise.** All three packs keep the 14 event names and `<category>/<file>` layout. The themed scripts have identical non-comment Godot code; Menu Kit's event lists include more variations and a few different preferred files.

The shipped Godot helper defaults to `res://audio/pulselite/` and `ogg`. Its `_files_for(event)` filters its event list through `ResourceLoader.exists()`, so absent higher-numbered Menu Kit variants can be skipped when using a smaller theme. `_available` then caches the resolved paths; `_cache` retains loaded audio streams. There is no public theme-change/cache-reset method. Replacing files or changing `base_path` during a running session does not guarantee the new theme will load.

Preserve the configured folder path and format, replace the complete category tree with the chosen theme while stopped, let Godot reimport, then restart. Game event calls such as `play("menu_confirm")` and `wire_buttons(self)` can stay as they are. Moving the audio requires the corresponding `base_path` setting before first playback; changing between WAV and OGG also requires the `extension` setting. The public free addon uses a different default location and WAV format, so do not blindly copy the paid helper's defaults into its installation instructions.

**Runtime evidence:** Godot `4.7.stable.official.5b4e0cb0f`, Ubuntu/WSL, headless. Six private fixtures used the unchanged shipped Menu Kit or Sci-Fi script against each of the three packs' OGG folders at the same `res://audio/pulselite/` path. In every fixture, all 14 calls returned a player with a loaded stream and emitted `played` with an existing pack path; the script bytes and post-import project settings stayed identical across each three-theme comparison. This demonstrates the path/event contract in these fixtures, not an actual game migration or audible playback.

**Test limitation:** every fixture exited with code 0 and the 14-event assertion passed, but Godot reported ObjectDB leak warnings and OGG resource-still-in-use errors at shutdown. An explicit fixture teardown retry retained those diagnostics. The complete fixture run is therefore not a clean QA PASS; the cause has not been isolated to engine, fixture or helper. Do not turn this narrow loading evidence into a claim of fully tested runtime switching, leak-free playback or Unity compatibility. No product code was changed to hide the errors.

**Unity scope:** source inspection confirms the same event names, matching files and `resourcesFolder = "PulseLite"`. Its loaded-clip cache also prevents an unqualified hot-swap promise. Unity editor import, execution and audible playback were not run for this task. Do not market the Godot fixture as Unity acceptance.

## Caption behavior for the companion visuals

`wire_buttons` gives ordinary buttons `button_click` on press and hover sounds on pointer/focus entry. Confirm and Back need the `pulselite_event` metadata on those ordinary buttons (or an explicit `play` call); labels alone do not select those events. Toggle buttons use `toggle_on` / `toggle_off` from `toggled`, rather than their press metadata. Use the real `played(event,path)` output for displayed captions.

No product files, event mappings, settings, licences or prices were changed. Documentation prepared with AI assistance.
