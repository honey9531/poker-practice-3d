"""Generate the application icon in ``assets/icon``.

Usage:
    python tools/generate_icon.py [OUTPUT_DIR]

Writes ``app.svg`` (the source artwork), ``app.png`` (256 px, window icon) and
``app.ico`` (16-256 px, Windows executable icon). The ICO container stores PNG
images, which Windows Vista and later support. Rendering uses Qt's SVG renderer
offscreen; this is a build-time tool, not part of the UI.
"""

from __future__ import annotations

import io
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "icon"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

# A casino chip (deep green with cream inserts) carrying a gold spade.
SVG = """<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" viewBox="0 0 256 256">
<defs>
<radialGradient id="body" cx="0.42" cy="0.36" r="0.75">
<stop offset="0" stop-color="#1d7a4f"/><stop offset="1" stop-color="#0b3d26"/>
</radialGradient>
</defs>
<circle cx="128" cy="128" r="120" fill="url(#body)" stroke="#06261a" stroke-width="6"/>
{inserts}
<circle cx="128" cy="128" r="80" fill="none" stroke="#f1e7cf" stroke-width="5" stroke-dasharray="10 8"/>
<circle cx="128" cy="128" r="64" fill="#f6efdf" stroke="#c9a45a" stroke-width="5"/>
<path transform="translate(80 78) scale(0.96)"
 d="M50 0 C78 24 98 41 98 61 C98 76 87 85 74 85 C64 85 57 80 53 72 C54 85 59 94 68 100 L32 100
 C41 94 46 85 47 72 C43 80 36 85 26 85 C13 85 2 76 2 61 C2 41 22 24 50 0 Z" fill="#14130f"/>
</svg>
"""


def svg_text() -> str:
    import math

    inserts = []
    for i in range(8):
        angle = math.radians(i * 45)
        x = 128 + 104 * math.cos(angle)
        y = 128 + 104 * math.sin(angle)
        inserts.append(
            f'<rect x="{x - 11:.1f}" y="{y - 17:.1f}" width="22" height="34" rx="4" fill="#f1e7cf" '
            f'transform="rotate({i * 45 + 90} {x:.1f} {y:.1f})"/>'
        )
    return SVG.replace("{inserts}", "".join(inserts))


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def ico(images: dict[int, bytes]) -> bytes:
    """ICO container with embedded PNG images."""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = io.BytesIO()
    payload = io.BytesIO()
    offset = 6 + 16 * len(images)
    for size, png in sorted(images.items()):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO format
        entries.write(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + payload.tell()))
        payload.write(png)
    return header + entries.getvalue() + payload.getvalue()


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    text = svg_text()
    (output / "app.svg").write_text(text, encoding="utf-8")
    renderer = QSvgRenderer(QByteArray(text.encode()))
    if not renderer.isValid():
        print("Invalid icon SVG", file=sys.stderr)
        return 1
    pngs = {size: render_png(renderer, size) for size in ICO_SIZES}
    (output / "app.png").write_bytes(pngs[256])
    (output / "app.ico").write_bytes(ico(pngs))
    print(f"Wrote app.svg, app.png and app.ico to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
