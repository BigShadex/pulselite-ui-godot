#!/usr/bin/env python3
"""Fetch pinned native QA dependencies outside the product tree (standard library only)."""

import argparse
import hashlib
from pathlib import Path
import shutil
import urllib.request
import zipfile

MAAACK_COMMIT = "4ae5fd97b363b8236abfe616179226aa03ded0cd"
MAAACK_PATH = "addons/maaacks_ui_sound_controller"
PINNED_FILES = {
    "base/scripts/ui_sound_controller.gd": "4c5322427bbc31bf3460e1c5027e32743938fbc1f53536c7e70cfccdff2ce616",
    "LICENSE.txt": "43209eee620ea92309fce4eba7025d01963708238a8b848a323b15a8c67f3b5d",
}
# Official godot-builds release SHA512-SUMS.txt, verified 2026-10-20.
GODOT_SHA512 = {
    "4.3": "fd52bb4ba8acc30ca5accd1c566d470ad7282f891ccc0995dfafabcf92bcf76280ce182bf9d80ebd885f3ed2165d01e1fc3f2928436b15498dfbd98656c2a45a",
    "4.7": "b639ca9c1ddea39bb3df89bd5283a51ca6047467abe6b25e9436566f2b2082ede633025073989ecf39c7d5d3c2493d80ea13e3af6dd5e261bbf89e462d6d2214",
}


def download(url, target, digest, algorithm):
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, part.open("wb") as output:
            shutil.copyfileobj(response, output)
        with part.open("rb") as data:
            actual = hashlib.file_digest(data, algorithm).hexdigest()
        if actual != digest:
            raise ValueError(f"Checksum mismatch for {target.name}")
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)
    print(f"Verified {algorithm}: {target.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot-version", choices=GODOT_SHA512, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == Path(__file__).resolve().parents[1] or Path(__file__).resolve().parents[1] in output.parents:
        raise ValueError("QA dependencies must be outside the product repository")
    asset = f"Godot_v{args.godot_version}-stable_linux.x86_64"
    archive = output / (asset + ".zip")
    download(
        f"https://github.com/godotengine/godot-builds/releases/download/{args.godot_version}-stable/{asset}.zip",
        archive, GODOT_SHA512[args.godot_version], "sha512",
    )
    with zipfile.ZipFile(archive) as contents:
        executable = output / asset
        executable.write_bytes(contents.read(asset))
        executable.chmod(0o755)
    for relative, expected in PINNED_FILES.items():
        download(
            f"https://raw.githubusercontent.com/Maaack/Godot-UI-Sound-Controller/{MAAACK_COMMIT}/{MAAACK_PATH}/{relative}",
            output / "maaack" / Path(relative).name, expected, "sha256",
        )


if __name__ == "__main__":
    main()
