"""Estrategia Accion del Precio: Techos y Pisos.

Velas de 1 minuto, expiracion siempre de 1 minuto. Usa Bandas de Bollinger
(SMA 20 + 2 desviaciones estandar) calculadas sobre las velas previas como
el "techo" (banda superior) y el "piso" (banda inferior) del precio.

Regla: si las ultimas 3 velas cerradas son del MISMO color y las 3 cierran
por FUERA de la banda (tocando techo o piso repetidamente), se entra en
CONTRA de esa tendencia esperando el rebote:
  - 3 velas verdes cerrando por encima del techo -> entra put (reversion abajo)
  - 3 velas rojas cerrando por debajo del piso -> entra call (reversion arriba)

A mas velas de confirmacion, menor riesgo (aqui se usan 3, el ajuste mas
sensible/rapido de la estrategia clasica).
"""
import statistics

from byblue.core.models import Candle, Direction
from byblue.strategy.base import Signal, Strategy

BB_PERIOD = 20
CONFIRM_CANDLES = 3
BB_STD_MULTIPLIER = 2


class TechosPisosStrategy(Strategy):
    name = "Accion del Precio (Techos y Pisos)"

    def on_new_candle(self, history: list[Candle]) -> Signal:
        needed = BB_PERIOD + CONFIRM_CANDLES
        if len(history) < needed:
            return Signal(direction=None, reason="Esperando datos suficientes")

        band_candles = history[-needed:-CONFIRM_CANDLES]
        confirm_candles = history[-CONFIRM_CANDLES:]

        if any(c.is_doji for c in confirm_candles):
            return Signal(direction=None, reason="N/A")

        closes = [c.close for c in band_candles]
        mean = statistics.fmean(closes)
        std_dev = statistics.pstdev(closes)
        techo = mean + BB_STD_MULTIPLIER * std_dev
        piso = mean - BB_STD_MULTIPLIER * std_dev

        all_green = all(c.is_green for c in confirm_candles)
        all_red = all(c.is_red for c in confirm_candles)

        if all_green and all(c.close > techo for c in confirm_candles):
            return Signal(direction=Direction.PUT, reason="Techo: 3 velas verdes fuera de banda -> entra put")

        if all_red and all(c.close < piso for c in confirm_candles):
            return Signal(direction=Direction.CALL, reason="Piso: 3 velas rojas fuera de banda -> entra call")

        return Signal(direction=None, reason="Sin toque de techo/piso")
