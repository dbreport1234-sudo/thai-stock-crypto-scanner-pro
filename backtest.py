import argparse
import pandas as pd
from scanner.data_sources import fetch_daily
from scanner.indicators import add_indicators

def run_backtest(df, initial_cash=100000.0, fee_rate=0.001):
    x = add_indicators(df).dropna(subset=["close"]).copy()
    cash, units, entry, stop, target = initial_cash, 0.0, 0.0, 0.0, 0.0
    equity_curve, trades = [], []
    for i in range(55, len(x)-1):
        row = x.iloc[i]
        next_open = float(x.iloc[i+1]["open"])
        close = float(row["close"])
        # Conservative intraday check: stop is checked before target if both hit in one candle.
        if units > 0:
            low, high = float(row["low"]), float(row["high"])
            exit_price, why = None, None
            if low <= stop:
                exit_price, why = stop, "STOP"
            elif high >= target:
                exit_price, why = target, "TARGET"
            elif float(row["ema20"]) < float(row["ema50"]) and float(row["macd_hist"]) < 0:
                exit_price, why = next_open, "TREND_EXIT"
            if exit_price is not None:
                proceeds = units * exit_price * (1-fee_rate)
                pnl = proceeds - units * entry
                cash += proceeds
                trades.append({"entry":entry,"exit":exit_price,"pnl":pnl,"reason":why})
                units = 0.0
        if units == 0 and float(row["ema20"]) > float(row["ema50"]) and 50 <= float(row["rsi"]) <= 70 and float(row["macd_hist"]) > 0:
            risk = max(float(row["atr"])*1.5, close*0.005)
            buy_price = next_open
            budget = cash * 0.95
            units = budget / (buy_price * (1+fee_rate))
            if units > 0:
                cash -= units * buy_price * (1+fee_rate)
                entry, stop, target = buy_price, buy_price-risk, buy_price+1.5*risk
        equity_curve.append(cash + units * close)
    final_equity = equity_curve[-1] if equity_curve else initial_cash
    peak, max_dd = initial_cash, 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak:
            max_dd = min(max_dd, (value-peak)/peak)
    wins = sum(t["pnl"] > 0 for t in trades)
    print(f"Initial equity: {initial_cash:,.2f}")
    print(f"Final marked equity: {final_equity:,.2f}")
    print(f"Net return: {(final_equity/initial_cash-1)*100:.2f}%")
    print(f"Closed trades: {len(trades)}")
    print(f"Win rate: {(wins/len(trades)*100 if trades else 0):.2f}%")
    print(f"Max drawdown (sampled): {max_dd*100:.2f}%")
    print("Note: simplified daily-candle backtest; fees/slippage and data limitations mean this is not a forecast.")
    return trades

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",required=True)
    p.add_argument("--market",choices=["thai","crypto"],required=True)
    p.add_argument("--period",default="2y")
    p.add_argument("--cash",type=float,default=100000)
    p.add_argument("--fee",type=float,default=0.001)
    a=p.parse_args()
    df=fetch_daily(a.symbol,a.market,a.period)
    if len(df)<100: raise SystemExit(f"Only {len(df)} candles available; need more data.")
    run_backtest(df,a.cash,a.fee)
if __name__=="__main__": main()
