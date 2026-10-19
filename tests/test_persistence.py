"""SQLite persistence: codec, migrations, recovery, history, statistics, replay, settings."""

import json
import random
import sqlite3

import pytest

from poker import Action, Table
from poker.events import HandEnded, HandStarted
from poker_helpers import make_hand
from services.database import SCHEMA_VERSION, Database, DatabaseError
from services.hand_log import describe_events
from services.hand_presenter import HandPresenter
from services.history import HistoryStore
from services.history_codec import RecordError, decode_events, encode_events
from services.recorder import HistoryRecorder
from services.replay import ReplaySession, checkpoints
from services.settings import AppSettings
from services.statistics import aggregate, hand_facts
from services.wording import says


def random_hands(seed, count=40, players=4):
    rng = random.Random(seed)
    table = Table([(f"P{i}" if i else "You", 1000) for i in range(players)], 5, 10, rng=rng)
    hands = []
    for _ in range(count):
        if not table.can_start_hand:
            break
        hand = table.start_hand()
        while not hand.is_complete:
            legal = hand.legal_actions()
            roll = rng.random()
            if legal.can_bet_or_raise and roll < 0.2:
                action = Action.raise_to(legal.min_to) if legal.can_raise else Action.bet(legal.min_to)
            elif legal.can_all_in and roll < 0.25:
                action = Action.all_in()
            elif not legal.can_check and roll < 0.45:
                action = Action.fold()
            else:
                action = Action.check() if legal.can_check else Action.call()
            hand.act(legal.seat, action)
        table.settle_hand()
        hands.append(hand)
    return hands


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def store(db):
    return HistoryStore(db)


# --- codec --------------------------------------------------------------------

def test_events_round_trip_through_json():
    for hand in random_hands(1, count=30):
        assert decode_events(encode_events(hand.events)) == list(hand.events)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        json.dumps({"version": 99, "events": []}),
        json.dumps({"version": 1, "events": []}),
        json.dumps({"version": 1, "events": [{"type": "nonsense"}]}),
        json.dumps({"version": 1, "events": [{"type": "blind", "seat": 0}]}),
        json.dumps({"version": 1, "events": ["x"]}),
    ],
)
def test_malformed_records_are_rejected(text):
    with pytest.raises(RecordError):
        decode_events(text)


def test_truncated_hand_is_rejected():
    hand = random_hands(2, count=1)[0]
    payload = json.loads(encode_events(hand.events))
    payload["events"] = payload["events"][:-1]  # drop HandEnded
    with pytest.raises(RecordError):
        decode_events(json.dumps(payload))


# --- database -----------------------------------------------------------------

def test_new_database_is_migrated(db):
    assert db.schema_version == SCHEMA_VERSION
    tables = {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sessions", "hands", "hand_players", "settings"} <= tables


def test_reopening_keeps_data(tmp_path):
    path = tmp_path / "keep.db"
    first = Database(path)
    HistoryStore(first).save_settings({"k": 1})
    first.close()
    second = Database(path)
    assert HistoryStore(second).load_settings() == {"k": 1}
    assert second.recovered_from is None
    second.close()


def test_corrupted_file_is_moved_aside_and_replaced(tmp_path):
    path = tmp_path / "broken.db"
    path.write_bytes(b"this is definitely not an sqlite database" * 100)
    db = Database(path)
    assert db.recovered_from is not None and db.recovered_from.exists()
    assert db.schema_version == SCHEMA_VERSION
    HistoryStore(db).save_settings({"ok": True})
    db.close()


def test_newer_schema_is_refused(tmp_path):
    path = tmp_path / "future.db"
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    conn.close()
    with pytest.raises(DatabaseError):
        Database(path)


# --- statistics facts -----------------------------------------------------------

def test_facts_follow_definitions():
    # Seat 0 button, seat 1 SB, seat 2 BB.
    hand = make_hand([1000, 1000, 1000], button=0,
                     holes={0: "AhAd", 1: "7c2d", 2: "KsQs"}, board="Ac 9d 4h 2s Jc")
    hand.act(0, Action.raise_to(30))  # VPIP + PFR
    hand.act(1, Action.fold())  # posted SB only: not VPIP
    hand.act(2, Action.call())  # VPIP, no PFR
    for _ in range(3):
        hand.act(2, Action.check())
        hand.act(0, Action.check())
    facts = {f.seat: f for f in hand_facts(hand.events)}
    assert (facts[0].vpip, facts[0].pfr, facts[0].showdown, facts[0].won_showdown) == (True, True, True, True)
    assert (facts[1].vpip, facts[1].pfr, facts[1].saw_flop, facts[1].showdown) == (False, False, False, False)
    assert (facts[2].vpip, facts[2].pfr, facts[2].saw_flop, facts[2].won_showdown) == (True, False, True, False)
    # Pot 65 (30 + 5 + 30): seat 0 wins it after putting in 30.
    assert facts[0].won_amount == 65 and facts[0].net == 35
    assert facts[1].net == -5 and facts[2].net == -30
    stats = aggregate([facts[0]])
    assert (stats.hands, stats.hands_won, stats.vpip, stats.showdown_win_rate) == (1, 1, 1.0, 1.0)


def test_checking_big_blind_is_not_vpip():
    hand = make_hand([1000, 1000], button=0)
    hand.act(0, Action.call())
    hand.act(1, Action.check())
    while not hand.is_complete:
        legal = hand.legal_actions()
        hand.act(legal.seat, Action.check())
    facts = {f.seat: f for f in hand_facts(hand.events)}
    assert facts[0].vpip and not facts[1].vpip


# --- history store ------------------------------------------------------------

def record_all(store, hands):
    session = store.start_session("You", {"opponents": 3})
    for number, hand in enumerate(hands, 1):
        store.record_hand(session, number, hand.events, human_seat=0,
                          styles={1: "Balanced"}, summary="summary")
    return session


def test_record_list_and_load(store):
    hands = random_hands(3, count=10)
    record_all(store, hands)
    listed = store.list_hands()
    assert len(listed) == len(hands)
    assert listed[0].hand_number == len(hands)  # most recent first
    record = store.load_hand(listed[-1].id)
    assert list(record.events) == list(hands[0].events)
    assert {p.seat for p in record.players} == {p.seat for p in hands[0].players}
    assert sum(p.net for p in record.players) == 0


def test_sql_statistics_match_event_derived_statistics(store):
    hands = random_hands(4, count=60)
    session = record_all(store, hands)
    expected = aggregate(f for h in hands for f in hand_facts(h.events) if f.seat == 0)
    assert store.statistics() == expected
    assert store.statistics(session) == expected
    assert store.statistics(session + 99).hands == 0


def test_statistics_are_per_session(store):
    hands = random_hands(5, count=20)

    def human_hands(subset):
        # Only hands the human was dealt into count (they may bust part way).
        return sum(1 for h in subset if any(p.seat == 0 for p in h.players))

    first = record_all(store, hands[:8])
    second = record_all(store, hands[8:])
    assert store.statistics(first).hands == human_hands(hands[:8])
    assert store.statistics(second).hands == human_hands(hands[8:])
    assert store.statistics().hands == human_hands(hands)
    sessions = store.list_sessions()
    assert [s.id for s in sessions] == [second, first]
    assert sessions[1].hands == human_hands(hands[:8])


def test_corrupted_record_is_isolated(store, db):
    hands = random_hands(6, count=3)
    record_all(store, hands)
    bad_id = store.list_hands()[1].id
    with db.transaction() as conn:
        conn.execute("UPDATE hands SET events = '{broken' WHERE id = ?", (bad_id,))
    assert len(store.list_hands()) == 3  # the list still works
    with pytest.raises(RecordError):
        store.load_hand(bad_id)
    store.load_hand(store.list_hands()[0].id)


def test_clear_removes_history_but_keeps_settings(store):
    record_all(store, random_hands(7, count=3))
    store.save_settings({"animations_enabled": False})
    store.clear()
    assert store.list_hands() == [] and store.statistics().hands == 0
    assert store.load_settings() == {"animations_enabled": False}


def test_open_sessions_are_closed_at_startup(store):
    session = store.start_session("You", {})
    store.close_open_sessions()
    assert store.list_sessions()[0].ended_at is not None
    assert store.list_sessions()[0].id == session


# --- recorder -----------------------------------------------------------------

def test_recorder_reports_failures_without_raising(store, db):
    from services.game_session import GameSession, SessionConfig

    errors = []
    recorder = HistoryRecorder(store, on_error=errors.append)
    session = GameSession(SessionConfig(opponents=1, seed=1))
    recorder.session_started(session)
    db.close()  # every further write fails
    hand = random_hands(8, count=1, players=2)[0]
    recorder.hand_completed(session, hand)
    recorder.session_ended()
    assert errors and all("Could not" in e for e in errors)


# --- replay -------------------------------------------------------------------

def test_replay_is_read_only_and_reaches_final_state(store, db):
    hands = random_hands(9, count=5)
    record_all(store, hands)
    before = (store.statistics(), db.conn.execute("SELECT COUNT(*) FROM hands").fetchone()[0])
    summary = store.list_hands()[0]
    replay = ReplaySession(store.load_hand(summary.id))
    assert replay.position == 0
    replay.seek(replay.steps - 1)
    view = replay.build_view()
    final = hands[-1].result.final_stacks
    assert {s.seat: s.stack for s in view.seats} == dict(final)
    replay.seek(0)
    assert replay.build_view().board == ()
    assert (store.statistics(), db.conn.execute("SELECT COUNT(*) FROM hands").fetchone()[0]) == before


def test_replay_hides_unshown_cards_unless_revealing(store):
    hands = random_hands(10, count=30)
    record_all(store, hands)
    for summary in store.list_hands():
        record = store.load_hand(summary.id)
        replay = ReplaySession(record)
        replay.seek(replay.steps - 1)
        folded = [s for s in replay.build_view().seats if s.folded and not s.is_human]
        if folded:
            assert all(s.cards == () for s in folded)
            replay.reveal_all = True
            revealed = {s.seat: s for s in replay.build_view().seats}
            assert all(all(revealed[s.seat].cards) for s in folded)
            return
    pytest.fail("no hand with a folded opponent")


def test_replay_checkpoints_cover_every_action():
    hand = random_hands(11, count=1)[0]
    points = checkpoints(hand.events)
    assert points[-1] == len(hand.events)
    actions = sum(1 for e in hand.events if type(e).__name__ == "PlayerActed")
    assert len(points) >= actions + 1
    assert isinstance(hand.events[0], HandStarted) and isinstance(hand.events[-1], HandEnded)
    assert HandPresenter.from_events(hand.events[: points[-1]]).complete


# --- settings and wording -------------------------------------------------------

def test_settings_validation_falls_back_to_defaults():
    settings = AppSettings.from_mapping({
        "animations_enabled": "yes", "analysis_mode": True, "chip_scheme": "neon",
        "session_defaults": {"opponents": 9, "difficulty": "hard", "startingStack": "lots"},
    })
    assert settings.animations_enabled is True  # invalid type -> default
    assert settings.analysis_mode is True
    assert settings.chip_scheme == "classic"
    assert settings.session_defaults["opponents"] == 3
    assert settings.session_defaults["difficulty"] == "hard"
    assert AppSettings.from_mapping(settings.to_mapping()) == settings


def test_hand_log_reads_naturally():
    hand = make_hand([1000, 1000], button=0)
    hand.act(0, Action.raise_to(60))
    hand.act(1, Action.fold())
    lines = [line.text for line in describe_events(hand.events)]
    assert lines[0] == "P0 has the button; blinds 5/10"
    assert "P0 raises to 60" in lines and "P1 folds" in lines
    assert lines[-1].startswith("P0 wins the main pot")


@pytest.mark.parametrize("verb, you", [("raises", "You raise"), ("has", "You have"),
                                       ("pushes", "You push"), ("wins", "You win"), ("is", "You are")])
def test_second_person_agreement(verb, you):
    assert says("You", verb) == you
    assert says("Avery", verb) == f"Avery {verb}"
