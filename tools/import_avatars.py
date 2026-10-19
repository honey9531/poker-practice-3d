"""Import the opponents' 3D characters into ``assets/avatars``.

The characters come from the Microsoft Rocketbox Avatar Library (MIT licence,
https://github.com/microsoft/Microsoft-Rocketbox), downloaded from a pinned
commit. For each one this tool:

1. downloads the rigged FBX and its colour, normal and opacity textures;
2. converts the model with Qt's ``balsam`` into a QML component and a mesh;
3. shrinks the 2048 px textures (JPEG for colour and normals, PNG where alpha
   is needed) and rewrites the generated materials to use them;
4. adds property aliases for the bones the table animates (spine, neck,
   head, arms, legs, eyelids) so QML can pose the character.

The output is committed, like the card artwork, so the app needs no network
or conversion step. Run it again only to change the characters:

    python tools/import_avatars.py [OUTPUT_DIR]

Needs network access and ``pyside6-balsam`` (installed with PySide6).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "avatars"

REPO = "microsoft/Microsoft-Rocketbox"
COMMIT = "0943055db6ec570bcef9f2c8b41c9e5467c808f9"
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/Assets/Avatars/Adults"
API = f"https://api.github.com/repos/{REPO}/contents/Assets/Avatars/Adults"

# Opponent name -> Rocketbox avatar. Names match services.game_session.OPPONENT_NAMES.
AVATARS = {
    "Avery": "Female_Adult_04",
    "Blake": "Male_Adult_12",
    "Casey": "Female_Adult_03",
    "Drew": "Male_Adult_03",
    "Emery": "Male_Adult_10",
}

# Texture kind -> (pixel size, format). Faces get more detail than clothes.
TEXTURES = {
    "head_color": (1024, "jpg"),
    "body_color": (1024, "jpg"),
    "head_normal": (512, "jpg"),
    "body_normal": (512, "jpg"),
    "opacity_color": (512, "png"),  # hair and eyelashes need alpha
}

# QML property name -> Biped bone. Only bones present in a model get an alias.
BONES = {
    "pelvis": "Pelvis", "spine": "Spine", "spine1": "Spine1", "spine2": "Spine2",
    "neck": "Neck", "head": "Head",
    "leftClavicle": "L_Clavicle", "leftUpperArm": "L_UpperArm", "leftForearm": "L_Forearm",
    "leftHand": "L_Hand", "leftFinger": "L_Finger2",
    "rightClavicle": "R_Clavicle", "rightUpperArm": "R_UpperArm", "rightForearm": "R_Forearm",
    "rightHand": "R_Hand", "rightFinger": "R_Finger2",
    "leftThigh": "L_Thigh", "leftCalf": "L_Calf", "leftFoot": "L_Foot",
    "rightThigh": "R_Thigh", "rightCalf": "R_Calf", "rightFoot": "R_Foot",
    "leftEyelid": "LEyeBlinkTop", "rightEyelid": "REyeBlinkTop",
}

LICENSE_NOTE = """# 3D characters

The opponents' 3D characters are from the Microsoft Rocketbox Avatar Library,
https://github.com/microsoft/Microsoft-Rocketbox (commit {commit}),
converted for Qt Quick 3D by tools/import_avatars.py with smaller textures.

| Player | Rocketbox avatar |
| --- | --- |
{rows}

If you use them in research, the authors ask that you cite: Gonzalez-Franco et
al., "The Rocketbox library and the utility of freely available rigged avatars",
Frontiers in Virtual Reality (2020), doi:10.3389/frvir.2020.561558.

## Licence

MIT License

Copyright (c) 2020 Microsoft

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def fetch(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=180) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def list_textures(avatar: str) -> list[str]:
    with urllib.request.urlopen(f"{API}/{avatar}/Textures?ref={COMMIT}", timeout=60) as response:
        return [entry["name"] for entry in json.load(response)]


def balsam() -> str:
    tool = shutil.which("pyside6-balsam") or str(Path(sys.executable).parent / "pyside6-balsam")
    if not Path(tool).exists():
        raise SystemExit("pyside6-balsam not found (it is installed with PySide6)")
    return tool


def convert_texture(source: Path, dest: Path, size: int) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    image = QImage(str(source))
    if image.isNull():
        raise SystemExit(f"Cannot read {source}")
    scaled = image.scaled(size, size * image.height() // image.width(),
                          Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if dest.suffix == ".jpg":
        scaled = scaled.convertToFormat(QImage.Format.Format_RGB888)
        ok = scaled.save(str(dest), "JPG", 88)
    else:
        ok = scaled.save(str(dest), "PNG")
    if not ok:
        raise SystemExit(f"Cannot write {dest}")


def top_level_blocks(lines: list[str], keyword: str) -> list[tuple[int, int]]:
    """(start, end) line ranges of ``keyword {`` blocks directly inside the root Node."""
    ranges = []
    i = 0
    while i < len(lines):
        if lines[i].startswith(f"    {keyword} {{"):
            depth, j = 0, i
            while True:
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0:
                    break
                j += 1
            ranges.append((i, j))
            i = j
        i += 1
    return ranges


def material_block(material_id: str, kind: str, textures: dict[str, str]) -> list[str]:
    """Our material for one of the model's three surfaces (body, head, opacity)."""
    lines = [f"    PrincipledMaterial {{", f"        id: {material_id}", f'        objectName: "{kind}"']
    if kind == "opacity":
        lines += [
            f'        baseColorMap: Texture {{ source: "{textures["opacity_color"]}"; generateMipmaps: true; mipFilter: Texture.Linear }}',
            "        alphaMode: PrincipledMaterial.Mask",
            "        alphaCutoff: 0.4",
            "        cullMode: Material.NoCulling",
            "        roughness: 0.75",
        ]
    else:
        lines += [
            f'        baseColorMap: Texture {{ source: "{textures[f"{kind}_color"]}"; generateMipmaps: true; mipFilter: Texture.Linear }}',
            f'        normalMap: Texture {{ source: "{textures[f"{kind}_normal"]}"; generateMipmaps: true; mipFilter: Texture.Linear }}',
            "        normalStrength: 0.6",
            f"        roughness: {0.62 if kind == 'head' else 0.82}",
            f"        specularAmount: {0.35 if kind == 'head' else 0.2}",
        ]
    return lines + ["    }"]


def rewrite_qml(text: str, textures: dict[str, str]) -> str:
    """Replace balsam's textures and materials, and add bone aliases."""
    lines = text.splitlines()
    textures_blocks = top_level_blocks(lines, "Texture")
    material_blocks = top_level_blocks(lines, "PrincipledMaterial")
    replacements: dict[int, tuple[int, list[str]]] = {}
    for start, end in textures_blocks:
        replacements[start] = (end, [])
    for start, end in material_blocks:
        block = "\n".join(lines[start:end + 1])
        material_id = re.search(r"id: (\w+)", block).group(1)
        kind = next(k for k in ("body", "head", "opacity") if material_id.endswith(f"_{k}_material"))
        replacements[start] = (end, material_block(material_id, kind, textures))
    out: list[str] = []
    i = 0
    while i < len(lines):
        if i in replacements:
            end, new = replacements[i]
            out += new
            i = end + 1
            continue
        out.append(lines[i])
        i += 1
    result = "\n".join(out) + "\n"

    aliases = [
        f"    property alias {name}: bip01_{bone}"
        for name, bone in BONES.items()
        if re.search(rf"\bid: bip01_{bone}\b", result)
    ]
    header = "    // Bones the table poses and animates.\n" + "\n".join(aliases) + "\n"
    result = result.replace('    objectName: "Root"\n', '    objectName: "Root"\n\n' + header, 1)
    return (
        "// Generated by tools/import_avatars.py from the Microsoft Rocketbox Avatar Library (MIT).\n"
        "// Do not edit by hand.\n" + result
    )


def import_avatar(player: str, avatar: str, output: Path, work: Path) -> None:
    src = work / avatar
    (src / "Textures").mkdir(parents=True)
    fbx = src / f"{avatar}.fbx"
    print(f"{player}: {avatar}")
    fetch(f"{RAW}/{avatar}/Export/{avatar}.fbx", fbx)

    dest = output / player
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "maps").mkdir(parents=True)
    textures: dict[str, str] = {}
    for name in list_textures(avatar):
        kind = name.split("_", 1)[1].rsplit(".", 1)[0]  # f004_body_color.tga -> body_color
        if kind not in TEXTURES:
            continue
        size, fmt = TEXTURES[kind]
        tga = src / "Textures" / name
        fetch(f"{RAW}/{avatar}/Textures/{name}", tga)
        file_name = f"{kind}.{fmt}"
        convert_texture(tga, dest / "maps" / file_name, size)
        textures[kind] = f"maps/{file_name}"

    generated = work / f"{avatar}_qml"
    subprocess.run([balsam(), "--outputPath", str(generated), str(fbx)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    qml = next(generated.glob("*.qml"))
    (dest / "meshes").mkdir()
    for mesh in (generated / "meshes").glob("*.mesh"):
        shutil.copy(mesh, dest / "meshes" / mesh.name)
    component = f"Avatar{player}.qml"
    (dest / component).write_text(rewrite_qml(qml.read_text(encoding="utf-8"), textures), encoding="utf-8")


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])  # QImage plugins (TGA)
    with tempfile.TemporaryDirectory() as tmp:
        for player, avatar in AVATARS.items():
            import_avatar(player, avatar, output, Path(tmp))
    rows = "\n".join(f"| {player} | {avatar} |" for player, avatar in AVATARS.items())
    (output / "LICENSE.md").write_text(LICENSE_NOTE.format(commit=COMMIT, rows=rows), encoding="utf-8")
    del app
    print(f"Wrote {len(AVATARS)} characters to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
