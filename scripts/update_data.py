#!/usr/bin/env python3
"""
Fetch stock data for a watchlist and produce a JSON file consumable by the static site.

Inputs:
  - ../watchlist.txt : newline-separated tickers (e.g., AAPL)
  - Environment: ALPHA_VANTAGE_KEY

Outputs:
  - ../site/data.json : consolidated dashboard data
  - ../site/alert_content.txt : only created if any stock change > 2% or < -2%

Dependencies:
  - yfinance
  - requests
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests
import yfinance as yf


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WATCHLIST_PATH = os.path.join(ROOT_DIR, 'watchlist.txt')
SITE_DIR = os.path.join(ROOT_DIR, 'site')
DATA_JSON_PATH = os.path.join(SITE_DIR, 'data.json')
ALERT_PATH = os.path.join(SITE_DIR, 'alert_content.txt')


def read_watchlist(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Watchlist not found at {path}")
    tickers: List[str] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith('#'):
                tickers.append(t)
    return tickers


def fetch_alpha_vantage_series(ticker: str, api_key: str) -> List[float]:
    """Return last 30 closing prices (oldest -> newest)."""
    url = (
        'https://www.alphavantage.co/query'
        f'?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&outputsize=compact'
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    series = data.get('Time Series (Daily)')
    if not isinstance(series, dict):
        # Alpha Vantage may rate-limit; return empty list if not available
        return []
    # Sort dates ascending, take last 30
    dates = sorted(series.keys())[-30:]
    closes: List[float] = []
    for d in dates:
        try:
            closes.append(float(series[d]['4. close']))
        except Exception:
            continue
    return closes


def safe_get_info(t: yf.Ticker, key: str):
    # yfinance.info can be slow/partial; try fast_info fallback
    try:
        info = t.info or {}
        if key in info and info[key] is not None:
            return info[key]
    except Exception:
        pass
    try:
        fi = getattr(t, 'fast_info', None)
        if fi is not None and hasattr(fi, key):
            return getattr(fi, key)
    except Exception:
        pass
    return None


def fetch_current_open_name(ticker: str) -> Dict[str, Any]:
    t = yf.Ticker(ticker)
    # Current price
    current = None
    # Try info currentPrice, then lastPrice from fast_info, then history
    current = safe_get_info(t, 'currentPrice')
    if current is None:
        current = safe_get_info(t, 'lastPrice')
    if current is None:
        try:
            hist = t.history(period='1d', interval='1m')
            if not hist.empty:
                current = float(hist['Close'].iloc[-1])
        except Exception:
            current = None

    # Open price
    day_open = None
    day_open = safe_get_info(t, 'open')
    if day_open is None:
        try:
            hist_d = t.history(period='1d')
            if not hist_d.empty:
                day_open = float(hist_d['Open'].iloc[0])
        except Exception:
            day_open = None

    # Company name
    company_name = None
    try:
        info = t.info or {}
        company_name = info.get('longName') or info.get('shortName')
    except Exception:
        company_name = None
    if not company_name:
        company_name = ticker

    return {
        'current': current,
        'open': day_open,
        'companyName': company_name,
    }


def main() -> int:
    os.makedirs(SITE_DIR, exist_ok=True)

    try:
        tickers = read_watchlist(WATCHLIST_PATH)
    except Exception as e:
        print(f"Error reading watchlist: {e}", file=sys.stderr)
        return 1

    alpha_key = os.environ.get('ALPHA_VANTAGE_KEY')
    if not alpha_key:
        print("ALPHA_VANTAGE_KEY is not set in environment", file=sys.stderr)
        return 1

    stocks_out: List[Dict[str, Any]] = []
    alerts: List[str] = []

    for ticker in tickers:
        try:
            basics = fetch_current_open_name(ticker)
            current = basics['current']
            day_open = basics['open']
            company_name = basics['companyName']

            # Historical series (best-effort; Alpha Vantage can rate-limit)
            series = fetch_alpha_vantage_series(ticker, alpha_key)

            # Compute changes
            if current is None or day_open is None or day_open == 0:
                day_change = None
                pct_change = None
            else:
                day_change = float(current) - float(day_open)
                pct_change = (day_change / float(day_open)) * 100.0

            stock_item = {
                'ticker': ticker,
                'companyName': company_name,
                'currentPrice': round(float(current), 2) if isinstance(current, (int, float)) else None,
                'dayChange': round(float(day_change), 2) if isinstance(day_change, (int, float)) else None,
                'dayChangePercent': round(float(pct_change), 2) if isinstance(pct_change, (int, float)) else None,
                'historicalData': [round(float(x), 2) for x in series][-30:],
            }
            stocks_out.append(stock_item)

            # Alerts
            if isinstance(pct_change, (int, float)) and (pct_change > 2.0 or pct_change < -2.0):
                direction = 'up' if pct_change > 2 else 'down'
                alerts.append(f"STOCK ALERT: {ticker} is {direction} {round(pct_change, 2)}%")

            # Be a bit polite to the free API
            time.sleep(1.0)

        except Exception as e:
            print(f"Error processing {ticker}: {e}", file=sys.stderr)
            continue

    payload = {
        'lastUpdated': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'stocks': stocks_out,
    }

    with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    # Write alert file only if alerts exist
    if alerts:
        with open(ALERT_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(alerts).strip() + '\n')

    print(f"Wrote {DATA_JSON_PATH} with {len(stocks_out)} stocks")
    if alerts:
        print(f"Alerts generated: {len(alerts)} -> {ALERT_PATH}")
    else:
        print("No alerts generated")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())


