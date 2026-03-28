import math
from unittest.mock import MagicMock, patch

import pytest

from main import MACD_MIN_BARS, MACD_FAST, MACD_SLOW, MACD_SIGNAL, MAGNIFICENT_7
from main import calculate_macd_signal, build_target_portfolio


def _make_price_data(closes: list[float]) -> list[dict]:
    return [{"close": c, "datetime": float(i * 300_000)} for i, c in enumerate(closes)]


def _bullish_prices(n: int = 100) -> list[float]:
    """Flat then sharp upswing — fast EMA rises faster than slow EMA, MACD > signal."""
    flat = [100.0] * int(n * 0.6)
    surge = [100.0 + i * 3.0 for i in range(n - int(n * 0.6))]
    return flat + surge


def _bearish_prices(n: int = 100) -> list[float]:
    """Flat then sharp downswing — fast EMA falls faster than slow EMA, MACD < signal."""
    flat = [100.0] * int(n * 0.6)
    crash = [100.0 - i * 3.0 for i in range(n - int(n * 0.6))]
    return flat + crash


# --- calculate_macd_signal ---

def test_bullish_signal_is_positive():
    price_data = _make_price_data(_bullish_prices(100))
    score = calculate_macd_signal("AAPL", price_data)
    assert score > 0, f"Expected positive score, got {score}"


def test_bearish_signal_is_negative():
    price_data = _make_price_data(_bearish_prices(100))
    score = calculate_macd_signal("AAPL", price_data)
    assert score < 0, f"Expected negative score, got {score}"


def test_insufficient_data_returns_zero():
    price_data = _make_price_data([100.0] * (MACD_MIN_BARS - 1))
    score = calculate_macd_signal("AAPL", price_data)
    assert score == 0.0


def test_exact_min_bars_does_not_raise():
    price_data = _make_price_data([100.0 + i for i in range(MACD_MIN_BARS)])
    score = calculate_macd_signal("AAPL", price_data)
    assert isinstance(score, float)
    assert not math.isnan(score)


# --- build_target_portfolio ---

@patch("main.get_price_history")
@patch("main.calculate_macd_signal")
def test_portfolio_selects_positive_signals(mock_signal, mock_history):
    mock_history.return_value = _make_price_data([100.0] * 50)
    # 3 positives: AAPL, MSFT, NVDA
    signal_map = {s: (1.0 if s in {"AAPL", "MSFT", "NVDA"} else -1.0) for s in MAGNIFICENT_7}
    mock_signal.side_effect = lambda sym, data: signal_map[sym]

    selected = build_target_portfolio()

    assert set(selected) == {"AAPL", "MSFT", "NVDA"}
    assert len(selected) == 3


@patch("main.get_price_history")
@patch("main.calculate_macd_signal")
def test_full_risk_off_returns_empty(mock_signal, mock_history, caplog):
    mock_history.return_value = _make_price_data([100.0] * 50)
    mock_signal.return_value = -1.0

    import logging
    with caplog.at_level(logging.INFO):
        selected = build_target_portfolio()

    assert selected == []
    assert "All MACD signals negative" in caplog.text
