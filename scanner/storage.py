import json, sqlite3, csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "scanner_history.sqlite3"

def save(results):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, scanned_at TEXT NOT NULL,
            symbol TEXT NOT NULL, market TEXT, signal TEXT, price REAL, payload TEXT NOT NULL)""")
        now = datetime.now(timezone.utc).isoformat()
        con.executemany("INSERT INTO scans(scanned_at,symbol,market,signal,price,payload) VALUES(?,?,?,?,?,?)",
            [(now, r.get("symbol",""), r.get("market",""), r.get("signal",""), r.get("price"), json.dumps(r, ensure_ascii=False)) for r in results])
        con.commit()

def export_csv(results, path):
    if not results:
        return
    fields = sorted({k for r in results for k in r})
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
