"""
Alternate entry point: runs the EMA18/50 crossover screener using the
local data/ticker_map.txt as the universe (avoids scraping malaysiastock.biz)
and a current date window.

Run from src/:  python run_screener.py
"""
from datetime import date
from functools import partial
from time import time
import concurrent.futures

from tqdm import tqdm

from ticker_data_retrieval import get_stock_price, load_ticker_map
from exponential_moving_average import add_EMA_to_df, check_EMA_crossing


START_DATE = "2020-01-01"
END_DATE = date.today().isoformat()


def screen(ticker):
    try:
        df = get_stock_price(ticker, START_DATE, END_DATE)
        if df is None or df.empty:
            return None
        add_EMA_to_df(df)
        if check_EMA_crossing(df):
            return ticker
    except Exception:
        return None


def main():
    start = time()
    ticker_map = load_ticker_map("../data/ticker_map.txt")
    tickers = sorted(ticker_map.keys())

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        results = list(tqdm(executor.map(screen, tickers), total=len(tickers)))

    hits = [t for t in results if t]

    print(f"\nTime taken: {time() - start:.1f}s")
    print(f"Screened {len(tickers)} tickers, {len(hits)} matched.")
    print(f"Window: {START_DATE} to {END_DATE}")
    print("Criteria: EMA18 > EMA50 on last day, EMA18 < EMA50 previous day, >=51 candles.\n")
    for t in hits:
        print(f"  {t:<12} {ticker_map[t]}")


if __name__ == "__main__":
    main()
