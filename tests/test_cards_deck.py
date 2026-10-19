import random

import pytest

from poker import FULL_DECK, Card, Deck, DeckError, Rank, Suit, parse_cards


def test_full_deck_has_52_unique_cards():
    assert len(FULL_DECK) == 52
    assert len(set(FULL_DECK)) == 52
    for suit in Suit:
        assert sum(c.suit is suit for c in FULL_DECK) == 13
    for rank in Rank:
        assert sum(c.rank is rank for c in FULL_DECK) == 4


def test_card_parsing_and_formatting():
    card = Card.from_str("As")
    assert card == Card(Rank.ACE, Suit.SPADES)
    assert str(card) == "As"
    assert Card.from_str("td") == Card(Rank.TEN, Suit.DIAMONDS)
    assert parse_cards("2c Kh") == parse_cards("2cKh") == [
        Card(Rank.TWO, Suit.CLUBS), Card(Rank.KING, Suit.HEARTS)
    ]
    assert all(Card.from_str(str(c)) == c for c in FULL_DECK)


@pytest.mark.parametrize("text", ["", "A", "1s", "Ax", "10s", "AsK"])
def test_invalid_cards_are_rejected(text):
    with pytest.raises(ValueError):
        Card.from_str(text)


@pytest.mark.parametrize("text", ["A", "AsK", "As 1d"])
def test_invalid_card_lists_are_rejected(text):
    with pytest.raises(ValueError):
        parse_cards(text)


def test_empty_card_list():
    assert parse_cards("") == []


def test_suit_colours():
    assert Suit.HEARTS.is_red and Suit.DIAMONDS.is_red
    assert not Suit.SPADES.is_red and not Suit.CLUBS.is_red


def test_deck_deals_every_card_exactly_once():
    deck = Deck(random.Random(1))
    dealt = deck.deal(52)
    assert sorted(dealt, key=str) == sorted(FULL_DECK, key=str)
    assert deck.remaining == 0
    with pytest.raises(DeckError):
        deck.deal_one()


def test_deck_shuffle_is_seeded():
    assert Deck(random.Random(7)).deal(52) == Deck(random.Random(7)).deal(52)
    assert Deck(random.Random(7)).deal(52) != Deck(random.Random(8)).deal(52)


def test_deck_tracks_dealt_cards():
    deck = Deck(random.Random(3))
    first = deck.deal(5)
    assert deck.dealt == tuple(first)
    assert deck.remaining == 47


def test_stacked_deck_puts_cards_on_top_without_duplicates():
    top = parse_cards("As Kd 2c")
    deck = Deck.stacked(top)
    assert deck.deal(3) == top
    rest = deck.deal(49)
    assert len(set(rest)) == 49
    assert not set(rest) & set(top)


def test_stacked_deck_rejects_duplicates():
    with pytest.raises(DeckError):
        Deck.stacked(parse_cards("As As"))
