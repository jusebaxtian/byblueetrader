"""Estrategia a 5 minutos.

Velas de 1 minuto, expiracion siempre de 1 minuto. En cada cierre de vela
se toma el cuadrante de las ultimas 5 velas cerradas, pero solo se evalua
el color mayoritario de las ultimas 3 de ese cuadrante. Si la mayoria es
roja se entra en verde (call); si la mayoria es verde se entra en rojo
(put). Solo se opera con mayoria 2-1: si las 3 son del mismo color (3-0,
unanime) o si alguna es doji, se omite la entrada ese minuto (N/A).
"""
from byblue.core.models import Candle, Direction
from byblue.strategy.base import Signal, Strategy

WINDOW_SIZE = 5
EVALUATED_CANDLES = 3


class FiveMinuteStrategy(Strategy):
    name = "Estrategia a 5 minutos"

    def on_new_candle(self, history: list[Candle]) -> Signal:
        if len(history) < WINDOW_SIZE:
            return Signal(direction=None, reason="Esperando cuadrante de 5 velas")

        window = history[-WINDOW_SIZE:]
        last_three = window[-EVALUATED_CANDLES:]

        if any(c.is_doji for c in last_three):
            return Signal(direction=None, reason="N/A")

        greens = sum(1 for c in last_three if c.is_green)
        reds = sum(1 for c in last_three if c.is_red)

        if reds == 3 or greens == 3:
            return Signal(direction=None, reason="N/A")
        if reds > greens:
            return Signal(direction=Direction.CALL, reason="Mayoria roja -> entra call")
        if greens > reds:
            return Signal(direction=Direction.PUT, reason="Mayoria verde -> entra put")
        return Signal(direction=None, reason="N/A")
