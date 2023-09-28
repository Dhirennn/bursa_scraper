from ticker_data_retrieval import get_stock_price


def compute_rsi(data, period=14, return_all=False):
    """
    Compute the Relative Strength Index (RSI) for a given data using the TradingView method.

    Args:
    - data (pd.DataFrame): DataFrame containing the stock prices with a 'Close' column.
    - period (int): The period for RSI computation (default is 14 days).
    - return_all (bool): Whether to return the RSI for all days or just the latest value.

    Returns:
    - pd.Series or float: If return_all is True, a series containing RSI values is returned.
                          Otherwise, the latest RSI value is returned.
    """

    # Calculate the price change for each period
    delta = data["Close"].diff()

    # Calculate the average gain and average loss for the specified period
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    # Calculate the Relative Strength (RS) by dividing the average gain by the average loss
    rs = avg_gain / avg_loss

    # Calculate the Relative Strength Index (RSI)
    rsi = 100 - (100 / (1 + rs))

    data["RSI"] = rsi

    return data["RSI"] if return_all else data["RSI"].iloc[-1]


if __name__ == "__main__":
    # Fetching the stock price data for GENM again using the get_stock_price function
    genm_data = get_stock_price("PETGAS", "2000-01-01", "2023-09-27")
    print(genm_data)
    latest_rsi_genm = compute_rsi(genm_data)
    print(latest_rsi_genm)
