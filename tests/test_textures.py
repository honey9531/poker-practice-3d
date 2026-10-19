import sys

from PySide6.QtGui import QImage

from services.paths import assets_dir

sys.path.insert(0, str(assets_dir().parent / "tools"))
import generate_textures  # noqa: E402


def test_committed_textures_match_generator():
    for name, data in generate_textures.all_textures().items():
        assert (assets_dir() / "table" / name).read_bytes() == data, f"Run tools/generate_textures.py ({name})"


def test_felt_noise_is_a_translucent_tile(qapp):
    image = QImage(str(assets_dir() / "table" / "felt_noise.png"))
    assert not image.isNull()
    assert (image.width(), image.height()) == (generate_textures.SIZE, generate_textures.SIZE)
    assert image.hasAlphaChannel()
