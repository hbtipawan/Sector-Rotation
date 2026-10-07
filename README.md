# PKC Sector Radar

A free, ScreeningMantis-style dashboard for NSE stocks:

- **Rotation** – theme / sector / NSE-index returns for Today, 1W, 1M, 3M, 6M, YTD, 1Y, with mean or median, rank change vs last week, and a click-through list of the stocks in each group.
- **Breadth** – % of stocks above 20/50/200 DMA, advance/decline, 52-week highs/lows, 4% movers, one year of history.
- **RS ranking** – every stock ranked 1–99 by relative strength, filterable by sector, theme, Stage 2, Minervini trend template.
- **Scanners** – 52-week closing highs, Darvas box breakouts, volume spikes, 20/50 EMA crossovers, leaders near highs, trend template.

**No broker login, no API key, no password.** Prices come from Upstox's public historical-candle service, which answers without an account. Today's candle is added from NSE's official bhavcopy. Yahoo Finance is wired in as a backup.

```
GitHub Actions (6:40 PM IST, Mon–Fri, free)
   ├─ update_reference.py   sector + NSE index lists      (niftyindices.com)
   ├─ fetch_prices.py       2 years of daily candles       (Upstox → NSE bhavcopy for today; Yahoo backup)
   ├─ compute.py            returns, RS, breadth, scans    → docs/data/*.json
   └─ commit docs/data      → website updates itself
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
