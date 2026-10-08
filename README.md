# PKC Sector Radar

A free, ScreeningMantis-style dashboard for NSE stocks:

- **Rotation** – theme / sector / NSE-index returns for Today, 1W, 1M, 3M, 6M, YTD, 1Y, with mean or median, rank change vs last week, and a click-through list of the stocks in each group.
- **Breadth** – % of stocks above 20/50/200 DMA, advance/decline, 52-week highs/lows, 4% movers, one year of history.
- **RS ranking** – every stock ranked 1–99 by relative strength, filterable by sector, theme, Stage 2, Minervini trend template.
- **Scanners** – 59 scans in 9 groups (`scripts/scanners.py`), led by a **Confluence** list (stocks firing in 4+ of the 7 bullish groups). Momentum (4% day, burst, gap-up, RS jump, power trend, ants, high-octane, 3/6/12-month swing leaders, episodic pivot, buyable gap-up), breakouts (52-week / 2-year / all-time highs, strong-close highs, Darvas, Bollinger, Stage 2, VCP, 3 weeks tight, launch pad, IPO high), volume, trend & pullbacks (incl. power of 3, wedge pop), price action (outside day, open = low, hammer at 50 DMA, double inside day, bull snort), oscillators, RS-line new highs (1/3/6/12 months) and weakness (incl. leader down on volume). Any scan can be limited to the top 5 or 10 themes.
- **Watchlists** – multiple lists, return since added, pivot/stop/target with buy-zone alerts, notes, flags, track record, import/export, phone ↔ PC sync.
- **VPCI Screener** – your Streamlit screener (`vpci/` folder, files unchanged) run every evening: Fresh Signals, Buyable, Watchlist, All Results, Ranked, G4 Pending, New Listings, Sector Leadership, Sector Rotation — for both completed weeks and the running week.

**No broker login, no API key, no password.** Prices come from Upstox's public historical-candle service, which answers without an account. Today's candle is added from NSE's official bhavcopy. Yahoo Finance is wired in as a backup.

```
GitHub Actions (6:40 PM IST, Mon–Fri, free)
   ├─ update_reference.py   sector + NSE index lists      (niftyindices.com)
   ├─ fetch_prices.py       2 years of daily candles       (Upstox → NSE bhavcopy for today; Yahoo backup)
   ├─ compute.py            returns, RS, breadth, scans    → docs/data/*.json
   ├─ fetch_fundamentals.py new NSE results + shareholding (config/fund_*.csv)
   └─ publish docs/ to Pages → website updates itself
```

Cost: ₹0. Setup: about 20 minutes, once.

---

## Step 1 — Try it on your PC (optional, 10 minutes)

1. Install Python 3.12 from python.org (tick "Add Python to PATH").
2. Unzip this folder, e.g. to `D:\sector-radar`.
3. Double-click `run_local.bat`. It downloads all ~2,900 NSE stocks (about 6 minutes), computes everything and opens the site at http://localhost:8000.

Quick 20-stock test instead: open Command Prompt in the folder and run
```
pip install -r requirements.txt
python scripts\fetch_prices.py --limit 20
```

## Step 2 — Put it on GitHub

1. Create a free account at github.com.
2. Click **New repository** → name it `sector-radar` → choose **Private** or **Public** (see Step 3) → Create.
3. On the empty repo page click **uploading an existing file** and drag in everything from the folder. Make sure the `.github` folder goes in too (on Windows, turn on "show hidden items" if you can't see it). Commit.
4. Go to **Actions** → enable workflows if asked → **Daily update** → **Run workflow**. It takes about 10 minutes. A green tick means `docs/data` now holds fresh data.

From now on it runs by itself at 6:40 PM IST every weekday. There are no secrets to add. A private repo gets 2,000 free Action minutes a month; this uses about 250.

## Step 3 — Host the website (free)

There is nothing secret in the repo, so pick based on who may see the dashboard:

**Public, simplest (2 minutes).** Make the repo public → **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder `/docs` → Save. Your site is at `https://<your-username>.github.io/sector-radar/`. Anyone with the link can view it.

**Private, only you.** GitHub Pages needs a paid plan for private repos, so use Cloudflare Pages:
1. Free account at dash.cloudflare.com.
2. **Workers & Pages → Create → Pages → Connect to Git** → pick `sector-radar`.
3. Framework preset: **None**. Build command: empty. Build output directory: `docs`. Deploy.
4. You get a link like `sector-radar-xyz.pages.dev`. Each evening's data commit redeploys it.
5. Lock it to you: **Zero Trust → Access → Applications → Add → Self-hosted**, enter the pages.dev address, allow only your email.

## Step 4 — Edit themes

Themes live in `config/themes.csv`: one theme per row, NSE symbols separated by spaces.

```
Theme,Symbols
Wires & Cables,POLYCAB KEI FINCABLES RRKABEL HAVELLS ...
```

Edit it on GitHub (open the file → pencil icon → commit). A theme appears once 3 of its stocks pass the filters. The next daily run picks up changes; to see them immediately, run the workflow by hand.

**Sector** comes from NSE's classification of the ~750 Nifty Total Market stocks. **NSE Index** groups are equal-weighted members of 39 sectoral and thematic indices. Both refresh automatically.

## Optional — Industry for every stock and the ₹500 Cr filter

BSE blocks cloud servers, but its public company list works from a home connection and has every company's industry and market cap:

```
python scripts\pc_bse_industry.py
```

Upload the `config/industry_bse.csv` it writes to `config/` on GitHub. From the next run you get an **Industry** tab covering all stocks, and stocks below ₹500 Cr are dropped. Re-run monthly.

Without it, the universe is filtered by liquidity: price ≥ ₹20 and median daily turnover ≥ ₹1 Cr over 50 days (about 1,550 stocks).

## Watchlists

Tap **☆** next to any stock name (Rotation, RS ranking, Scanners, VPCI, stock card) to put it in one or more lists. The **Watchlists** tab then shows, per list:

- **Since added** — price and NIFTY 500 level are recorded on the day you add a stock: return since added, return vs NIFTY, days on the list, best gain and worst dip since added, 3-month sparkline. The added date/price can be edited (change the date and the price fills in from that day's close).
- **Your levels** — pivot (buy-above), stop, target, flag colour and a note. Setup column: below pivot / near pivot / **buy zone** (pivot to +5%, IBD) / extended / below stop / target hit. Risk %, reward/risk and a position-size calculator from your risk per trade.
- **Needs your attention today** — stop hit, breakout above your pivot, buy zone, near pivot or stop, target reached, warnings (4% breakdown, lost 50 DMA, RS falling below 70, red flags), new hits in key scans, results due within 7 days, fresh VPCI signals. The tab shows a count of urgent items.
- Columns: Tracking / Performance / Fundamentals; sort and CSV like every table.
- **Track record** — removed stocks are logged with their return and return vs NIFTY, giving your hit rate.
- Import (paste symbols, TradingView `.txt`, Kite lists), export to TradingView, backup file, share link, and **☆ Add all** on every scanner.

Watchlists are saved in your browser. **Sync devices** keeps phone and PC identical through a secret GitHub gist: create a token with only the `gist` permission (the button links to the right GitHub page), paste it once on each device. The first connect on a device that already has lists merges both.

`compute.py` also writes `docs/data/closes.json` (one year of daily closes, ~0.8 MB compressed) for the sparklines, back-dated adds and the 12-month chart in every stock card.

## Fundamentals (automatic, from NSE filings)

`scripts/fetch_fundamentals.py` reads the companies' own quarterly filings on NSE every evening — no login, no uploads:

- **Quarterly results** (about 10 quarters per stock): revenue, every expense line, profit before tax, net profit attributable to shareholders, EPS; balance sheet and cash flow from the half-year (Sep) and year-end (Mar) filings.
- **Shareholding pattern** (latest 5+ quarters): promoter, FII, DII, mutual funds, retail, number of shareholders.
- **Results calendar** (board meetings for the next 60 days) and **industry** (Yahoo Finance classification).

The first run downloads everything (~35,000 small files, about 45 min); after that each run fetches only filings published since the previous one, usually a few minutes. Data is kept in `config/fund_results.csv`, `config/fund_holdings.csv` and `config/fund_info.csv`.

`scripts/fundamentals.py` turns this into: profit and revenue growth (YoY, QoQ, trailing four quarters), three-quarter earnings acceleration, operating margin and its change, P/E, P/S and PEG on today's market cap, ROE, ROCE, debt/equity, free cash flow, CWIP share of assets, and shareholding changes over 1 quarter and 1 year. A **Fund rating 1–99** (70% growth, 30% quality, percentile across the universe; loss-makers capped low) sits next to the RS rating, and every scanner can be limited to Fund 60+ or 80+.

Fundamental scanners: growth leaders 25/25, earnings acceleration, CANSLIM-style, SEPA, margin expansion, revenue streak, turnaround, post-results breakout, results in the next 7 days, quality compounders, GARP, capex cycle, net-cash small caps, smart-money accumulation, mutual funds moving in, promoter buying, under-followed leaders, and fundamental red flags.

Banks and lenders skip margin, ROCE, debt and cash-flow tests. Growth is only computed from a profitable base.

## VPCI Screener

`vpci/` holds your screener exactly as in the `rojiroti` repo (`app.py`, `vpci_engine.py`, `data_sources.py`, `signal_history.py`, `sector_history.py`, `Stock_List.csv`). `scripts/vpci_app_run.py` does what clicking **Run Market Scan** does, with the app's defaults (Upstox → Yahoo, relaxed off, 12 workers), twice: once with "Screen the RUNNING week" off and once on (volume pro-rated). It reads its functions straight from `vpci/app.py`, so when you change the screener, copy the new files into `vpci/` and the website follows.

Checked against the real app: running `app.py` through Streamlit's test harness on 140 stocks gave identical values in every column, the same statuses and the same market caps.

Kite isn't used here (it needs a fresh token every day). Sector-rotation history is saved as one snapshot per week in `docs/data/vpci/history/`.

## Settings

`config/settings.json`:

| Setting | Default | Meaning |
|---|---|---|
| `min_price` | 20 | Ignore stocks below this price |
| `min_median_turnover_cr` | 1.0 | Median 50-day traded value, ₹ crore |
| `min_market_cap_cr` | 500 | Used only if `industry_bse.csv` or `mcap.csv` exists |
| `min_group_size` | 3 | Smallest group shown on the Rotation tab |
| `include_series` | EQ, BE | NSE series included |
| `upstox_requests_per_second` | 10 | Download speed; lower it if you ever see refusals |

## How the numbers are calculated

- **Prices** are adjusted for splits and bonuses (checked: HDFC Bank's 1:1 bonus and Bajaj Finance's split show no jumps). Upstox closes and volumes matched NSE's bhavcopy exactly for all 2,912 stocks tested.
- **Group return** = equal-weighted mean (or median) of member stocks' returns. Rank arrows compare with the same calculation 5 sessions ago.
- **RS rating** = percentile (1–99) of 0.4 × 3-month + 0.2 × 6-month + 0.2 × 9-month + 0.2 × 12-month performance.
- **Stage** = price vs the 150-day SMA (30-week) and its 20-day slope: above and rising = Stage 2, below and falling = Stage 4.
- **Trend template** = Minervini's 8 conditions with RS ≥ 70.
- **Darvas breakout** = prior 20-session range ≤ 15%, close above its high, volume ≥ 1.5× the 50-day average.
- **Breadth** uses today's universe for the whole history.

## Troubleshooting

| Problem | Fix |
|---|---|
| Actions run is red | Open it and read the step that failed. If Upstox failed, the Yahoo step should have run instead. |
| Site says "Data files could not be loaded" | The workflow hasn't succeeded yet — check the Actions tab. |
| Today's candle missing | NSE publishes the bhavcopy around 6 PM; on rare late days the run uses Upstox's own end-of-day candle. Run the workflow again later if needed. |
| Want data now | Actions → Daily update → Run workflow (choose `yahoo` if Upstox is down). |
| Workflow stopped running | GitHub pauses schedules after 60 days without repo activity on public repos. The daily data commit counts as activity, so this only happens if runs keep failing. |

## A note on the data source

Upstox's historical-candle endpoint is meant for its API users, and it currently answers without a login. That could change without notice; if it does, the job falls back to Yahoo automatically and you'll see "Yahoo (backup)" in the site header. Keep the dashboard for personal use; don't resell the data.
