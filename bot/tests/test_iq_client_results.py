import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from byblue.core.iq_client import IQClient


class FakeApiBinary:
    def __init__(self, win_status, amount):
        self._win_status = win_status
        self._amount = amount

    def check_win_v4(self, order_id):
        return self._win_status, self._amount

    def check_connect(self):
        return True


class FakeApiDigital:
    def __init__(self, sequence):
        self._sequence = list(sequence)

    def check_win_digital_v2(self, order_id):
        return self._sequence.pop(0)

    def check_connect(self):
        return True


def make_client(fake_api) -> IQClient:
    client = IQClient()
    client._api = fake_api
    return client


def test_binary_win_maps_correctly():
    client = make_client(FakeApiBinary("win", 8.5))
    status, profit = client.check_binary_result(order_id=1)
    assert status == "win"
    assert profit == 8.5


def test_binary_loose_maps_to_loss():
    # iqoptionapi uses the literal string "loose" (not "loss") for a losing trade.
    client = make_client(FakeApiBinary("loose", -10.0))
    status, profit = client.check_binary_result(order_id=1)
    assert status == "loss"
    assert profit == -10.0


def test_binary_equal_maps_correctly():
    client = make_client(FakeApiBinary("equal", 0))
    status, profit = client.check_binary_result(order_id=1)
    assert status == "equal"


def test_digital_win_maps_from_bool_tuple():
    # check_win_digital_v2 returns (closed: bool, profit), not a status string.
    client = make_client(FakeApiDigital([(True, 4.25)]))
    status, profit = client.check_digital_result(order_id=1)
    assert status == "win"
    assert profit == 4.25


def test_digital_loss_maps_from_bool_tuple():
    client = make_client(FakeApiDigital([(True, -5.0)]))
    status, profit = client.check_digital_result(order_id=1)
    assert status == "loss"
    assert profit == -5.0


def test_digital_polls_until_closed():
    # First check comes back "not closed yet" (False, None); must keep polling.
    client = make_client(FakeApiDigital([(False, None), (False, None), (True, 3.0)]))
    status, profit = client.check_digital_result(order_id=1)
    assert status == "win"
    assert profit == 3.0


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
