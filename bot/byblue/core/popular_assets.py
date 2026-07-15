"""Curated list of popular assets, used instead of the live open-assets
query (`get_all_open_time`), which is known to hang on some accounts.

If the selected asset is closed when an order is placed, `iq_client` simply
raises IQClientError and the trading loop logs it and keeps running — no
need to pre-validate openness here.
"""
from byblue.core.models import OptionMode

POPULAR_BINARY_ASSETS = [
    "EURUSD",
    "EURUSD-OTC",
    "GBPUSD",
    "GBPUSD-OTC",
    "USDJPY",
    "USDJPY-OTC",
    "EURJPY",
    "EURJPY-OTC",
    "AUDUSD",
    "AUDUSD-OTC",
    "USDCAD",
    "USDCAD-OTC",
    "EURGBP",
    "EURGBP-OTC",
    "NZDUSD",
    "NZDUSD-OTC",
    "USDCHF",
    "USDCHF-OTC",
]

POPULAR_DIGITAL_ASSETS = [
    "EURUSD",
    "EURUSD-OTC",
    "GBPUSD",
    "GBPUSD-OTC",
    "USDJPY",
    "USDJPY-OTC",
    "AUDUSD",
    "AUDUSD-OTC",
    "USDCAD",
    "USDCAD-OTC",
    "BTCUSD",
    "ETHUSD",
]


def popular_assets_for(mode: OptionMode) -> list[str]:
    return POPULAR_DIGITAL_ASSETS if mode == OptionMode.DIGITAL else POPULAR_BINARY_ASSETS
