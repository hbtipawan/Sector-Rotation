"""Download daily candles for every NSE stock + benchmark indices.

Sources (no login, no account, no API key):
  upstox (default) - Upstox public historical-candle API. Split/bonus adjusted.
                     Today's candle is topped up from NSE's official bhavcopy
                     (or Upstox's intraday endpoint) if the history call doesn't
                     include it yet.
  yahoo  (backup)  - Yahoo Finance chart API.

Output: cache/prices.csv.gz  (symbol,date,open,high,low,close,volume)
        cache/universe.csv   (symbol,name,series,key,kind,isin)

Run:  python scripts/fetch_prices.py
      python scripts/fetch_prices.py --source yahoo
      python scripts/fetch_prices.py --limit 50     (quick test)
"""
import argparse
import gzip
import io
import json
import os
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
SETTINGS = json.loads((ROOT / "config" / "settings.json").read_text())
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
IST = timezone(timedelta(hours=5, minutes=30))
UPSTOX = "https://api.upstox.com/v3/historical-candle"

# Display name -> Upstox index key
INDEX_KEYS = {
    "NIFTY 500": "NSE_INDEX|Nifty 500",
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "NIFTY MIDCAP 150": "NSE_INDEX|NIFTY MIDCAP 150",
    "NIFTY SMLCAP 250": "NSE_INDEX|NIFTY SMLCAP 250",
    "NIFTY MICROCAP250": "NSE_INDEX|NIFTY MICROCAP250",
}


def today_ist():
    return datetime.now(IST).date()


# ---------------------------------------------------------------- universe
def build_universe():
    """All NSE stocks in allowed series, from Upstox's public instrument list."""
    r = requests.get("https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
                     headers={"User-Agent": UA}, timeout=120)
    r.raise_for_status()
    ins = json.loads(gzip.decompress(r.content))
    allowed = set(SETTINGS["include_series"])
    # Keep only listed companies (NSE's equity list excludes ETFs, which Upstox also tags EQ).
    companies = None
    try:
        e = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv",
                         headers={"User-Agent": UA}, timeout=60)
        e.raise_for_status()
        eq = pd.read_csv(io.StringIO(e.text))
        eq.columns = [c.strip() for c in eq.columns]
        companies = set(eq["ISIN NUMBER"].astype(str).str.strip())
        (CACHE / "equity_l.csv").write_text(e.text)
    except Exception as ex:
        cached = CACHE / "equity_l.csv"
        if cached.exists():
            eq = pd.read_csv(cached)
            eq.columns = [c.strip() for c in eq.columns]
            companies = set(eq["ISIN NUMBER"].astype(str).str.strip())
        print(f"WARN NSE equity list not downloaded ({ex}); "
              f"{'using cached copy' if companies else 'ETFs may be included'}")
    rows, seen = [], set()
    for x in ins:
        if x.get("segment") != "NSE_EQ" or x.get("instrument_type") not in allowed:
            continue
        if companies is not None and x.get("isin") not in companies:
            continue
        sym = x.get("trading_symbol")
        if not sym or sym in seen:
            continue
        seen.add(sym)
        rows.append((sym, x.get("name", sym), x["instrument_type"], x["instrument_key"], "stock", x.get("isin", "")))
    for name in [SETTINGS["benchmark"]] + SETTINGS["extra_indices"]:
        if name in INDEX_KEYS:
            rows.append((name, name, "INDEX", INDEX_KEYS[name], "index", ""))
    return pd.DataFrame(rows, columns=["symbol", "name", "series", "key", "kind", "isin"])


# ---------------------------------------------------------------- upstox
_session = threading.local()


def sess():
    if not hasattr(_session, "s"):
        _session.s = requests.Session()
        _session.s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return _session.s


def _candles_to_df(c):
    if not c:
        return None
    d = pd.DataFrame(c).iloc[:, :6]
    d.columns = ["date", "open", "high", "low", "close", "volume"]
    d["date"] = d["date"].str[:10]
    return d.sort_values("date").drop_duplicates("date", keep="last")


def upstox_get(url):
    for attempt in range(6):
        try:
            r = sess().get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(30, 3 * (attempt + 1)))
            continue
        if r.status_code != 200:
            return None
        j = r.json()
        return j.get("data", {}).get("candles") if j.get("status") == "success" else None
    raise RuntimeError("Upstox kept refusing (rate limit or outage)")


def upstox_history(key, frm, to):
    return _candles_to_df(upstox_get(f"{UPSTOX}/{quote(key, safe='')}/days/1/{to}/{frm}"))


def upstox_today(key):
    return _candles_to_df(upstox_get(f"{UPSTOX}/intraday/{quote(key, safe='')}/days/1"))


def nse_bhavcopy(d):
    """Official NSE end-of-day file for date d -> DataFrame keyed by ISIN, or None."""
    name = f"BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    for host in ("https://nsearchives.nseindia.com", "https://archives.nseindia.com"):
        try:
            r = requests.get(f"{host}/content/cm/{name}", headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 200 and r.content[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(r.content))
                b = pd.read_csv(z.open(z.namelist()[0]))
                b = b[b["SctySrs"].isin(SETTINGS["include_series"])]
                b = b.rename(columns={"OpnPric": "open", "HghPric": "high", "LwPric": "low",
                                      "ClsPric": "close", "TtlTradgVol": "volume"})
                b["date"] = d.isoformat()
                return b.set_index("ISIN")[["date", "open", "high", "low", "close", "volume"]]
        except Exception:
            pass
    return None


# ---------------------------------------------------------------- yahoo (backup)
YAHOO_INDEX = {"NIFTY 500": "^CRSLDX", "NIFTY 50": "^NSEI", "NIFTY MIDCAP 150": "NIFTYMIDCAP150.NS",
               "NIFTY SMLCAP 250": "NIFTYSMLCAP250.NS"}


def yahoo_candles(symbol, kind, days):
    ys = YAHOO_INDEX.get(symbol) if kind == "index" else f"{symbol}.NS"
    if not ys:
        return None
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ys)}",
                     params={"range": "2y" if days <= 730 else "5y", "interval": "1d"},
                     headers={"User-Agent": UA}, timeout=30)
    if r.status_code != 200:
        return None
    res = r.json()["chart"]["result"]
    if not res or "timestamp" not in res[0]:
        return None
    q = res[0]["indicators"]["quote"][0]
    d = pd.DataFrame({"date": pd.to_datetime(res[0]["timestamp"], unit="s", utc=True)
                      .tz_convert("Asia/Kolkata").strftime("%Y-%m-%d"),
                      "open": q["open"], "high": q["high"], "low": q["low"],
                      "close": q["close"], "volume": q["volume"]}).dropna(subset=["close"])
    d = d[d["date"] >= (date.today() - timedelta(days=days)).isoformat()]
    return d.drop_duplicates("date", keep="last")


# ---------------------------------------------------------------- runner
class RateLimiter:
    def __init__(self, per_sec):
        self.gap, self.lock, self.next = 1.0 / per_sec, threading.Lock(), 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next)
            self.next = t + self.gap
        time.sleep(max(0, t - now))


def run_pool(rows, job, workers, label):
    out, failed, t0 = {}, [], time.time()
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(job, r): r for r in rows}
        for n, f in enumerate(as_completed(futs), 1):
            r = futs[f]
            try:
                d = f.result()
                if d is not None and len(d):
                    out[r.symbol] = d
                else:
                    failed.append(r.symbol)
            except Exception as e:
                failed.append(f"{r.symbol}:{type(e).__name__}")
            if n % 500 == 0:
                print(f"  {label} {n}/{len(rows)}  {time.time() - t0:.0f}s", flush=True)
    return out, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["upstox", "yahoo"], default=os.environ.get("PRICE_SOURCE", "upstox"))
    ap.add_argument("--limit", type=int, default=0, help="only first N stocks (testing)")
    a = ap.parse_args()

    CACHE.mkdir(exist_ok=True)
    u = build_universe()
    if a.limit:
        u = pd.concat([u[u.kind == "index"], u[u.kind == "stock"].head(a.limit)])
    u.to_csv(CACHE / "universe.csv", index=False)
    print(f"Universe: {(u.kind == 'stock').sum()} stocks + {(u.kind == 'index').sum()} indices; source={a.source}")

    days = SETTINGS["history_calendar_days"]
    today = today_ist()
    frm, to = (today - timedelta(days=days)).isoformat(), today.isoformat()
    rows = list(u.itertuples())
    t0 = time.time()

    if a.source == "upstox":
        rl = RateLimiter(SETTINGS.get("upstox_requests_per_second", 10))

        def job(row):
            rl.wait()
            return upstox_history(row.key, frm, to)
        data, failed = run_pool(rows, job, 8, "history")

        # Top up today's candle if the history call stopped at yesterday.
        latest = max(d["date"].iloc[-1] for d in data.values()) if data else ""
        after_close = datetime.now(IST).hour * 60 + datetime.now(IST).minute >= 15 * 60 + 40
        if today.weekday() < 5 and after_close and latest < to:
            bhav = nse_bhavcopy(today)
            missing = [r for r in rows if r.symbol in data and data[r.symbol]["date"].iloc[-1] < to]
            still = []
            if bhav is not None:
                print(f"Adding today's candle from NSE bhavcopy ({len(bhav)} rows)")
                for r in missing:
                    if r.kind == "stock" and r.isin in bhav.index:
                        b = bhav.loc[[r.isin]].iloc[[0]].reset_index(drop=True)
                        data[r.symbol] = pd.concat([data[r.symbol], b], ignore_index=True)
                    else:
                        still.append(r)
            else:
                still = missing
            if still:
                print(f"Adding today's candle from Upstox intraday for {len(still)} symbols")

                def tjob(row):
                    rl.wait()
                    return upstox_today(row.key)
                tod, _ = run_pool(still, tjob, 8, "today")
                for s, d in tod.items():
                    d = d[d["date"] == to]
                    if len(d):
                        data[s] = pd.concat([data[s], d], ignore_index=True)
    else:
        rl = RateLimiter(8)

        def job(row):
            rl.wait()
            return yahoo_candles(row.symbol, row.kind, days)
        data, failed = run_pool(rows, job, 8, "yahoo")

    if not data:
        sys.exit("No data downloaded")
    out = []
    for s, d in data.items():
        d = d.drop_duplicates("date", keep="last").copy()
        d.insert(0, "symbol", s)
        out.append(d)
    p = pd.concat(out, ignore_index=True)
    p.to_csv(CACHE / "prices.csv.gz", index=False, compression="gzip")
    (CACHE / "fetch_meta.json").write_text(json.dumps({
        "source": a.source, "symbols": p.symbol.nunique(), "rows": len(p),
        "last_date": p.date.max(), "failed": failed[:200], "failed_count": len(failed),
        "seconds": round(time.time() - t0)}, indent=1))
    print(f"Saved {p.symbol.nunique()} symbols, {len(p)} rows, last date {p.date.max()}, "
          f"failed {len(failed)}, {time.time() - t0:.0f}s")
    # Guard: a broken run must never overwrite the website.
    if len(failed) > 0.3 * len(rows):
        sys.exit("Too many failures - not publishing")


if __name__ == "__main__":
    main()
