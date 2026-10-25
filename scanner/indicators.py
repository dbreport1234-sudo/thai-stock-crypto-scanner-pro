import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns: open, high, low, close, volume; returns a copied frame."""
    out = df.copy().sort_index()
    for col in ("open", "high", "low", "close"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["volume"] = pd.to_numeric(out.get("volume", 0), errors="coerce").fillna(0)
    close = out["close"]
    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = (100 - (100 / (1 + rs))).fillna(50)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    prev_close = close.shift(1)
    tr = pd.concat([
        out["high"] - out["low"],
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    out["prior_high20"] = out["high"].shift(1).rolling(20).max()
    out["vol_avg20"] = out["volume"].shift(1).rolling(20).mean()
    return out.replace([np.inf, -np.inf], np.nan)
