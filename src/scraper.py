"""
This file contains functions that are used to scrape data from the web.
"""

import requests
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
from time import time
import os
import pprint


# Functions to scrape ticker code from i3investor.com #
def get_ticker_code(ticker):
    """
    Used to get ticker (stock) code.
    e.g; $GENM = 4715

    :param ticker: ticker name ( e.g; GENM )
    :return: number ( e.g; 4715 )
    """
    # First, I make a request to i3investor.com to scrape the ticker code
    url = f"https://klse.i3investor.com/web/stock/overview/{ticker}"

    # Default number if no number is found (This is $GENM's ticker code, I will manually modify later)
    number = 4715

    # get response from the site and extract the price data
    response = requests.get(url, headers={"User-Agent": "test"})
    soup = BeautifulSoup(response.content, "html.parser")
    script = soup.find_all("strong")

    try:
        # script[1].text contains info like this: KLSE (MYR): GENM (4715)
        if len(script) >= 1:
            ticker_info = script[1].text
        else:
            ticker_info = "(4715)"
    except IndexError:
        print("continue")

    # Use regex to search for the number within the parentheses
    match = re.search(r"\((\d+)\)", ticker_info)

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

    # Ensure the data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")

    # Loop through tickers and get their numbers
    for ticker in tqdm(tickers):
        try:
            number = get_ticker_code(ticker)

            # Write the ticker and its number to the file immediately using append
            with open("data/ticker_map.txt", "a") as file:
                file.write(f"{ticker} : {number}\n")

        except Exception as e:
            print(f"Unexpected error for {ticker}: {e}")

    print("Time taken: ", time() - start_time)


def get_stock_list():
    """
    Used to scrape the list of ALL stocks (tickers) in BURSA from malaysiastock.biz.
    The name of the stocks are the tickers themselves.
    Returns: list of tickers (stocks)

    """
    # scrape the list of stocks from malaysiastock.biz
    url = "https://www.malaysiastock.biz/Stock-Screener.aspx"
    response = requests.get(url, headers={"User-Agent": "test"})
    soup = BeautifulSoup(response.content, "html.parser")

    # find the table that contains the list of stocks
    table = soup.find(id="MainContent2_tbAllStock")

    # return the result in a list
    return [stock.getText() for stock in table.find_all("a")]


def get_price_target(ticker):
    """
    Get the Average Target Price based on the provided HTML structure (version 2).

    Args:
    - ticker (str): The ticker symbol for which to fetch the price target.

    Returns:
    - str: The extracted Average Target Price.
    """
    url = f"https://klse.i3investor.com/web/stock/analysis-price-target/{ticker}"
    response = requests.get(url, headers={"User-Agent": "test"})
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the <p> tag with the string "Avg Target Price"
    avg_target_price_label = soup.find("p", string="Avg Target Price")

    # If found, navigate to the <strong> tag inside its sibling <p> tag to retrieve the desired value
    if avg_target_price_label:
        avg_target_price_value_tag = avg_target_price_label.find_next_sibling("p").find(
            "strong"
        )
        if avg_target_price_value_tag:
            return avg_target_price_value_tag.text.strip()

    return None


def get_analyst_projections(ticker):
    """
    Get the analyst projections (SELL, HOLD, BUY) based on the provided HTML structure.

    Args:
    - ticker (str): The ticker symbol for which to fetch the analyst projections.

    Returns:
    - dict: A dictionary containing the analyst projections for SELL, HOLD, and BUY.
    """
    url = f"https://klse.i3investor.com/web/stock/analysis-price-target/{ticker}"
    response = requests.get(url, headers={"User-Agent": "test"})
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all <div class="col-4"> tags which contain the projections
    projection_divs = soup.find_all("div", class_="col-4")

    projections = {}

    for div in projection_divs:
        # Extract the number from the nested <strong> tag
        number_tag = div.find("strong")
        if number_tag:
            number = number_tag.text.strip()

            # Extract the action label from the nested <p class="subtitle"> tag
            action_label_tag = div.find("p", class_="subtitle")
            if action_label_tag:
                action_label = action_label_tag.text.strip().upper()
                projections[action_label] = number

    return projections


if __name__ == "__main__":
    petronas = get_ticker_code("PETGAS")
    print(petronas)
    print(get_price_target(petronas))
    pprint.pprint(get_analyst_projections(petronas))
