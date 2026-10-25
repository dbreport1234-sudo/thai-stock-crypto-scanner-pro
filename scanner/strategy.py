from datetime import datetime, timezone
import math
from .indicators import add_indicators

def analyze(symbol, name, market, df, settings):
    if df is None or len(df) < int(settings.get("min_history", 60)):
        return {"symbol": symbol, "name": name, "market": market, "signal": "INSUFFICIENT_DATA",
                "reason": "Not enough candles", "time": datetime.now(timezone.utc).isoformat()}
    x = add_indicators(df).dropna(subset=["close"])
    if len(x) < 55:
        return {"symbol": symbol, "name": name, "market": market, "signal": "INSUFFICIENT_DATA",
                "reason": "Not enough indicator history", "time": datetime.now(timezone.utc).isoformat()}
    # The last candle may still be forming on some providers; using it can create transient signals.
    row = x.iloc[-1]
    close = float(row["close"])
    rsi = float(row["rsi"])
    ema20, ema50 = float(row["ema20"]), float(row["ema50"])
    macd_hist = float(row["macd_hist"])
    prior_high = row["prior_high20"]
    vol, avgvol = float(row["volume"]), float(row["vol_avg20"]) if not math.isnan(float(row["vol_avg20"])) else 0.0
    volume_ok = avgvol <= 0 or vol >= avgvol
    breakout = not math.isnan(float(prior_high)) and close > float(prior_high)
    if ema20 > ema50 and 50 <= rsi <= 70 and macd_hist > 0 and breakout and volume_ok:
        signal = "BUY WATCH"
        reason = "EMA20>EMA50, RSI 50-70, MACD positive, 20-candle breakout, volume confirmed"
    elif ema20 < ema50 and rsi < 45 and macd_hist < 0:
        signal = "SELL / EXIT WATCH"
        reason = "EMA20<EMA50, RSI<45 and MACD negative"
    else:
        signal = "WAIT"
        reason = "Entry/exit conditions not fully met"
    atr = float(row["atr"]) if not math.isnan(float(row["atr"])) else 0.0
    stop_mult = float(settings.get("atr_stop_multiple", 1.5))
    risk = max(atr * stop_mult, close * 0.005)
    stop = close - risk
    t1 = close + risk * float(settings.get("target1_r_multiple", 1.5))
    t2 = close + risk * float(settings.get("target2_r_multiple", 2.5))
    idx = x.index[-1]
    stamp = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
    return {
        "symbol": symbol, "name": name, "market": market, "signal": signal, "reason": reason,
        "time": stamp, "price": round(close, 8), "rsi": round(rsi, 2),
        "ema20": round(ema20, 8), "ema50": round(ema50, 8),
        "macd_hist": round(macd_hist, 8), "atr": round(atr, 8),
        "stop_loss": round(stop, 8), "target1": round(t1, 8), "target2": round(t2, 8),
        "risk_reward_t1": float(settings.get("target1_r_multiple", 1.5)),
        "volume_confirmed": bool(volume_ok), "breakout": bool(breakout)
    }


def add_multi_timeframe_context(result, daily_df):
    """Attach daily/weekly/monthly trend context from daily candles."""
    import pandas as pd
    from .indicators import add_indicators
    if daily_df is None or daily_df.empty:
        result["timeframes"] = {"daily":{"trend":"NO_DATA"},"weekly":{"trend":"NO_DATA"},"monthly":{"trend":"NO_DATA"}}
        return result
    frame = daily_df.copy().sort_index()
    frame.index = pd.to_datetime(frame.index, utc=True, errors="coerce")
    frame = frame[~frame.index.isna()]
    contexts = {}
    for label, rule, min_bars in (("daily", "1D", 50), ("weekly", "W", 50), ("monthly", "ME", 20)):
        if label == "daily":
            candles = frame
        else:
            candles = frame.resample(rule).agg({
                "open":"first", "high":"max", "low":"min", "close":"last", "volume":"sum"
            }).dropna(subset=["close"])
        if len(candles) < min_bars:
            contexts[label] = {"trend":"INSUFFICIENT_HISTORY", "candles":int(len(candles))}
            continue
        ind = add_indicators(candles).dropna(subset=["close"])
        last = ind.iloc[-1]
        close = float(last["close"])
        e20 = float(last["ema20"])
        e50 = float(last["ema50"])
        if e20 > e50 and close > e20:
            trend = "BULLISH"
        elif e20 < e50 and close < e20:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        contexts[label] = {
            "trend":trend, "close":round(close,8),
            "ema20":round(e20,8), "ema50":round(e50,8),
            "candles":int(len(candles))
        }
    result["timeframes"] = contexts
    return result
