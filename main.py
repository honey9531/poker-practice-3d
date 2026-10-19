"""Hold'em Practice entry point.

Run with ``python main.py``. Virtual chips only; no real-money gambling.

Options:
    --self-test   verify resources and play a few automated hands, then exit
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        from services.logging_setup import configure_logging
        from services.self_test import run_self_test

        configure_logging()
        return run_self_test()

    from services.application import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
