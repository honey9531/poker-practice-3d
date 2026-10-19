"""Representative table states for the gallery, screenshots and UI tests."""

from __future__ import annotations

from services.table_view import (
    ActionView,
    BetPreset,
    PotView,
    SeatView,
    TableView,
    display_slots,
)


def preview_table(players: int = 6, *, showdown: bool = False) -> TableView:
    """A mid-hand (or showdown) six-max table with every visual element in use."""
    names = ["You", "Avery", "Blake", "Casey", "Drew", "Emery"][:players]
    styles = ["", "Balanced", "Aggressive", "Conservative", "Balanced", "Aggressive"]
    slots = display_slots(list(range(players)), human_seat=0)
    seats = []
    for seat, name in enumerate(names):
        human = seat == 0
        folded = seat == 3 and players > 3
        all_in = seat == 2 and players > 2
        winner = showdown and seat == 1
        cards: tuple[str, ...]
        if human:
            cards = ("Ah", "Kh")
        elif showdown and not folded:
            cards = {1: ("Qs", "Qd"), 2: ("9c", "9d"), 4: ("Jh", "Tc"), 5: ("7s", "6s")}.get(seat, ("2c", "3d"))
        else:
            cards = ("", "")
        seats.append(
            SeatView(
                seat=seat,
                slot=slots[seat],
                name=name,
                stack={0: 1840, 1: 2310, 2: 0, 3: 965, 4: 1500, 5: 3725}.get(seat, 1000),
                bet=0 if showdown else {0: 120, 1: 360, 2: 480, 4: 120}.get(seat, 0),
                cards=() if folded else cards,
                folded=folded,
                all_in=all_in,
                is_human=human,
                # Heads-up the button posts the small blind.
                is_dealer=seat == (0 if players == 2 else players - 1),
                is_small_blind=seat == 0,
                is_big_blind=seat == 1,
                to_act=not showdown and human,
                last_action={1: "Raise 360", 2: "All-in 480", 3: "Fold", 4: "Call 120"}.get(seat, ""),
                is_winner=winner,
                won_amount=3330 if winner else 0,
                hand_label="Three of a kind, Queens" if winner else ("Pair of Nines" if showdown and seat == 2 else ""),
                best_cards=("Qs", "Qd", "Qh", "Kd", "8c") if winner else (),
                style=styles[seat],
            )
        )
    pots = (
        PotView("Main pot", 2160, tuple(n for n in names if n != "Casey")),
        PotView("Side pot 1", 1170, ("You", "Avery", "Drew", "Emery")),
    ) if players > 2 else (PotView("Main pot", 720, tuple(names)),)
    actions = None if showdown else ActionView(
        step=7, can_fold=True, can_check=False, can_call=True, call_amount=360,
        can_bet=False, can_raise=True, can_all_in=True, min_to=840, max_to=1960,
        stack=1840, committed=120,
        presets=(
            BetPreset("Min", 840), BetPreset("½ Pot", 1290), BetPreset("¾ Pot", 1700),
            BetPreset("Pot", 1960), BetPreset("All-in", 1960),
        ),
    )
    return TableView(
        seats=tuple(seats),
        board=("Qh", "8c", "Kd") + (("4s", "2h") if showdown else ("7d",)),
        pots=pots,
        total_pot=sum(p.amount for p in pots) + (0 if showdown else sum(s.bet for s in seats)),
        street="showdown" if showdown else "turn",
        hand_number=42,
        small_blind=10,
        big_blind=20,
        message="Avery wins 3,330 with Three of a kind, Queens" if showdown else "Your turn: call 360 or raise",
        actions=actions,
        hand_in_progress=not showdown,
        session_active=True,
        winning_cards=("Qh", "Kd", "8c") if showdown else (),
    )
