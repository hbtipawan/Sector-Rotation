"""All-time-high reference for the Green Line Breakout scanner.

The daily price file holds about two years. For the all-time high we also need
the older history, which Upstox serves as monthly candles back to listing
(public endpoint, no login, split/bonus adjusted).

Writes config/ath.csv:  symbol, ath_before, cutoff
  ath_before = highest monthly high in the months BEFORE `cutoff`
  cutoff     = first day of the month in which the file was built
compute.py combines it with the daily highs from `cutoff` onwards, so the file
only needs refreshing now and then; it is rebuilt when older than 7 days
(and that also picks up any new split adjustments).
"""
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import fetch_prices as F  # noqa: E402  (reuses the session, retry logic and rate limiter)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "ath.csv"
MAX_AGE_DAYS = 7


def main():
    force = "--force" in sys.argv
    if OUT.exists() and not force:
        old = pd.read_csv(OUT)
        built = pd.to_datetime(old["built"].iloc[0]).date() if "built" in old and len(old) else None
        if built and (F.today_ist() - built).days < MAX_AGE_DAYS:
            print(f"ath.csv built {built}, still fresh - skipping")
            return
    u = pd.read_csv(F.CACHE / "universe.csv", dtype={"symbol": str})
    u = u[u.kind == "stock"]
    today = F.today_ist()
    cutoff = today.replace(day=1)
    to = (cutoff - timedelta(days=1)).isoformat()
    rl = F.RateLimiter(F.SETTINGS.get("upstox_requests_per_second", 10))

    def job(row):
        rl.wait()
        c = F.upstox_get(f"{F.UPSTOX}/{quote(row.key, safe='')}/months/1/{to}/2000-01-01")
        if not c:
            return None
        return pd.Series([pd.Series([x[2] for x in c], dtype=float).max()])  # 1-item Series (run_pool needs len)

    t0 = time.time()
    data, failed = F.run_pool(list(u.itertuples()), job, 8, "monthly")
    out = pd.DataFrame({"symbol": list(data), "ath_before": [round(float(v.iloc[0]), 2) for v in data.values()]})
    out["cutoff"], out["built"] = cutoff.isoformat(), today.isoformat()
    out.sort_values("symbol").to_csv(OUT, index=False)
    print(f"ath.csv: {len(out)} stocks, {len(failed)} without older history (new listings), {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
