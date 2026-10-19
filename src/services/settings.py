"""Application settings with validation and defaults.

Stored values that are missing, of the wrong type or out of range fall back to
defaults, so a damaged settings table can never stop the application.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from services.chips import DEFAULT_DENOMINATIONS, ChipDenomination

CHIP_SCHEMES: dict[str, tuple[ChipDenomination, ...]] = {
    "classic": DEFAULT_DENOMINATIONS,
    "vivid": (
        ChipDenomination(1, "#f4f1ea", "#1c8bc9", "#155f8a"),
        ChipDenomination(5, "#d8262f", "#fff4d6", "#8f1219"),
        ChipDenomination(25, "#119b55", "#fff4d6", "#0a6034"),
        ChipDenomination(100, "#1a1a1f", "#e9c46a", "#1a1a1f"),
        ChipDenomination(500, "#7b2fbf", "#fff4d6", "#4d1a7d"),
        ChipDenomination(1000, "#f2b705", "#1a1a1f", "#6b5000"),
        ChipDenomination(5000, "#e05a1b", "#fff4d6", "#8a330a"),
    ),
}

DEFAULT_SESSION = {
    "opponents": 3,
    "startingStack": 2000,
    "bigBlind": 20,
    "opponentStyle": "mixed",
    "difficulty": "normal",
    "blindIncreaseEvery": 0,
}

_SESSION_CHOICES = {
    "opponents": (1, 2, 3, 4, 5),
    "startingStack": (1000, 2000, 5000, 10000),
    "bigBlind": (10, 20, 50, 100),
    "opponentStyle": ("mixed", "conservative", "balanced", "aggressive"),
    "difficulty": ("easy", "normal", "hard"),
    "blindIncreaseEvery": (0, 5, 10, 20),
}

AUTO_DEAL_DELAY_MS = 2500


@dataclass(frozen=True, slots=True)
class AppSettings:
    animations_enabled: bool = True
    analysis_mode: bool = False
    auto_deal: bool = False
    chip_scheme: str = "classic"
    session_defaults: Mapping[str, Any] = field(default_factory=lambda: dict(DEFAULT_SESSION))
    window: Mapping[str, int] = field(default_factory=dict)  # x, y, width, height, maximized

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AppSettings":
        settings = cls()

        def flag(key: str, default: bool) -> bool:
            value = values.get(key, default)
            return value if isinstance(value, bool) else default

        scheme = values.get("chip_scheme", settings.chip_scheme)
        stored_session = values.get("session_defaults")
        session = dict(DEFAULT_SESSION)
        if isinstance(stored_session, Mapping):
            for key, choices in _SESSION_CHOICES.items():
                if stored_session.get(key) in choices:
                    session[key] = stored_session[key]
        return replace(
            settings,
            animations_enabled=flag("animations_enabled", settings.animations_enabled),
            analysis_mode=flag("analysis_mode", settings.analysis_mode),
            auto_deal=flag("auto_deal", settings.auto_deal),
            chip_scheme=scheme if scheme in CHIP_SCHEMES else settings.chip_scheme,
            session_defaults=session,
            window=cls.clean_window(values.get("window")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "animations_enabled": self.animations_enabled,
            "analysis_mode": self.analysis_mode,
            "auto_deal": self.auto_deal,
            "chip_scheme": self.chip_scheme,
            "session_defaults": dict(self.session_defaults),
            "window": dict(self.window),
        }

    @staticmethod
    def clean_window(value: Any) -> dict[str, int]:
        """Window geometry with sane integer values, or {} if unusable."""
        if not isinstance(value, Mapping):
            return {}
        try:
            geometry = {key: int(value[key]) for key in ("x", "y", "width", "height")}
        except (KeyError, TypeError, ValueError):
            return {}
        if not (640 <= geometry["width"] <= 16384 and 480 <= geometry["height"] <= 16384):
            return {}
        geometry["maximized"] = int(bool(value.get("maximized", 0)))
        return geometry

    @staticmethod
    def clean_session_defaults(values: Mapping[str, Any]) -> dict[str, Any]:
        """Keep only recognised, valid session options."""
        return {
            key: values[key]
            for key, choices in _SESSION_CHOICES.items()
            if key in values and values[key] in choices
        }
