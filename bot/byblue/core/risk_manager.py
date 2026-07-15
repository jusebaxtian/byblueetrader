"""Session risk management: Stop Win / Stop Loss + Martingala state machine.

Martingala rule (per user spec): on loss, repeat the SAME direction with the
stake multiplied, up to `mg_max_levels`. On a win, or after exhausting the
max levels, reset back to the base stake and level 0.
"""
from dataclasses import dataclass, field

from byblue.core.models import Direction


@dataclass
class RiskConfig:
    base_stake: float
    stop_win: float
    stop_loss: float
    mg_multiplier: float = 2.0
    mg_max_levels: int = 0  # 0 = Martingala disabled


@dataclass
class RiskManager:
    config: RiskConfig
    session_pnl: float = 0.0
    mg_level: int = 0
    pending_direction: Direction | None = field(default=None)

    def should_stop(self) -> bool:
        if self.session_pnl >= self.config.stop_win:
            return True
        if self.session_pnl <= -abs(self.config.stop_loss):
            return True
        return False

    def next_stake(self) -> float:
        if self.mg_level == 0:
            return self.config.base_stake
        return round(self.config.base_stake * (self.config.mg_multiplier ** self.mg_level), 2)

    def register_signal(self, direction: Direction) -> None:
        """Called when a fresh (non-martingala) signal is taken."""
        if self.mg_level == 0:
            self.pending_direction = direction

    def register_result(self, direction: Direction, profit: float) -> None:
        """profit: positive on win, negative (stake lost) on loss, 0 on N/A/equal."""
        self.session_pnl += profit

        if profit > 0:
            self._reset_martingala()
            return
        if profit == 0:
            return

        # loss
        if self.config.mg_max_levels <= 0:
            self._reset_martingala()
            return

        if self.mg_level < self.config.mg_max_levels:
            self.mg_level += 1
            self.pending_direction = direction
        else:
            self._reset_martingala()

    def _reset_martingala(self) -> None:
        self.mg_level = 0
        self.pending_direction = None

    def in_martingala(self) -> bool:
        return self.mg_level > 0
