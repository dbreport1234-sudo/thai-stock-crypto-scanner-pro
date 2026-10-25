# Thai Stock & Crypto Scanner Pro

A signal-only market scanner for Thai equities and crypto. It scans a configurable watchlist, calculates trend/momentum/breakout signals, stores results in JSON/CSV/SQLite, sends Discord webhook alerts, and serves a static dashboard through GitHub Pages.

> This is research software, not investment advice. Signals are not guaranteed to be profitable. Market data can be delayed, incomplete, adjusted, or unavailable. Test with paper trading and account for fees, slippage, liquidity, and taxes before risking money. This app does not place orders.

## Features
- Thai shares through Yahoo Finance symbols such as `PTT.BK`, `AOT.BK`, `ADVANC.BK`.
- Crypto OHLCV from Binance public market data via `ccxt` (no API key needed for public data).
- 15-minute scan workflow via GitHub Actions (GitHub scheduled jobs can start late; not tick-level real time).
- EMA trend, RSI, MACD histogram, volume confirmation and breakout checks; daily/weekly/monthly trend context.
- Risk levels using ATR; signals include entry, stop, target 1/2 and risk/reward.
- Discord embeds through `DISCORD_WEBHOOK_URL` GitHub Secret.
- Dashboard hosted on GitHub Pages; scan snapshots stored in `docs/data/latest.json`.
- SQLite local history, CSV export, and a simple backtest command.

## Repository layout
```text
thai-stock-crypto-scanner-pro/
├── .github/workflows/scan.yml
├── config/
│   └── watchlist.json
├── docs/
│   ├── index.html
│   └── data/latest.json
├── scanner/
│   ├── __init__.py
│   ├── data_sources.py
│   ├── indicators.py
│   ├── strategy.py
│   ├── storage.py
│   ├── discord_alerts.py
│   └── main.py
├── tests/test_indicators.py
├── backtest.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 1. Run locally (Windows PowerShell)
Install Python 3.11 or 3.12, then:
```powershell
cd thai-stock-crypto-scanner-pro
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item config\watchlist.example.json config\watchlist.json
```
If `watchlist.json` already exists in the project, skip the copy command. Set Discord webhook only for the current PowerShell session:
```powershell
$env:DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"
python -m scanner.main
python backtest.py --symbol PTT.BK --market thai --period 2y
```
Do not commit webhook URLs, API tokens, or broker credentials.

## 2. Configure watchlist
Edit `config/watchlist.json`. Thai shares use Yahoo Finance suffix `.BK`; crypto symbols use CCXT format such as `BTC/USDT`. Data availability and interval support varies by provider. Start with a small watchlist, then expand.

## 3. GitHub Actions + Pages setup
1. Create a GitHub repository and upload these files.
2. In **Settings → Secrets and variables → Actions → New repository secret**, add `DISCORD_WEBHOOK_URL` (the Discord channel webhook URL). Leave it unset if alerts are not needed.
3. In **Settings → Pages**, set deployment source to **Deploy from a branch**, choose `main` and `/docs` if available in your repository settings. The workflow writes `docs/data/latest.json` back to `main`; Pages serves `docs/index.html`.
4. In **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions** so the workflow can update `docs/data/latest.json`.
5. Enable Actions and run **Actions → Thai Stock & Crypto Scanner → Run workflow** once manually.
6. Open the Pages URL shown under Settings → Pages.

The workflow runs every 15 minutes (`*/15 * * * *`). GitHub may delay scheduled workflows, especially during busy periods. This is not a guaranteed exact 15-minute scheduler. A public repository is generally the easiest way to use scheduled Actions; GitHub plan and repository rules can affect availability.

## 4. Signal rules
A signal is generated when the latest completed candle passes all checks:
- `BUY WATCH`: EMA20 above EMA50, RSI between 50 and 70, MACD histogram positive, close above the previous 20-candle high, and volume above its 20-candle average (volume check is skipped if the source has no usable volume).
- `SELL / EXIT WATCH`: EMA20 below EMA50, RSI below 45, and MACD histogram negative.
- Otherwise `WAIT`.
- ATR-based stop and targets are indicative levels, not execution instructions. A signal is informational and can be stale by the time it is read.

The 15-minute signal is the entry-watch timeframe. The dashboard JSON also includes daily, weekly and monthly EMA trend context. If history is too short for a timeframe, it is explicitly marked `INSUFFICIENT_HISTORY` rather than guessing.

## 5. Backtest
```powershell
python backtest.py --symbol PTT.BK --market thai --period 2y
python backtest.py --symbol BTC/USDT --market crypto --period 2y
```
The included backtest uses daily candles and a simple next-candle entry/exit simulation with a stop and target. It is educational and simplified: it does not model order-book liquidity, taxes, funding, corporate actions perfectly, or exchange execution. Inspect trade count and drawdown; do not optimize only for win rate.

## 6. Security and limitations
- Do not store Discord webhook URLs in files or commit them.
- No exchange keys and no broker API keys are needed or used.
- The scanner does not submit orders.
- Yahoo Finance may rate-limit or change access; Binance public data may be unavailable in some regions.
- GitHub Actions and GitHub Pages are not a continuously running server. Dashboard refreshes when the latest JSON is committed/deployed.
- Start with a small watchlist. Respect each data provider's terms and use licensed market data for production.
