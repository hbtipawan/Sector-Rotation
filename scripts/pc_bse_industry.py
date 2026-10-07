"""OPTIONAL - run this on YOUR OWN PC (Indian internet), not on GitHub.

BSE blocks cloud servers, but from a home connection its public scrip list gives
every listed company's industry and market cap. This fills two gaps:
  * an "Industry" grouping that covers all ~2,000 stocks (NSE index lists cover ~750)
  * the Rs 500 Cr market-cap filter

Writes config/industry_bse.csv (ISIN, Industry, MarketCapCr). Commit that file to
GitHub (upload it on the website). Re-run once a month or so.

Run:  pip install requests pandas
      python scripts/pc_bse_industry.py
"""
from pathlib import Path

import pandas as pd
import requests

URL = ("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
       "?Group=&Scripcode=&industry=&segment=Equity&status=Active")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 Safari/537.36",
     "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
OUT = Path(__file__).resolve().parents[1] / "config" / "industry_bse.csv"


def pick(row, *names):
    low = {k.lower(): v for k, v in row.items()}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def main():
    r = requests.get(URL, headers=H, timeout=60)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):  # some versions wrap the list
        data = next((v for v in data.values() if isinstance(v, list)), [])
    rows = []
    for d in data:
        isin = pick(d, "ISIN_NUMBER", "ISIN")
        ind = pick(d, "INDUSTRY", "Industry")
        mc = pick(d, "Mktcap", "MKTCAP", "MarketCap")
        if isin and ind:
            try:
                mc = float(str(mc).replace(",", "")) if mc not in (None, "") else None
            except ValueError:
                mc = None
            rows.append((isin.strip(), str(ind).strip(), mc))
    df = pd.DataFrame(rows, columns=["ISIN", "Industry", "MarketCapCr"]).drop_duplicates("ISIN")
    if df.empty:
        raise SystemExit("BSE returned no rows - the site layout may have changed.")
    # Sanity check on units using Reliance (ISIN INE002A01018): should be lakhs of crore.
    rel = df.loc[df.ISIN == "INE002A01018", "MarketCapCr"]
    if len(rel) and rel.iloc[0] and rel.iloc[0] > 1e8:  # reported in rupees/lakhs -> convert
        df["MarketCapCr"] = df["MarketCapCr"] / 1e7
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} companies to {OUT}")
    if len(rel):
        print(f"Check: Reliance market cap = {df.loc[df.ISIN == 'INE002A01018', 'MarketCapCr'].iloc[0]:,.0f} Cr")


if __name__ == "__main__":
    main()
