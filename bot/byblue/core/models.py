from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    CALL = "call"
    PUT = "put"


class OptionMode(str, Enum):
    BINARY = "binary"
    DIGITAL = "digital"


class BalanceMode(str, Enum):
    REAL = "REAL"
    PRACTICE = "PRACTICE"
    TOURNAMENT = "TOURNAMENT"


@dataclass(frozen=True)
class Candle:
    asset: str
    timestamp: int
    open: float
    close: float
    high: float
    low: float

    @property
    def is_doji(self) -> bool:
        return self.open == self.close

    @property
    def is_green(self) -> bool:
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open


@dataclass
class TradeResult:
    order_id: int
    asset: str
    direction: Direction
    stake: float
    mode: OptionMode
    result: str  # "win" | "loss" | "N/A"
    payout: float
    timestamp: int
    strategy_name: str
