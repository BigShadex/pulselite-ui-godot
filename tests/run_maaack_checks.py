#!/usr/bin/env python3
"""Native, isolated Godot checks. No plugin or project settings are overwritten."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_SHA256 = "4c5322427bbc31bf3460e1c5027e32743938fbc1f53536c7e70cfccdff2ce616"
CONTROLLER_RELATIVE = Path("addons/maaacks_ui_sound_controller/base/scripts/ui_sound_controller.gd")
PROJECT = 'config_version=5\n[application]\nconfig/name="PulseLite integration QA"\nconfig/features=PackedStringArray("4.3")\n'


def run(godot, project, *arguments, marker=None):
    result = subprocess.run(
        [str(godot), "--headless", "--path", str(project), *arguments],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        env={**os.environ, "GODOT_SILENCE_ROOT_WARNING": "1"},
    )
    print(result.stdout, end="", flush=True)
    if result.returncode or "ERROR:" in result.stdout or "SCRIPT ERROR" in result.stdout:
        raise RuntimeError(f"Godot failed ({result.returncode}): {arguments}")
    if marker and marker not in result.stdout:
        raise RuntimeError(f"Godot never completed {marker}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", type=Path, required=True)
    parser.add_argument("--controller-source", type=Path, required=True,
                        help="Maaack's pinned ui_sound_controller.gd, fetched by fetch_maaack_qa.py")
    args = parser.parse_args()
    godot = args.godot.resolve(strict=True)
    source = args.controller_source.resolve(strict=True)
    licence = (source.parent / "LICENSE.txt").resolve(strict=True)
    if hashlib.sha256(source.read_bytes()).hexdigest() != CONTROLLER_SHA256:
        raise ValueError("Maaack controller differs from the reviewed pin; review before updating")

    with tempfile.TemporaryDirectory(prefix="pulselite-maaack-") as folder:
        project = Path(folder)
        shutil.copytree(ROOT / "addons/pulselite_ui", project / "addons/pulselite_ui")
        (project / "project.godot").write_text(PROJECT, encoding="utf-8")
        shutil.copy(ROOT / "tests/test_addon_standalone.gd", project)
        # The optional preset must not break users who never install Maaack.
        run(godot, project, "--editor", "--import")
        run(godot, project, "--script", "res://test_addon_standalone.gd", marker="PASS standalone")

        target = project / CONTROLLER_RELATIVE
        target.parent.mkdir(parents=True)
        shutil.copy(source, target)
        shutil.copy(licence, target.parent / "LICENSE.txt")
        shutil.copy(ROOT / "tests/test_maaack_preset.gd", project)
        run(godot, project, "--editor", "--import")
        run(godot, project, "--script", "res://test_maaack_preset.gd", marker="PASS Maaack integration")


if __name__ == "__main__":
    main()
