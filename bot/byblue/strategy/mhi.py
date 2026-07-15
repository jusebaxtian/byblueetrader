"""Estrategia MHI (Maioria).

Velas de 1 minuto, expiracion siempre de 1 minuto. Solo dispara en los
minutos multiplos de 5 del reloj (ej. :00, :05, :10...): al cerrar la vela
justo anterior a esos minutos, evalua el color mayoritario de las ultimas
3 velas y entra en el color contrario. Fuera de esos minutos no opera.
"""
from byblue.core.models import Candle, Direction
from byblue.strategy.base import Signal, Strategy

EVALUATED_CANDLES = 3
FIVE_MIN_SECONDS = 300


class MHIStrategy(Strategy):
    name = "MHI"

    def on_new_candle(self, history: list[Candle]) -> Signal:
        if not history:
            return Signal(direction=None, reason="Esperando velas")

        latest = history[-1]
        next_candle_start = latest.timestamp + 60
        if next_candle_start % FIVE_MIN_SECONDS != 0:
            return Signal(direction=None, reason="Fuera de horario MHI")

        if len(history) < EVALUATED_CANDLES:
            return Signal(direction=None, reason="Esperando 3 velas")

        last_three = history[-EVALUATED_CANDLES:]
        if any(c.is_doji for c in last_three):
            return Signal(direction=None, reason="N/A")

        greens = sum(1 for c in last_three if c.is_green)
        reds = sum(1 for c in last_three if c.is_red)

        if reds > greens:
            return Signal(direction=Direction.CALL, reason="MHI: mayoria roja -> entra call")
        if greens > reds:
            return Signal(direction=Direction.PUT, reason="MHI: mayoria verde -> entra put")
        return Signal(direction=None, reason="N/A")
