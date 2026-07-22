import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from byblue.core.models import Candle, Direction
from byblue.core.risk_manager import RiskConfig, RiskManager
from byblue.strategy.five_minute import FiveMinuteStrategy
from byblue.strategy.mhi import MHIStrategy


def make_candle(ts: int, open_: float, close: float) -> Candle:
    return Candle(asset="EURUSD", timestamp=ts, open=open_, close=close, high=max(open_, close), low=min(open_, close))


def test_majority_red_enters_call():
    strategy = FiveMinuteStrategy()
    history = [
        make_candle(0, 1.10, 1.11),
        make_candle(60, 1.11, 1.10),
        make_candle(120, 1.10, 1.09),  # red
        make_candle(180, 1.09, 1.08),  # red
        make_candle(240, 1.08, 1.085),  # green
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction == Direction.CALL


def test_majority_green_enters_put():
    strategy = FiveMinuteStrategy()
    history = [
        make_candle(0, 1.10, 1.11),
        make_candle(60, 1.11, 1.10),
        make_candle(120, 1.08, 1.09),  # green
        make_candle(180, 1.09, 1.10),  # green
        make_candle(240, 1.10, 1.095),  # red
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction == Direction.PUT


def test_doji_skips_with_na():
    strategy = FiveMinuteStrategy()
    history = [
        make_candle(0, 1.10, 1.11),
        make_candle(60, 1.11, 1.10),
        make_candle(120, 1.08, 1.09),
        make_candle(180, 1.09, 1.09),  # doji
        make_candle(240, 1.10, 1.095),
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "N/A"


def test_insufficient_history_skips():
    strategy = FiveMinuteStrategy()
    history = [make_candle(0, 1.10, 1.11)]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None


def test_unanimous_three_same_color_skips_with_na():
    strategy = FiveMinuteStrategy()
    history = [
        make_candle(0, 1.10, 1.11),
        make_candle(60, 1.11, 1.10),
        make_candle(120, 1.10, 1.09),  # red
        make_candle(180, 1.09, 1.08),  # red
        make_candle(240, 1.08, 1.07),  # red -> unanimous 3-0
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "N/A"


def test_martingala_progression_and_reset_on_win():
    rm = RiskManager(RiskConfig(base_stake=1.0, stop_win=100, stop_loss=100, mg_multiplier=2.0, mg_max_levels=2))
    assert rm.next_stake() == 1.0

    rm.register_result(Direction.CALL, profit=-1.0)  # loss -> level 1
    assert rm.mg_level == 1
    assert rm.next_stake() == 2.0

    rm.register_result(Direction.CALL, profit=-2.0)  # loss -> level 2
    assert rm.mg_level == 2
    assert rm.next_stake() == 4.0

    rm.register_result(Direction.CALL, profit=8.0)  # win -> reset
    assert rm.mg_level == 0
    assert rm.next_stake() == 1.0


def test_martingala_exhausts_levels_and_resets():
    rm = RiskManager(RiskConfig(base_stake=1.0, stop_win=100, stop_loss=100, mg_multiplier=2.0, mg_max_levels=1))
    rm.register_result(Direction.CALL, profit=-1.0)  # loss -> level 1
    assert rm.mg_level == 1
    rm.register_result(Direction.CALL, profit=-2.0)  # loss again, max reached -> reset
    assert rm.mg_level == 0


def test_stop_win_triggers():
    rm = RiskManager(RiskConfig(base_stake=1.0, stop_win=5.0, stop_loss=100, mg_max_levels=0))
    rm.register_result(Direction.CALL, profit=5.0)
    assert rm.should_stop() is True


def test_stop_loss_triggers():
    rm = RiskManager(RiskConfig(base_stake=1.0, stop_win=100, stop_loss=5.0, mg_max_levels=0))
    rm.register_result(Direction.CALL, profit=-5.0)
    assert rm.should_stop() is True


def test_martingala_pending_direction_forces_same_side_after_loss():
    """Mirrors the direction-selection logic in workers.py's trading loop:
    while in_martingala(), the next entry must reuse pending_direction
    (the losing trade's side) rather than a fresh strategy read."""
    rm = RiskManager(RiskConfig(base_stake=1.0, stop_win=100, stop_loss=100, mg_multiplier=2.0, mg_max_levels=2))

    fresh_signal_direction = Direction.CALL
    direction = rm.pending_direction if rm.in_martingala() else fresh_signal_direction
    assert direction == Direction.CALL
    rm.register_result(direction, profit=-1.0)

    # Even if the strategy now reads PUT on the next candle, martingala must
    # still repeat CALL (the losing direction) with the multiplied stake.
    fresh_signal_direction = Direction.PUT
    direction = rm.pending_direction if rm.in_martingala() else fresh_signal_direction
    assert direction == Direction.CALL
    assert rm.next_stake() == 2.0
    rm.register_result(direction, profit=4.0)  # win -> reset

    assert rm.in_martingala() is False
    assert rm.next_stake() == 1.0


def test_mhi_skips_outside_five_minute_mark():
    strategy = MHIStrategy()
    # next candle would start at ts+60=180, not a multiple of 300
    history = [
        make_candle(0, 1.10, 1.09),
        make_candle(60, 1.09, 1.08),
        make_candle(120, 1.08, 1.07),
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "Fuera de horario MHI"


def test_mhi_enters_call_on_majority_red_at_five_minute_mark():
    strategy = MHIStrategy()
    # last candle closes at ts=240 -> next candle starts at 300, a multiple of 300
    history = [
        make_candle(60, 1.10, 1.11),
        make_candle(120, 1.10, 1.09),  # red
        make_candle(180, 1.09, 1.08),  # red
        make_candle(240, 1.08, 1.085),  # green (2-1 majority, not unanimous)
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction == Direction.CALL


def test_mhi_enters_put_on_majority_green_at_five_minute_mark():
    strategy = MHIStrategy()
    history = [
        make_candle(60, 1.10, 1.09),
        make_candle(120, 1.08, 1.09),  # green
        make_candle(180, 1.09, 1.10),  # green
        make_candle(240, 1.10, 1.095),  # red (2-1 majority, not unanimous)
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction == Direction.PUT


def test_mhi_unanimous_three_same_color_skips_with_na():
    strategy = MHIStrategy()
    history = [
        make_candle(60, 1.10, 1.11),
        make_candle(120, 1.10, 1.09),  # red
        make_candle(180, 1.09, 1.08),  # red
        make_candle(240, 1.08, 1.075),  # red -> unanimous 3-0
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "N/A"


def test_mhi_doji_skips_with_na():
    strategy = MHIStrategy()
    history = [
        make_candle(60, 1.10, 1.09),
        make_candle(120, 1.08, 1.09),  # green
        make_candle(180, 1.09, 1.09),  # doji
        make_candle(240, 1.10, 1.11),  # green
    ]
    signal = strategy.on_new_candle(history)
    assert signal.direction is None
    assert signal.reason == "N/A"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
