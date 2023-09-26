"""
This file contains functions that are used to scrape data from the web.
"""

import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from time import time


# Functions to scrape ticker code from i3investor.com #
def get_ticker_code(ticker):
    """
    Used to get ticker (stock) code.
    e.g; $GENM = 4715

    :param ticker: ticker name ( e.g; GENM )
    :return: number ( e.g; 4715 )
    """
    # First, I make a request to i3investor.com to scrape the ticker code
    url = f'https://klse.i3investor.com/web/stock/overview/{ticker}'

    # Default number if no number is found (This is $GENM's ticker code, I will manually modify later)
    number = 4715

    # get response from the site and extract the price data
    response = requests.get(url, headers={'User-Agent': 'test'})
    soup = BeautifulSoup(response.content, "html.parser")
    script = soup.find_all('strong')

    try:
        # script[1].text contains info like this: KLSE (MYR): GENM (4715)
        if len(script) >= 1:
            ticker_info = script[1].text
        else:
            ticker_info = "(4715)"
    except IndexError:
        print("continue")

    # Use regex to search for the number within the parentheses
    match = re.search(r'\((\d+)\)', ticker_info)

    # Extract the number if a match is found
    if match:
        number = match.group(1)
    else:
        print(f"No number found within parentheses for {ticker}.")

    return number


def update_tickers_number(tickers):
    """
    Used to update the ticker map file with the latest ticker numbers.
    This is because saving the ticker numbers in a file is faster than scraping them from the web
    every time I need them.
    Args:
        tickers: list of tickers to update (e.g; ['GENM', 'GENTING'])

    Returns: None

    """
    # Dictionary to store ticker-number mapping
    ticker_map = {}

    # Track start time
    start_time = time()


    # Loop through tickers and get their numbers
    for ticker in tqdm(tickers):
        try:
            number = get_ticker_code(ticker)

            # Write the ticker and its number to the file immediately using append
            with open('ticker_map.txt', 'a') as file:
                file.write(f"{ticker} : {number}\n")

        except Exception as e:
            print(f"Unexpected error for {ticker}: {e}")

    print('Time taken: ', time() - start_time)



def get_stock_list():
    """
    Used to scrape the list of ALL stocks (tickers) in BURSA from malaysiastock.biz.
    The name of the stocks are the tickers themselves.
    Returns: list of tickers (stocks)

    """
    # scrape the list of stocks from malaysiastock.biz
    url = "https://www.malaysiastock.biz/Stock-Screener.aspx"
    response = requests.get(url, headers={'User-Agent': 'test'})
    soup = BeautifulSoup(response.content, "html.parser")

    # find the table that contains the list of stocks
    table = soup.find(id="MainContent2_tbAllStock")

    # return the result in a list
    return [stock.getText() for stock in table.find_all('a')]




if __name__ == "__main__":
    print(len(get_stock_list()))








