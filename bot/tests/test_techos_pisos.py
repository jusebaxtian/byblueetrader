import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from byblue.core.models import Candle, Direction
from byblue.strategy.techos_pisos import BB_PERIOD, CONFIRM_CANDLES, TechosPisosStrategy


def make_candle(ts: int, open_: float, close: float) -> Candle:
    return Candle(asset="EURUSD", timestamp=ts, open=open_, close=close, high=max(open_, close), low=min(open_, close))


def flat_band_candles(count: int, base: float = 1.1000, step: float = 0.0001) -> list[Candle]:
    """Small oscillation around `base` so the Bollinger Band stays tight."""
    candles = []
    for i in range(count):
        ts = i * 60
        wobble = step if i % 2 == 0 else -step
        candles.append(make_candle(ts, base, base + wobble))
    return candles


def test_insufficient_history_skips():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(5)
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "Esperando datos suficientes"


def test_three_green_candles_above_ceiling_enters_put():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(BB_PERIOD)
    start_ts = len(history) * 60
    # 3 strongly green candles closing well above the tight band -> "techo" touch.
    breakout = [
        make_candle(start_ts, 1.1000, 1.1050),
        make_candle(start_ts + 60, 1.1050, 1.1100),
        make_candle(start_ts + 120, 1.1100, 1.1150),
    ]
    signal = strategy.on_new_candle(history + breakout)
    assert signal.direction == Direction.PUT


def test_three_red_candles_below_floor_enters_call():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(BB_PERIOD)
    start_ts = len(history) * 60
    breakout = [
        make_candle(start_ts, 1.1000, 1.0950),
        make_candle(start_ts + 60, 1.0950, 1.0900),
        make_candle(start_ts + 120, 1.0900, 1.0850),
    ]
    signal = strategy.on_new_candle(history + breakout)
    assert signal.direction == Direction.CALL


def test_mixed_colors_do_not_trigger():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(BB_PERIOD)
    start_ts = len(history) * 60
    mixed = [
        make_candle(start_ts, 1.1000, 1.1050),
        make_candle(start_ts + 60, 1.1050, 1.1000),  # opposite color breaks the streak
        make_candle(start_ts + 120, 1.1000, 1.1150),
    ]
    signal = strategy.on_new_candle(history + mixed)
    assert signal.direction is None


def test_price_inside_band_does_not_trigger():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(BB_PERIOD)
    start_ts = len(history) * 60
    inside_band = [
        make_candle(start_ts, 1.1000, 1.1001),
        make_candle(start_ts + 60, 1.1001, 1.1002),
        make_candle(start_ts + 120, 1.1002, 1.1003),
    ]
    signal = strategy.on_new_candle(history + inside_band)
    assert signal.direction is None
    assert signal.reason == "Sin toque de techo/piso"


def test_doji_in_confirmation_window_skips_with_na():
    strategy = TechosPisosStrategy()
    history = flat_band_candles(BB_PERIOD)
    start_ts = len(history) * 60
    with_doji = [
        make_candle(start_ts, 1.1000, 1.1050),
        make_candle(start_ts + 60, 1.1050, 1.1050),  # doji
        make_candle(start_ts + 120, 1.1100, 1.1150),
    ]
    signal = strategy.on_new_candle(history + with_doji)
    assert signal.direction is None
    assert signal.reason == "N/A"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
