"""Generate table textures in ``assets/table``.

Usage:
    python tools/generate_textures.py [OUTPUT_DIR]

``felt_noise.png`` is a seamless tile of soft light/dark speckles encoded in
the alpha channel, laid over the felt colour to give it a woven texture.
Generation is deterministic (fixed seed) and needs only the standard library.
"""

from __future__ import annotations

import random
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "table"
SIZE = 256


def _blur(values: list[float], size: int, radius: int) -> list[float]:
    """Separable box blur with wrap-around, so the tile stays seamless."""
    def blur_rows(src: list[float]) -> list[float]:
        out = [0.0] * len(src)
        span = 2 * radius + 1
        for y in range(size):
            row = src[y * size:(y + 1) * size]
            for x in range(size):
                out[y * size + x] = sum(row[(x + d) % size] for d in range(-radius, radius + 1)) / span
        return out

    def transpose(src: list[float]) -> list[float]:
        return [src[x * size + y] for y in range(size) for x in range(size)]

    return transpose(blur_rows(transpose(blur_rows(values))))


def felt_noise(size: int = SIZE, seed: int = 1931) -> bytes:
    rng = random.Random(seed)
    fine = [rng.gauss(0, 1) for _ in range(size * size)]
    coarse = _blur([rng.gauss(0, 1) for _ in range(size * size)], size, 3)
    soft = _blur(fine, size, 1)
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)  # PNG filter type: none
        for x in range(size):
            i = y * size + x
            n = 0.75 * soft[i] + 2.2 * coarse[i]
            alpha = min(255, int(abs(n) * 70))
            shade = 255 if n > 0 else 0
            pixels += bytes((shade, shade, shade, alpha))
    return _png(size, size, bytes(pixels))


def _png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def all_textures() -> dict[str, bytes]:
    return {"felt_noise.png": felt_noise()}


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    for name, data in all_textures().items():
        (output / name).write_bytes(data)
    print(f"Wrote {len(all_textures())} files to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
