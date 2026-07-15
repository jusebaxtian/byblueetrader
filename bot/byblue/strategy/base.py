from abc import ABC, abstractmethod
from dataclasses import dataclass

from byblue.core.models import Candle, Direction


@dataclass
class Signal:
    direction: Direction | None  # None means "skip this tick"
    reason: str


class Strategy(ABC):
    name: str

    @abstractmethod
    def on_new_candle(self, history: list[Candle]) -> Signal:
        """Called each time a new 1-minute candle closes for the selected asset.

        `history` is the list of closed candles available so far, oldest first.
        Must return a Signal; direction=None means no trade this tick.
        """
        raise NotImplementedError
