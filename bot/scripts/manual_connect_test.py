"""Manual smoke test for Fase 1: login, switch to demo, place one trade, verify result.

Run: python -m scripts.manual_connect_test
Requires IQ_EMAIL / IQ_PASSWORD env vars, and an asset that is currently open.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from byblue.core.iq_client import IQClient
from byblue.core.models import BalanceMode, Direction, OptionMode

logging.basicConfig(level=logging.INFO)


def main() -> None:
    email = os.environ["IQ_EMAIL"]
    password = os.environ["IQ_PASSWORD"]

    client = IQClient()
    client.login(email, password)
    client.change_balance(BalanceMode.PRACTICE)
    print("Balance (demo):", client.get_balance())

    open_assets = client.get_open_assets()
    print("Open binary assets:", open_assets["binary"][:5])
    print("Open digital assets:", open_assets["digital"][:5])

    if not open_assets["binary"]:
        print("No open binary assets right now, skipping trade test.")
        return

    asset = open_assets["binary"][0]
    order_id = client.place_order(OptionMode.BINARY, asset, 1.0, Direction.CALL, 1)
    print(f"Placed order {order_id} on {asset}, waiting for result...")
    result, payout = client.check_result(OptionMode.BINARY, order_id)
    print("Result:", result, "Payout:", payout)


if __name__ == "__main__":
    main()
