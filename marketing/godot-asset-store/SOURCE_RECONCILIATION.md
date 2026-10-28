# v1.2.2 listing source reconciliation

**Checked:** 2026-10-29. This note separates the existing GitHub release from the current Godot Asset Store record. The listing and changelog in this folder are drafts only.

## Release and tag evidence

- GitHub's public releases page lists **PulseLite UI Sounds 1.2.2**, with tag **v1.2.2**, at commit **b6e42b8**. It reports the release at 17 Oct 00:29. The release notes say the 20 free CC BY 4.0 WAVs were unchanged, scripts are MIT, and the audio is procedural DSP rather than AI-generated; they also disclose AI assistance in scripts.
- The assigned local worktree contains commit `b6e42b86c41bbfa20ae85ba6345128d50fd4e854`; the commit metadata date is `2026-10-17T10:59:18+10:30`. `git show b6e42b8` shows five changed paths: `CREDITS.txt`, `README.md`, `addons/pulselite_ui/CREDITS.txt`, `addons/pulselite_ui/plugin.cfg`, and `addons/pulselite_ui/plugin.gd`.
- The local clone's `git tag --list` is empty, but the remote tag lookup verifies `refs/tags/v1.2.1` at `9a5095d7a3b438d53e98a18bf90af63350aeeef1` and `refs/tags/v1.2.2` at `b6e42b86c41bbfa20ae85ba6345128d50fd4e854`. GitHub's public release page independently shows `v1.2.2` at `b6e42b8`.
- The current local branch head is later than v1.2.2 (`5335169`, 2026-10-28). Later trailer/gallery/media commits are not treated as part of the v1.2.2 release. The v1.2.2 GitHub release and commit diff are the source for its changelog.

## Godot version and install evidence

- `README.md` at commit `b6e42b8` states **Tested on Godot 4.7.2** and **GDScript only, no dependencies**. The draft uses only the exact tested version and makes no broader compatibility promise.
- That same release README gives the install wording reproduced in `LISTING_DRAFT.md`: install from the Godot Asset Store, enable the plugin under Project > Project Settings > Plugins, or copy `addons/pulselite_ui/` manually; alternatively add the script as an autoload.
- **Minimum version for v1.2.2 remains UNVERIFIED.** The current public Godot Asset Store page shows minimum Godot version 4.7 for its listed v1.2.1 record; it is not evidence of the v1.2.2 field.

## License and product boundary

- At the v1.2.2 commit, `README.md`, `LICENSE`, `LICENSE-SOUNDS`, and both `CREDITS.txt` files establish MIT for scripts and CC BY 4.0 for the 20 sounds, with attribution required. `CREDITS.txt` supplies the suggested line reproduced in the draft.
- The free Godot add-on includes 20 sounds. The separately offered paid packs are not included in this Asset Library listing; no paid price is stated.
- v1.2.2 release text says the audio is procedural DSP, not AI-generated, and scripts were written with AI assistance. The v1.2.2 README also says the documentation was written with AI assistance. The current Asset Store disclosure additionally says its listing description was AI-assisted. The new listing draft explicitly identifies itself as AI-assisted and pending owner review.

## Current Asset Store record (not the v1.2.2 release)

The [public Godot Asset Store page](https://store.godotengine.org/asset/bigshadex/pulselite-ui-sounds-free-button-menu-sfx-autoload/) currently shows:

- Existing title: “PulseLite UI Sounds: Free Button & Menu SFX Autoload”.
- Version/changelog section: version 1.2.1, with no changelog provided; last updated 13 October 2026.
- Minimum Godot version: 4.7; tested version: 4.7.2.
- License: MIT (scripts) + CC BY 4.0 (sounds).
- Stability label: unstable.
- AI disclosure: procedural DSP audio (not AI-generated); GDScript, docs and description AI-assisted, then tested and reviewed.

For v1.2.2, the portal's minimum-version field, stability label, and any live version upload state are **UNVERIFIED**. The v1.2.2 release is verified on GitHub but was not found as the current version on the Godot Asset Store page.

## Commands and sources checked

Local source inspection:

```text
git log -1 --format=%H
  -> 53351691f8b7f037662ccfbd98fdb0086576df6e
git show --stat b6e42b8
git show b6e42b8:README.md
git show b6e42b8:addons/pulselite_ui/plugin.cfg
git show b6e42b8 --
git diff --name-only 9a5095d b6e42b8
git tag --list
git ls-remote --tags origin
  -> refs/tags/v1.2.1 9a5095d7a3b438d53e98a18bf90af63350aeeef1
     refs/tags/v1.2.2 b6e42b86c41bbfa20ae85ba6345128d50fd4e854
```

External source pages:

- [GitHub releases](https://github.com/BigShadex/pulselite-ui-godot/releases)
- [GitHub v1.2.2 tag/release](https://github.com/BigShadex/pulselite-ui-godot/releases/tag/v1.2.2)
- [Current Godot Asset Store record](https://store.godotengine.org/asset/bigshadex/pulselite-ui-sounds-free-button-menu-sfx-autoload/)

The `gh` command-line client was not installed, so the release/tag was verified from the public GitHub page and the matching local commit. Task tracking: Automated Income Collab issue #15, comment IDs `6476056193` and `6475863064`.
