# Architecture

## Layers

```
QML (qml/)            presentation, layout, input, animation — no poker rules
   │  properties / signals / slots / list models
bridge (src/bridge)   thin QObject adapters; converts engine state to QML-friendly data
   │
services (src/services)  application bootstrap, game controller, persistence, statistics
   │
poker (src/poker), ai (src/ai)   pure Python; no Qt imports; fully unit-testable
```

Dependencies only point downward. `poker` and `ai` never import Qt, so all rules are tested
without a GUI.

## Decisions

### Top-level packages under `src/`
The packages `poker`, `ai`, `services` and `bridge` are importable from `src/`
(`main.py` and `tests/conftest.py` add it to `sys.path`; PyInstaller will use it as `pathex`).

### QML singletons via `@QmlSingleton` + Python-owned instances
Bridge classes are registered with PySide6's `@QmlNamedElement`/`@QmlSingleton` decorators in
the `PokerPractice.Bridge` module. Each class's static `create()` returns an instance that
Python created beforehand and installed through `bridge.registry.install()`, with ownership
set to C++/Python so QML never deletes it.

`qmlRegisterSingletonInstance` was tried first and rejected: under PySide6 6.12, importing a
module registered that way makes built-in types (`Item`, `Rectangle`) unassignable to
`data` ("expected QObject"). Context properties were avoided because they are untyped and
discouraged in Qt 6.

### QML loaded from the filesystem
QML and assets are loaded from `resource_root()` — the project root in development, or
`sys._MEIPASS` in a PyInstaller bundle. This keeps QML editable without a compile step; the
packaging phase bundles `qml/` and `assets/` as data files. Compiling a `.qrc` with
`pyside6-rcc` remains an option if bundling proves fragile.

### Qt Quick Controls "Basic" style
Set before the application starts. It is fully customisable and renders identically on every
platform; the native Windows style restricts control customisation.

### User data location
`services.paths.user_data_dir()` resolves to `%APPDATA%\PokerPractice` on Windows (never
the install directory), overridable with `POKER_PRACTICE_DATA_DIR`.

### Logging
`services.logging_setup` writes a rotating log in `<data dir>/logs/` and installs a Qt message
handler so QML warnings/errors are captured. `load_ui()` also collects `QQmlEngine.warnings`
and raises `QmlLoadError` if the root window fails to load.

### Signals
`install_quit_on_signals()` quits on SIGINT/SIGTERM. A 250 ms no-op timer lets the Python
interpreter run signal handlers while Qt's event loop is idle.

## Poker engine (`src/poker`)

| Module | Responsibility |
| --- | --- |
| `cards.py` | `Rank`, `Suit`, immutable `Card`, parsing (`"As"`), `FULL_DECK` |
| `deck.py` | Seeded shuffle; dealing can never repeat a card; `Deck.stacked()` for deterministic scenarios/replays |
| `evaluator.py` | `evaluate()` 5–7 cards → comparable `HandValue(category, tiebreak)`; `best_five()` for highlighting; `describe()` |
| `pots.py` | `build_pots()` layers contributions into main/side pots; `award_pots()` with split and odd-chip handling |
| `actions.py` | `Action` (BET/RAISE amounts are *raise-to* street totals), `LegalActions` |
| `events.py` | Immutable event records — the single source for history, statistics and UI sequencing |
| `hand.py` | `HoldemHand` state machine for one hand |
| `table.py` | `Table`: stacks between hands, button rotation, blind levels, session reset |

All chip amounts are `int`. `HoldemHand` verifies chip conservation when it distributes the pot.

### Rules as implemented

- **Positions:** heads-up, the button posts the small blind and acts first pre-flop, last afterwards.
  Otherwise SB/BB are the next two seats after the button. Pre-flop action starts after the BB;
  later streets start with the first active player after the button.
- **Button:** "moving button" — it advances to the next seat with chips; busted seats are
  skipped and there are no dead blinds. (Simpler than the dead-button rule, standard for
  practice/home games.)
- **Short blinds:** a player who cannot cover a blind posts all they have and is all-in; the
  amount to call remains the full big blind (excess is returned as an uncalled bet).
- **Minimum bet** is the big blind. **Minimum raise:** the bet must grow by at least the
  largest bet/raise increment of the street.
- **Incomplete all-in raises** (smaller than a minimum raise) do not reopen betting for players
  who already acted. Several short all-ins that together amount to a full raise since a
  player's last action *do* reopen it for that player (TDA-style cumulative rule).
- A player cannot raise when every opponent is all-in (call or fold only).
- **Uncalled chips** are returned at the end of each street and when a hand ends by folds.
- **Run-outs:** when fewer than two players can still bet, remaining streets are dealt
  (with burns) without action and the hand goes to showdown.
- **Split pots:** each pot is split evenly among the best hands eligible for it; leftover
  chips go one at a time to winners in seat order starting left of the button.
- **Duplicate submissions:** `act(..., expected_action_count=n)` rejects actions prepared for a
  decision point that has already passed (`StaleActionError`). Acting out of turn, after the
  hand ended, or with an illegal amount raises `IllegalActionError`/`HandStateError` without
  changing state.
- Folding is always permitted when it is the player's turn (the UI may ask for confirmation
  when checking is free).

### Testing approach

- Deterministic scenarios use `tests/poker_helpers.make_hand()`, which stacks the deck in real
  dealing order so hole cards and boards are specified exactly.
- The evaluator is cross-checked against an independent brute-force 5-card reference on
  thousands of random 5/6/7-card hands.
- Randomized sessions (seeded) play hundreds of hands with random legal actions and assert
  chip conservation after every action, no negative stacks, no duplicate cards, pot awards
  equal to contributions and zero-sum results.

## Cards and chips (Phase 3)

### Playing cards: generated SVG assets
`tools/generate_cards.py` writes `assets/cards/{2c..As}.svg` and `back.svg` (all original artwork).
The generated files are committed so the app needs no build step;
`tests/test_card_assets.py` fails if they drift from the generator.

- Poker proportions 63 × 88 (viewBox 630 × 880); rounded corners, warm-white face gradient.
- Rank indices are **stroke-drawn vector glyphs**, not font text, so cards render identically on
  every system and never depend on platform card/suit glyphs.
- Standard pip layouts (lower-half pips inverted; the seven's extra pip is in the upper half),
  ornamental ace of spades, double-ended court figures (J/Q/K differ in headwear and held item;
  suits differ in robe colour and band pattern), symmetrical lattice-and-medallion back.
- Only SVG Tiny 1.2 features that Qt SVG supports (no `<pattern>`/`<clipPath>`: the back's lattice
  is clipped geometrically in Python).

`qml/components/PlayingCard.qml` shows a card: the body always keeps 63:88 inside whatever box it
gets, `sourceSize` follows the on-screen size × device pixel ratio (crisp on high-DPI), and it
offers face-up/face-down (3D flip via `Flipable`), unknown (`card: ""` → back), `highlighted`
(gold ring + lift), `dimmed`, and `dealFrom(dx, dy, delay)`. `animated: false` disables motion.

### Chips: QML Shapes, configurable colours
Chip colours must be configurable, so chips are drawn in QML rather than as fixed assets:

- `PokerChip.qml` — top view: body, six alternating edge inserts (one dashed stroke), dashed
  inner ring, centre inlay with the denomination, lighting gradient. Labels hide below a legible
  size (colour identifies the chip).
- `ChipStack.qml` — one denomination in perspective. Lower chips draw only their edge band
  (cylindrical shading, staggered inserts, seam); the top chip draws the full face, squashed.
- `ChipPile.qml` — an amount as stacks (largest denomination left, ≤ 10 chips per stack), with
  `animateFrom(dx, dy, delay)` for chip movement.

The amount → chips breakdown is Python (`services/chips.py`, greedy, exact for any amount since a
1-chip always exists) and reaches QML through the `Chips` singleton (`bridge/chips_bridge.py`),
which also publishes the denomination colour scheme and signals changes. Breakdown is display only:
the engine never sees chips.

### Gallery
`qml/screens/GalleryScreen.qml` shows all 52 cards, states, chips at several sizes, stacks and
piles. Open it with **Ctrl+Shift+G** or `tools/screenshot.py --screens gallery`.

## Table UI (Phase 4)

### View snapshots (`services/table_view.py`)
`TableView`, `SeatView`, `PotView`, `ActionView` and `BetPreset` are immutable snapshots of
exactly what the player may see. Opponents' hole cards are `""` (face down) until legitimately
revealed, so hidden information can never reach QML. `display_slots()` maps table seats to six
fixed screen slots with the human at the bottom and clockwise order preserved
(2 players: bottom/top; 3: bottom/upper-left/upper-right; …).

`services/preview.py` builds representative states (six-max mid-hand, showdown, heads-up) for
the gallery, screenshots (`tools/screenshot.py --preview hand|showdown|headsup|none`) and UI tests.

### Bridge
- `GameBridge` (QML `Game`) publishes a snapshot via `set_view()`: scalar properties with a
  single `viewChanged` notify, `pots` as a list, `actions` as a map (empty unless the human is
  to act), and `players` as a `PlayerListModel`.
- `PlayerListModel` (`QAbstractListModel`) exposes every `SeatView` field as a camelCase role.
  Updates emit `dataChanged` with only the changed roles; the model resets only when the set of
  seats changes. Seat delegates therefore persist, so card and chip animations are not restarted
  by unrelated updates.
- Community cards are bound by position (`Repeater { model: 5 }`), so a new card animates in
  without recreating the others.

### QML
- `PokerTable`: stadium-shaped padded rail (gradient, highlight, stitching), wood trim, felt with
  a radial overhead light, a tiled noise texture (`assets/table/felt_noise.png`, generated by
  `tools/generate_textures.py`) masked to the felt with `MultiEffect`, and a betting line.
- `TableScreen` lays out seats, bets and position markers at fixed fractions of the table
  rectangle per display slot; the table keeps a 2.05:1 aspect and every size derives from one
  `unit`, so the layout scales from 1024×640 to 4K without overlap.
- `PlayerSeat`: hole cards tucked behind a nameplate (avatar ring colour reflects opponent
  style), stack, last-action pill, all-in/fold/winner states, showdown hand label, turn glow.
- `ActionPanel`: summary (to call, pot, stack, minimum raise), presets, slider (snaps to
  big-blind multiples but always reaches min and max), numeric field (clamped to the legal
  range), Fold / Check-Call / Bet-Raise / All-in buttons with F/C/R/A shortcuts. Each
  submission carries the engine's action step; the panel locks after a click until the step
  changes, so double clicks cannot submit twice.
- `SessionSetupScreen`: opponents (1–5), starting stack, blinds, opponent style, difficulty.

## Engine ↔ QML (Phase 5)

```
QML ── Game.submitAction(kind, amount, step) ──► GameBridge ──► GameController ──► GameSession ──► HoldemHand
 ▲                                                                    │ QTimer pacing
 └──────────── Game properties / PlayerListModel ◄── set_view(TableView) ◄── build_view() ◄── HandPresenter(events)
```

- **`HandPresenter`** (`services/hand_presenter.py`) rebuilds the visible table by folding the
  engine's event log one event at a time. The engine resolves an all-in run-out inside a single
  `act()`; presentation follows behind it, so the UI can reveal the flop, turn, river, showdown
  and pot awards at a human pace. Stored histories can be replayed with the same code.
- **`GameSession`** (`services/game_session.py`, no Qt) owns the `Table`, seats the human at seat
  0 and opponents in seats 1–5, applies human actions (rejecting stale steps), asks strategies for
  opponent actions, and builds `TableView`s: visibility rules, bet presets (½, ¾, full pot raises
  computed as `current bet + fraction × (pot + call)`), messages, deal/session-over flags. An
  opponent strategy that returns an illegal action is logged and replaced by check/fold so the
  table can never stall.
- **`GameController`** (`services/game_controller.py`, QObject) paces everything with a single
  single-shot `QTimer`: per-event pauses (`Timing`), randomized opponent "thinking", optional
  auto-deal. Nothing sleeps or blocks the event loop. A generation counter discards callbacks
  from an abandoned session.
- **`GameBridge`** forwards `startSession`, `submitAction`, `deal`, `endSession` and publishes
  views. The decision-point `key` (`"<hand>:<step>"`) locks the action panel after a click;
  the engine's `expected_action_count` check rejects anything that still gets through, and the
  rejection is shown as a toast.
- **Opponents** see only `ai.observe(hand, seat)`: public information plus their own hole cards.
  Phase 5 seats `PassiveStrategy` (check/call) everywhere; Phase 7 replaces it.

### QA tools
`tools/walkthrough.py OUT --hands N` drives the real UI (Play → Start Session → action buttons →
a click on the table for the next hand), screenshots each street and hand result, checks chip
conservation and fails on QML
warnings.

## Complete gameplay (Phase 6)

- **All-in exposure:** when betting closes with two or more live hands before the river, the
  engine emits `CardsExposed` for each live hand before dealing the run-out; the presenter turns
  those cards face up so the run-out is watched with hands visible, as at a real table.
- **Animations driven by state changes, never by rules:** hole cards are dealt from the table
  centre in seat order (only within a short window after a new hand starts), the human's cards
  flip up when they land, board cards slide in face down and flip (flop cards staggered), new
  bets slide out from the player, bets fly to the pot when a street closes, and pots fly to the
  winners. Seat card delegates are fixed (two per seat) so a reveal flips the existing cards
  instead of recreating them.
- **Animations preference:** `App.animationsEnabled` disables QML motion and reduces controller
  pauses to 30 % (events still arrive in order).
- **Session flow:** once a hand is over, clicking the table deals the next one (also
  Space/Enter; the result banner shows the hint), End Session with confirmation, a
  session-over overlay (Play Again with the same settings, New Session, Main Menu), and Resume
  Table / New Session on the main menu while a session exists.
- **Fold safety:** folding when checking is free needs a second click ("Fold anyway?").
- **Result banner** on the felt after each hand.

## Computer opponents (Phase 7)

Practical heuristics, not a solver. All code is in `src/ai/` and sees only `observe(hand, seat)`.

- **Hand strength** (`hand_strength.py`): pre-flop strength is the Chen formula normalised to
  0..1; post-flop equity is a seeded Monte Carlo estimate against random hands for each live
  opponent (ties count as shares); draws (flush, open-ended, gutshot/one-ended) give outs.
  The Monte Carlo budget is expressed in hand evaluations per decision (easy 240, normal 480,
  hard 800) divided across players, keeping a decision under ~30 ms (95th percentile measured
  ≈15 ms six-handed on hard), so it can run on the GUI thread between animation frames.
- **Strategy** (`strategies.py`): one `HeuristicStrategy` parameterised by
  - a *style*: entry/raise thresholds, call margin over pot odds, value/raise equity thresholds,
    bluff, semi-bluff and steal rates, bet sizes, short-stack push threshold;
  - a *difficulty*: estimate noise, Monte Carlo budget, whether position and pot odds are used,
    and an occasional passive mistake rate.

  Pre-flop: push/fold below 12 big blinds; open-raise, late-position steals, limp or fold when
  unraised; facing a raise, required strength grows with its size (cheap calls need less).
  Post-flop: value bets, semi-bluffs with draws, occasional bluffs (more heads-up); facing a bet,
  compare equity to pot odds plus the style's margin (minus an implied-odds allowance for draws),
  raise with strong equity.
- **Legality:** every decision goes through `legalize()` (clamps sizes, turns impossible raises
  into calls, never folds a free check). The session additionally falls back to check/fold if a
  strategy ever produced an illegal action, so opponents can never stall the game.
- **Measured profiles** (six-handed, normal): conservative ≈13 % VPIP / 5 % PFR, balanced
  ≈25 % / 11 %, aggressive ≈40 % / 24 %.
- **Analysis mode:** each decision records a reason (e.g. "call: equity 41% vs pot odds 25%").
  The session exposes the reasons together with the opponents' hole cards *only after the hand
  is over*; the table's Analysis button shows them when analysis mode is enabled (setup screen).
- **Mixed style** seats rotate through the three styles from a random start.

## Persistence, statistics, history and settings (Phase 8)

### Storage
SQLite database `poker_practice.db` in the user-data directory (`%APPDATA%\PokerPractice` on
Windows). `services/database.py`:
- **Migrations:** ordered statement lists; `PRAGMA user_version` records the applied schema;
  each migration runs in one transaction. A database from a newer version is refused rather
  than modified.
- **Corruption:** at open, `PRAGMA quick_check` runs; an unreadable file is renamed to
  `poker_practice.corrupt-<timestamp>.db` and a fresh database is created. The main menu shows a
  notice. If the location is unusable, the app runs with an in-memory database and says so.
- Every write uses `Database.transaction()` (commit or roll back).

Schema v1: `sessions`, `hands` (summary columns + versioned JSON event log), `hand_players`
(per-player facts per hand), `settings` (JSON values).

### Recording
`HistoryRecorder` creates a session row when a session starts, records each completed hand
(from the engine's event log, not the UI), and closes the session on end/new session/quit.
Sessions left open by a crash are closed at the next start. Database errors are logged and shown
as a toast; play is never interrupted.

`services/history_codec.py` encodes events as versioned JSON and decodes them back to the
engine's event types, validating structure. A damaged row raises `RecordError`; the history list
still loads and the detail pane explains that the record is damaged.

### Statistics (`services/statistics.py`)
Facts are derived per player per hand from events and stored in `hand_players`; screens
aggregate them with SQL. Definitions (also in the module docstring):
hands played (dealt in), hands won (received chips from any pot), net chips, VPIP (pre-flop call
/bet/raise; blinds and a big-blind check do not count), PFR (pre-flop bet/raise), showdown
frequency (showdowns ÷ hands played), showdown win rate (showdowns with any pot won ÷
showdowns), biggest pot won. Tests check the SQL aggregates against the pure-Python aggregate.

### History and replay
- **History screen:** recent hands (newest first) with your cards, result and summary; the
  detail shows the board, each player's cards and result, and the chronological action log by
  street. Opponents' cards appear only if they were shown at the table unless "All cards" is
  chosen.
- **Replay:** `ReplaySession` folds the stored events with the same `HandPresenter` and
  `view_builder` as live play, pausing at meaningful checkpoints (setup, each action, each board
  card, exposures, showdown, each pot). The table screen renders it through the `Replay` bridge
  (a `GameBridge` subclass) with transport controls and "As played / Show all cards". Replays
  only read decoded events: they never write to the database or touch the live session.
- Human-facing sentences use second-person agreement for the human ("You raise", "You win").

### Settings
`AppSettings` (validated; bad stored values fall back to defaults): animations, auto-deal,
hand analysis, chip colour scheme (classic / vivid), and the last-used session options (which
pre-fill the setup screen). `Settings` bridge properties persist immediately and are applied to
the chips bridge and the game controller through a subscription.

## Polish and reliability (Phase 9)

- **Layouts** checked at 1024×640, 1024×768, 1280×800, 1366×768, 1920×1080, 2560×1080 and
  2560×1440, and at 1.5×/2× device pixel ratios. The table's size unit scales up to 160 px so
  cards, chips and seats stay in proportion on large windows; chrome uses fixed sizes and relies
  on the operating system's display scaling.
- **No replayed animations:** cards already on the board when the table appears (returning from
  the menu, replays) are shown immediately; only newly dealt cards animate.
- **Reduced motion:** with animations off, screen transitions are immediate, cards appear face
  up at once and the controller's pauses shrink to 30 %.
- **Errors:** recoverable problems from any bridge (rejected actions, storage failures) appear
  in one window-level toast. Unexpected exceptions — including those raised inside Qt callbacks,
  which cannot propagate — go through `install_exception_hook`: logged with traceback and shown
  in a dialog that names the log file.
- **Window geometry** (size, position, maximized) is saved on close and restored at start if it
  still fits the available screen area.
- **Icon:** `tools/generate_icon.py` writes `assets/icon/app.svg`, `app.png` (window icon) and a
  multi-size `app.ico` (PNG-in-ICO) for the Windows executable.

## Testing and packaging (Phase 10)

- **Self-test** (`main.py --self-test`, `services/self_test.py`) runs inside the packaged build:
  all card SVGs render through the bundled SVG plugin, textures and icon load, every screen opens
  without QML errors, complete hands are played against the computer opponents with chip
  conservation checked, hands are recorded and replayed, and the replay leaves history
  untouched. Results are printed and logged (windowed builds have no console); the exit status
  is 0 on success. Running it twice against the same data directory proves persistence.
- **PyInstaller** (`packaging/PokerPractice.spec`): one-folder build, windowed, icon and version
  resource on Windows. `qml/` and `assets/` are bundled as data; at run time
  `services.paths.resource_root()` resolves to `sys._MEIPASS` (the `_internal` folder) while
  user data still goes to `%APPDATA%\PokerPractice`.
- **Bundle filter** (`packaging/bundle_filter.py`): PyInstaller's Qt hooks pull every QML module
  and its libraries (QtWebEngine alone ~200 MB). The filter keeps only the QML modules the app
  imports, drops unused Qt libraries, Controls styles, plugins and translations (Linux bundle
  522 MB → ~200 MB) and is unit-tested for both Linux and Windows path layouts.
- **Logging in windowed builds:** the stderr handler is only installed when `sys.stderr` exists.
- **CI:** `.github/workflows/windows-build.yml` runs `packaging/build_windows.ps1` (tests, build,
  two self-test runs of the executable) on `windows-latest` and uploads the build.

## Rising blinds

`SessionConfig.blind_increase_every` (0, 5, 10 or 20 hands; chosen on the setup screen and saved
with the session defaults) turns on tournament-style blind levels. `services/blinds.py` defines the
schedule: the small blind is a whole-number multiple of the starting small blind
(×1, 2, 3, 5, 10, 15, 20, 30, …, then growing by half per level) and the big blind is always twice
the small blind, so every level is an integer. `GameSession.start_hand()` sets the table's blinds
for the next hand before dealing. The view carries the interval, the level of the hand on the table
and the hands left at that level (counting a hand in progress; 0 = "blinds go up next hand"), which
the table's top bar displays. Stacks are never topped up: chips are only won or lost.

## Opponents read betting habits

Opponents used to judge every big pre-flop raise as if it came from a strong hand, so a player who
shoved all-in every hand was almost never called (4 % of shoves) and won steadily.

`ai/tendencies.py` now records each player's *public* pre-flop habits during the session (hands
dealt, raises, all-ins), as real players notice who keeps shoving. When an opponent faces a big
pre-flop raise (≥ 12 big blinds, or a call costing ≥ 20 % of its stack) it estimates the raiser's
range: an unknown deep shover is assumed to hold about the top 6 % of hands, and the estimate moves
towards the observed all-in frequency (faster on hard, slower on easy). It then compares its equity
against that range (`equity_vs_range`, sampling from all 1,326 starting hands ranked strongest
first) with the pot odds, adding a small margin per extra opponent, and calls, re-shoves or folds.

Measured over 80 seeded sessions against three opponents, always shoving went from +425 chips per
session on average to −583 (bust in 65 of 80 sessions). A first-hand shove is still usually folded
to, which is correct against an unknown player, but it only wins the blinds.
