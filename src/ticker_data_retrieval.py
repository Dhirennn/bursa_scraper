"""
This module contains functions for retrieving stock data from Yahoo Finance.
"""
import yfinance as yf
import pandas as pd


def load_ticker_map(filename):
    """
    Load ticker to stock code mapping from a file into a dictionary.

    Args:
    - filename (str): Name of the file containing the ticker to stock code mapping.

    Returns:
    - dict: Dictionary with tickers as keys and stock codes as values.
    """
    ticker_map = {}

    with open(filename, "r") as file:
        for line in file:
            # Split each line at the colon to get the ticker and stock code
            ticker, stock_code = line.strip().split(" : ")
            ticker_map[ticker] = stock_code

    return ticker_map


def get_stock_code(ticker, ticker_map):
    """
    Get the stock code for a given ticker using a ticker map.

    Args:
    - ticker (str): The ticker to look up.
    - ticker_map (dict): Dictionary with tickers as keys and stock codes as values.

    Returns:
    - str: Stock code for the given ticker or None if the ticker is not found.
    """
    return ticker_map.get(ticker)


def get_stock_price(ticker, start_date, end_date):
    # Load the ticker map from the file
    ticker_map = load_ticker_map("data/ticker_map.txt")

    stock_code = get_stock_code(ticker, ticker_map)

    ticker_data = yf.Ticker(f"{stock_code}.KL").history(start=start_date, end=end_date)

    ticker_data = ticker_data.reset_index()

    return ticker_data


if __name__ == "__main__":

    # Example usage for getting stock price data of GENM from 2000-01-01 to 2023-09-29
    genm_data = get_stock_price("GENM", "2000-01-01", "2023-09-29")
    print(genm_data)
