CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    asset TEXT NOT NULL,
    direction TEXT NOT NULL,
    stake REAL NOT NULL,
    result TEXT NOT NULL,
    payout REAL NOT NULL,
    mode TEXT NOT NULL,
    strategy_name TEXT NOT NULL
);
