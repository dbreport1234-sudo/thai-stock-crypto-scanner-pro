import pandas as pd
import yfinance as yf
import os
import ccxt
import requests

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

# GitHub Actions runs on US servers, where api.binance.com answers HTTP 451.
# Binance's public market-data host is not geo-blocked, so it is tried first;
# other exchanges (via ccxt) are used as automatic fallbacks.
BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]
FALLBACK_EXCHANGES = [x.strip() for x in os.getenv("CRYPTO_FALLBACKS", "kucoin,okx,gateio,bitget,kraken").split(",") if x.strip()]
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}

def _binance_klines(symbol, timeframe, limit, start=None):
    pair = symbol.replace("/", "").upper()
    params = {"symbol": pair, "interval": timeframe, "limit": limit}
    if start:
        params["startTime"] = int(start)
    last = None
    for host in BINANCE_HOSTS:
        try:
            r = requests.get(host + "/api/v3/klines", params=params, timeout=20)
            if r.status_code == 200:
                return [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in r.json()]
            last = f"{host} HTTP {r.status_code}"
        except Exception as e:
            last = f"{host} {e}"
    raise RuntimeError(last)

def _ccxt_ohlcv(name, symbol, timeframe, limit, since=None):
    ex = getattr(ccxt, name)({"enableRateLimit": True, "timeout": 20000})
    return ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

def _ohlcv(symbol, timeframe, limit, since=None):
    errors = []
    try:
        rows = _binance_klines(symbol, timeframe, limit, since)
        if rows:
            return rows, "binance"
    except Exception as e:
        errors.append(f"binance: {e}")
    for name in FALLBACK_EXCHANGES:
        try:
            rows = _ccxt_ohlcv(name, symbol, timeframe, limit, since)
            if rows:
                return rows, name
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
    raise RuntimeError("All crypto sources failed for " + symbol + " | " + " | ".join(errors))

def _to_df(rows):
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.drop_duplicates("timestamp").set_index("timestamp")

def fetch_crypto(symbol: str, timeframe="15m", limit=500) -> pd.DataFrame:
    rows, _ = _ohlcv(symbol, timeframe, limit)
    return _to_df(rows)

def fetch_daily(symbol: str, market: str, period="2y") -> pd.DataFrame:
    if market == "thai":
        return fetch_thai(symbol, period=period, interval="1d")
    since = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp() * 1000)
    all_rows, src = [], None
    while len(all_rows) < 900:
        rows, src = _ohlcv(symbol, "1d", 1000, since)
        if not rows:
            break
        all_rows.extend(rows)
        nxt = rows[-1][0] + TF_MS["1d"]
        if nxt <= since or len(rows) < 2:
            break
        since = nxt
    if not all_rows:
        raise RuntimeError(f"No daily data for {symbol}")
    return _to_df(all_rows)[["open", "high", "low", "close", "volume"]]
