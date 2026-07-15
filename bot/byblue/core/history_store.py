"""Local-only SQLite trade history. Never synced to the backend."""
import os
import sqlite3
import sys
from pathlib import Path


def _schema_path() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller bundles `datas` under sys._MEIPASS
        return Path(sys._MEIPASS) / "byblue" / "db" / "schema.sql"
    return Path(__file__).resolve().parent.parent / "db" / "schema.sql"


SCHEMA_PATH = _schema_path()


def default_db_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    directory = Path(appdata) / "ByblueTrader"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "history.db"


class HistoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or default_db_path()
        # check_same_thread=False: the worker's HistoryStore is constructed on
        # the GUI thread (TradingWorker.__init__, before moveToThread) but all
        # reads/writes happen later on the dedicated worker QThread.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            self._conn.executescript(f.read())
        self._conn.commit()

    def add_trade(self, trade: dict) -> None:
        params = dict(trade)
        params.setdefault("strategy_name", params.pop("strategy", None))
        self._conn.execute(
            """INSERT INTO trades (timestamp, asset, direction, stake, result, payout, mode, strategy_name)
               VALUES (:timestamp, :asset, :direction, :stake, :result, :payout, :mode, :strategy_name)""",
            params,
        )
        self._conn.commit()

    def get_recent_trades(self, limit: int = 200) -> list[sqlite3.Row]:
        cursor = self._conn.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        )
        return list(reversed(cursor.fetchall()))

    def close(self) -> None:
        self._conn.close()
