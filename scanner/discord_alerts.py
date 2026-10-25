import os, requests

def send_alerts(results):
    url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("DISCORD_WEBHOOK_URL not set; skipping Discord notifications.")
        return
    selected = [r for r in results if r.get("signal") in ("BUY WATCH", "SELL / EXIT WATCH")]
    if not selected:
        print("No actionable watch signals; no Discord message sent.")
        return
    # Discord allows at most 10 embeds per message.
    for start in range(0, len(selected), 10):
        embeds = []
        for r in selected[start:start+10]:
            color = 0x2ECC71 if r["signal"] == "BUY WATCH" else 0xE74C3C
            def fmt(k):
                v = r.get(k)
                return "n/a" if v is None else str(v)
            embeds.append({
                "title": f'{r.get("signal")} · {r.get("symbol")}',
                "description": r.get("reason", ""),
                "color": color,
                "fields": [
                    {"name":"Market","value":str(r.get("market","")),"inline":True},
                    {"name":"Price","value":fmt("price"),"inline":True},
                    {"name":"RSI","value":fmt("rsi"),"inline":True},
                    {"name":"Stop loss (indicative)","value":fmt("stop_loss"),"inline":True},
                    {"name":"Target 1","value":fmt("target1"),"inline":True},
                    {"name":"Target 2","value":fmt("target2"),"inline":True}
                ],
                "footer":{"text":"Thai Stock & Crypto Scanner Pro · Signal only, not financial advice"},
                "timestamp": r.get("time") if str(r.get("time","")).endswith("+00:00") else None
            })
        response = requests.post(url, json={"username":"Thai Market Scanner","embeds":embeds}, timeout=15)
        response.raise_for_status()
