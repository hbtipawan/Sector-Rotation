"""Older daily closes from BSE for stocks that moved to NSE recently.

Many companies listed on BSE for years were only added to NSE in 2025-26, so NSE history
starts at the NSE listing and their bases would look short. For those stocks this fetches
the BSE history (Upstox, same split/bonus adjustment) for the days before the NSE listing.
BSE volume is scaled to NSE size using the days both exchanges traded.

Output: cache/bse_backfill.csv.gz (symbol,date,close,volume) - read by bases.py.
Stocks with no older BSE data (IPOs listed on both exchanges together) are remembered in
config/bse_skip.csv so they are not asked for again.

Run: python scripts/fetch_bse_backfill.py   (after fetch_prices.py)
"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE, CFG = ROOT / "cache", ROOT / "config"
S = json.loads((CFG / "settings.json").read_text())
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


_lock, _next = threading.Lock(), [0.0]


def get(key, frm, to):
    for a in range(4):
        with _lock:                                   # ~8 requests a second across threads
            w = _next[0] - time.monotonic()
            _next[0] = max(_next[0], time.monotonic()) + 0.125
        if w > 0:
            time.sleep(w)
        try:
            r = requests.get(f"https://api.upstox.com/v3/historical-candle/{quote(key, safe='')}/days/1/{to}/{frm}",
                             headers=UA, timeout=40)
            if r.status_code == 200:
                return (r.json().get("data") or {}).get("candles") or []
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 + 2 * a)
                continue
            return []
        except requests.RequestException:
            time.sleep(2)
    return None


def main():
    days = S.get("base_history_calendar_days", 0)
    if not days:
        return print("base_history_calendar_days not set - nothing to do")
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    frm = (today - timedelta(days=days)).isoformat()
    p = pd.read_csv(CACHE / "prices.csv.gz", dtype={"symbol": str, "date": str}, usecols=["symbol", "date", "close", "volume"])
    u = pd.read_csv(CACHE / "universe.csv", dtype=str)
    u = u[(u.kind == "stock") & u["isin"].notna()].set_index("symbol")
    first = p.groupby("symbol").date.min()
    tail = p[p.date >= (today - timedelta(days=80)).isoformat()]
    med_to = (tail.close * tail.volume / 1e7).groupby(tail.symbol).median()
    last_px = tail.groupby("symbol").close.last()
    skip_f = CFG / "bse_skip.csv"
    skip = set(pd.read_csv(skip_f).symbol) if skip_f.exists() else set()
    short = [s for s in u.index if s in first.index and first[s] > (today - timedelta(days=days - 45)).isoformat()
             and med_to.get(s, 0) >= 0.5 * S["min_median_turnover_cr"] and last_px.get(s, 0) >= S["min_price"] and s not in skip]
    print(f"{len(short)} liquid stocks with NSE history shorter than {days} days")
    out, new_skip, t0 = [], [], time.time()
    nse = {s: g for s, g in p[p.symbol.isin(set(short))].groupby("symbol")}

    def job(s):
        c = get(f"BSE_EQ|{u.loc[s, 'isin']}", frm, today.isoformat())
        if c is None:
            return s, None                            # network trouble: try again tomorrow
        b = pd.DataFrame([(x[0][:10], x[4], x[5]) for x in c], columns=["date", "close", "volume"]).sort_values("date")
        b = b[b.close > 0]
        before = b[b.date < first[s]]
        if len(before) < 20:
            return s, "skip"                          # nothing older on BSE (listed on both together)
        n = nse[s][["date", "volume"]].merge(b[["date", "volume"]], on="date", suffixes=("_n", "_b"))
        n = n[(n.volume_n > 0) & (n.volume_b > 0)]
        k = float(np.median(n.volume_n / n.volume_b)) if len(n) >= 10 else 1.0
        return s, before.assign(volume=(before.volume * k).round(), symbol=s)[["symbol", "date", "close", "volume"]]

    with ThreadPoolExecutor(6) as ex:
        for i, (s, r) in enumerate(ex.map(job, short), 1):
            if isinstance(r, str):
                new_skip.append(s)
            elif r is not None:
                out.append(r)
            if i % 200 == 0:
                print(f"  {i}/{len(short)}  {time.time() - t0:.0f}s", flush=True)
    if new_skip:
        pd.DataFrame({"symbol": sorted(skip | set(new_skip))}).to_csv(skip_f, index=False)
    df = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["symbol", "date", "close", "volume"])
    df.to_csv(CACHE / "bse_backfill.csv.gz", index=False, compression="gzip")
    print(f"BSE backfill: {df.symbol.nunique()} stocks, {len(df)} older daily closes; "
          f"{len(new_skip)} newly marked as no older BSE data; {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
