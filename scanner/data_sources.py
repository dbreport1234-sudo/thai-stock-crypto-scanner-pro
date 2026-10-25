import pandas as pd
import yfinance as yf
import ccxt

def fetch_thai(symbol: str, period="60d", interval="15m") -> pd.DataFrame:
    raw = yf.download(symbol, period=period, interval=interval, auto_adjust=False,
                      progress=False, threads=False)
    if raw is None or raw.empty:
        raise RuntimeError(f"No Yahoo Finance data for {symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns={c: str(c).lower().replace(" ", "_") for c in raw.columns})
    needed = ["open", "high", "low", "close"]
    if not all(c in raw.columns for c in needed):
        raise RuntimeError(f"Unexpected columns for {symbol}: {list(raw.columns)}")
    if "volume" not in raw:
        raw["volume"] = 0
    return raw[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])

def fetch_crypto(symbol: str, timeframe="15m", limit=500) -> pd.DataFrame:
    exchange = ccxt.binance({"enableRateLimit": True, "timeout": 20000})
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not rows:
        raise RuntimeError(f"No Binance OHLCV data for {symbol}")
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.set_index("timestamp")

def fetch_daily(symbol: str, market: str, period="2y") -> pd.DataFrame:
    if market == "thai":
        return fetch_thai(symbol, period=period, interval="1d")
    # Daily crypto candles; 2 years are fetched in pages.
    exchange = ccxt.binance({"enableRateLimit": True})
    since = exchange.parse8601("2024-01-01T00:00:00Z")
    all_rows = []
    while True:
        rows = exchange.fetch_ohlcv(symbol, timeframe="1d", since=since, limit=1000)
        if not rows:
            break
        all_rows.extend(rows)
        next_since = rows[-1][0] + 86_400_000
        if next_since <= since or len(rows) < 2:
            break
        since = next_since
        if len(all_rows) >= 900:
            break
    if not all_rows:
        raise RuntimeError(f"No daily data for {symbol}")
    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates("timestamp").set_index("timestamp")
    return df[["open", "high", "low", "close", "volume"]]
