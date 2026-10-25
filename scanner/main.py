import json, os, sys
from pathlib import Path
from datetime import datetime, timezone
from .data_sources import fetch_thai, fetch_crypto, fetch_daily
from .strategy import analyze, add_multi_timeframe_context
from .storage import save, export_csv

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "watchlist.json"
LATEST = ROOT / "docs" / "data" / "latest.json"

def main():
    if not CONFIG.exists():
        raise SystemExit(f"Missing {CONFIG}. Create config/watchlist.json from the provided sample.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    settings = cfg.get("settings", {})
    results, errors = [], []
    for item in cfg.get("thai_stocks", []):
        symbol, name = item["symbol"], item.get("name", item["symbol"])
        try:
            df = fetch_thai(symbol, settings.get("history_period","60d"), settings.get("interval","15m"))
            item_result = analyze(symbol, name, "thai", df, settings)
            try:
                daily = fetch_daily(symbol, "thai", period="5y")
                item_result = add_multi_timeframe_context(item_result, daily)
            except Exception as context_exc:
                item_result["timeframes"] = {"daily":{"trend":"NO_DATA"}, "weekly":{"trend":"NO_DATA"}, "monthly":{"trend":"NO_DATA"}}
                print(f"[WARN] {symbol} timeframe context: {context_exc}", file=sys.stderr)
            results.append(item_result)
        except Exception as exc:
            errors.append({"symbol":symbol,"market":"thai","error":str(exc)})
            print(f"[ERROR] {symbol}: {exc}", file=sys.stderr)
    for item in cfg.get("crypto", []):
        symbol, name = item["symbol"], item.get("name", item["symbol"])
        try:
            df = fetch_crypto(symbol, settings.get("interval","15m"), 500)
            item_result = analyze(symbol, name, "crypto", df, settings)
            try:
                daily = fetch_daily(symbol, "crypto", period="5y")
                item_result = add_multi_timeframe_context(item_result, daily)
            except Exception as context_exc:
                item_result["timeframes"] = {"daily":{"trend":"NO_DATA"}, "weekly":{"trend":"NO_DATA"}, "monthly":{"trend":"NO_DATA"}}
                print(f"[WARN] {symbol} timeframe context: {context_exc}", file=sys.stderr)
            results.append(item_result)
        except Exception as exc:
            errors.append({"symbol":symbol,"market":"crypto","error":str(exc)})
            print(f"[ERROR] {symbol}: {exc}", file=sys.stderr)
    payload = {
        "app":"Thai Stock & Crypto Scanner Pro",
        "scanned_at":datetime.now(timezone.utc).isoformat(),
        "mode":"signal-only",
        "results":results,
        "errors":errors,
        "summary":{
            "total":len(results),
            "buy_watch":sum(r.get("signal")=="BUY WATCH" for r in results),
            "sell_watch":sum(r.get("signal")=="SELL / EXIT WATCH" for r in results),
            "wait":sum(r.get("signal")=="WAIT" for r in results),
            "errors":len(errors)
        },
        "disclaimer":"Signals are informational, may be delayed or wrong, and do not guarantee profit."
    }
    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save(results)
    export_csv(results, ROOT / "latest_scan.csv")
    from .discord_alerts import send_alerts
    send_alerts(results)
    print(json.dumps(payload["summary"], ensure_ascii=False))
    # Avoid failing the whole run if one data source is temporarily down.
    if not results:
        raise SystemExit("No symbols returned data; inspect provider access/configuration.")

if __name__ == "__main__":
    main()
