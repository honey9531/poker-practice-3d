# Poker For Practice

**Hold'em Practice** is a Texas Hold'em practice application for Windows, built with Python,
PySide6 and Qt Quick/QML. Play no-limit hold'em against one to five computer opponents, then
review your hands, statistics and replays.

**Virtual chips only.** There is no real-money gambling, deposits, withdrawals or wagering.

## Features

- **Complete no-limit Texas Hold'em engine** (pure Python):
  - blinds (including short and all-in blinds), heads-up rules and a moving dealer button
  - minimum-raise rules, including incomplete all-in raises that don't reopen betting
  - side pots, split pots with odd-chip handling, uncalled bets, and all-in run-outs with hands shown
- **3D table:** a lit 3D scene seen from your seat — padded rail, felt, cards that are dealt,
  flip and lean up to be read, stacks of chips and dealer/blind pucks — with names, amounts and
  messages drawn crisply on top. The classic flat table is one click away in Settings, and is
  used automatically where 3D graphics are unavailable.
- **Original vector artwork:** an antique-style deck — parchment faces, gold-rimmed pips, ornate
  aces and court cards robed in their suit's colours — with four card backs to choose from, plus
  casino chips, stacks and a padded table with textured felt.
- **Animations:** dealing, card flips and chip movement.
- **Computer opponents:** conservative, balanced and aggressive styles at easy, normal and hard
  difficulty, with an optional post-hand analysis of their reasoning.
- **Betting controls:** fold, check/call, bet/raise and all-in, with a slider, an exact amount,
  pot-based presets and keyboard shortcuts.
- **Persistent data:** hand history with the chronological action log, read-only hand replay,
  statistics (VPIP, PFR, showdown frequency and win rate, net chips…) and settings, all stored
  in SQLite.

## Requirements

- Windows 10/11 (target platform); also runs on Linux and macOS from source
- Python 3.12+
- PySide6 6.12 (installed from `requirements.txt`)
- For the 3D table: a graphics driver with Direct3D 11/12, Vulkan, Metal or OpenGL 3.3. Without a
  GPU (virtual machines, remote desktops) the 3D table still runs with shadows and smoothing turned
  off; otherwise choose the classic table in Settings.

## Setup

```bash
python -m venv .venv            # Python 3.12+
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install -r requirements-dev.txt
```

If the system Python is older than 3.12, [uv](https://docs.astral.sh/uv/) can provide one:

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
```

## Running

```bash
python main.py                 # start the application
python main.py --self-test     # verify resources and play automated hands, then exit
```

### Playing

1. **Play** → choose opponents, stack, blinds, opponent style and difficulty → **Start Session**.
   *Blinds increase* makes the blinds rise every 5, 10 or 20 hands, as in a tournament
   (for example 10/20 → 20/40 → 30/60 → 50/100 → 100/200 …). The table's top bar shows the level and
   how many hands remain until the next increase. The default, *Never*, keeps the blinds fixed all
   session, as in a cash game.
2. Act with the buttons, or with keyboard shortcuts:
   - **F** fold
   - **C** check/call
   - **R** bet/raise the amount shown
   - **A** all-in

   Set the bet size with the presets, the slider or the amount field. Folding when you could
   check needs a second click.
3. When a hand is over, **click the table** (or press Space/Enter) to deal the next hand. You can
   also turn on *Deal next hand automatically* in Settings.
4. **Statistics** and **Hand History** (with **Replay**) are on the main menu.
5. **Settings** controls animations, auto-deal, hand analysis, the table (3D or classic 2D), the
   card back and chip colours, and lets you delete your history.

### Where data is stored

The SQLite database (hand history, statistics, settings) and the logs live outside the
installation folder:

| Platform | Location |
| --- | --- |
| Windows | `%APPDATA%\PokerPractice` |
| Linux | `$XDG_DATA_HOME/PokerPractice` (default `~/.local/share/PokerPractice`) |
| macOS | `~/Library/Application Support/PokerPractice` |

Set `POKER_PRACTICE_DATA_DIR` to use another directory. The tests and QA tools do this so they
never touch your real data.

## Testing

```bash
python -m pytest
```

The suite runs headless (`QT_QPA_PLATFORM=offscreen` is set in `tests/conftest.py`). It covers:

- **Engine:** hand rankings and kickers, betting rules, side pots, randomised
  chip-conservation sessions.
- **Opponents:** legality and style differences.
- **Interface:** QML components and screens.
- **Data and packaging:** persistence and restarts, replay, the bundle filter, and the
  self-test.
- **3D table:** the table meshes, the camera and projection, and the table style setting.

Headless runs use Qt Quick's software renderer, which cannot draw 3D, so the table screen tests
cover the 2D table and the tests of the live 3D scene in `tests/test_table_3d.py` are skipped.
Run them on a display, or under Xvfb:

```bash
xvfb-run -a env QT_QPA_PLATFORM=xcb python -m pytest tests/test_table_3d.py
```

### QA tools

```bash
python tools/screenshot.py out --sizes 1024x640,1920x1080 --screens menu,table --preview hand
python tools/walkthrough.py out --hands 8     # plays through the real UI, then history and replay
```

Both render offscreen, so they show the 2D table. For the 3D table, run them on a display or
under Xvfb (`xvfb-run -a env QT_QPA_PLATFORM=xcb python tools/screenshot.py … --wait 5000`; the
longer wait lets software-rendered 3D finish its animations).

- **`screenshot.py`** renders screens offscreen at the given window sizes.
- **`walkthrough.py`** clicks the same buttons a player would, saves screenshots, and fails on
  QML warnings, chip inconsistencies or unrecorded hands.
- **Gallery:** press **Ctrl+Shift+G** in the app to see every card, card state, chip
  denomination, stack and pile.

### Generated assets

The card artwork, the felt texture and the icon are generated, and the generated files are
committed. The tests fail if they are stale.

```bash
python tools/generate_cards.py      # assets/cards/*.svg (52 faces, 4 backs)
python tools/generate_textures.py   # assets/table/felt_noise.png
python tools/generate_icon.py       # assets/icon/app.svg, app.png, app.ico
```

## Packaging for Windows

PyInstaller builds a one-folder application: `dist\PokerPractice\PokerPractice.exe` plus its
`_internal` folder. It is configured in `packaging/PokerPractice.spec`.

On a Windows machine with Python 3.12 installed:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

The script:
1. creates `.venv-win` and installs the dependencies
2. runs the test suite
3. builds the executable
4. runs the packaged executable's `--self-test` twice against a temporary data directory,
   confirming that history persists between runs

To distribute the app, zip the whole `dist\PokerPractice` folder. Users unzip it anywhere and
run `PokerPractice.exe`; no Python installation or source code is needed.

`.github/workflows/windows-build.yml` runs the same script on a Windows runner and uploads the
built folder as an artifact.

On Linux, `packaging/build_linux.sh` builds and verifies `dist/PokerPractice/PokerPractice`.

### What has been verified

- **Linux:** the PyInstaller build was built and tested. Its self-test passed:
  - when copied away from the source tree
  - offscreen (2D table) and on an X11 display with the 3D table (software-rendered OpenGL)
  - twice in a row, with history persisting between runs
- **Windows:** the Windows executable has **not** been built or run yet, because development so
  far used a Linux machine without Windows. The spec, the build script and the CI workflow are
  ready, and the CI workflow (or the build script on Windows) is the next verification step.
- **Size:** the bundle is about 217 MB on Linux after removing unused Qt modules (see
  `packaging/bundle_filter.py`); the Qt Quick 3D runtime accounts for about 13 MB of it. Windows
  builds are usually smaller because system libraries are not bundled.
- **3D on a GPU:** the 3D table has only been run with software rendering (Mesa llvmpipe) so far;
  its full-detail mode (shadows, ambient occlusion, multisampling) still needs a look on real
  graphics hardware.

## Project layout

```
main.py              entry point (--self-test for build verification)
src/poker/           rules engine: cards, deck, evaluator, betting, pots, hand, table (no Qt)
src/ai/              computer opponents: hand strength, heuristic strategies
src/services/        bootstrap, session/controller, presenter, persistence, statistics, settings,
                     3D table meshes
src/bridge/          QObjects and models exposed to QML (import PokerPractice.Bridge)
qml/Main.qml         application window and navigation
qml/components/      theme, cards, chips, table (2D and 3D), seats, controls, dialogs
qml/screens/         menu, setup, table/replay, statistics, history, settings, gallery
assets/              generated card SVGs, felt texture, icon
packaging/           PyInstaller spec, bundle filter, build scripts
tests/               pytest suite
tools/               asset generators and QA tools
docs/                architecture notes
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions, the exact rules
implemented, and the definitions of each statistic.

## Troubleshooting

- **Blank window or startup failure:** check `<data dir>\logs\poker_practice.log`. QML errors
  are written there too.
- **"Something went wrong" dialog:** an unexpected error was logged in full in the log file
  named in the dialog. Include that file when reporting a problem.
- **"The history database was damaged and has been reset":** the old file was kept as
  `poker_practice.corrupt-<date>.db` next to the new one. The app continues with an empty
  history.
- **"Hand history cannot be saved this session":** the data directory was not writable, or
  another copy of the app was using the database. The app keeps working, but nothing is saved
  this session; the existing history is left untouched.
- **Starting over:** Settings → *Delete hand history and statistics*, or delete
  `poker_practice.db` from the data directory while the app is closed.
- **Windows SmartScreen or antivirus warnings:** the executable is not code-signed, and
  PyInstaller executables are sometimes flagged. Choose *More info → Run anyway*, or sign the
  build.
- **Verifying an installation:** run `PokerPractice.exe --self-test`. The executable has no
  console, so check its exit code (0 means success) and the `Self-test:` lines in the log file.
- **Build log shows a PyInstaller traceback about `libqmlassetdownloaderprivateplugin.so`:**
  this is a harmless logging bug in PyInstaller's Qt hook for a PySide6 labs plugin the app does
  not use. The build still succeeds.
- **Linux: `Could not load the Qt platform plugin "xcb"`:** install the system package
  `libxcb-cursor0`.
- **The 3D table is slow or does not appear:** the log names the graphics device at startup
  (`Graphics: …`). Software renderers (llvmpipe, Microsoft Basic Render Driver) get a lighter 3D
  table; on very slow machines choose Settings → *Table* → *Classic 2D*. If the window uses Qt's
  software renderer the classic table is shown automatically.
