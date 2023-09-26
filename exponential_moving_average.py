"""
Exponential Moving Average (EMA) is a type of moving average (MA) that places a greater weight and significance on the
most recent data points. The exponential moving average is also referred to as the exponentially weighted moving average.
An exponentially weighted moving average reacts more significantly to recent price changes than a simple moving average
(SMA), which applies an equal weight to all observations in the period.
"""
from ticker_data_retrieval import get_stock_price


def calculate_EMA(price, day):
    """
    Calculate the Exponential Moving Average (EMA) for a given price and day.
    Args:
        price: price of the stock
        day: number of days

    Returns:

    """
    return price.ewm(span=day).mean()



def add_EMA_to_df(df):
    """
    Add EMA18, EMA50, EMA100, EMA200 to the dataframe.
    Args:
        df: dataframe containing the stock price

    Returns:

    """
    df['EMA18'] = calculate_EMA(df['Close'], 18)
    df['EMA50'] = calculate_EMA(df['Close'], 50)
    df['EMA100'] = calculate_EMA(df['Close'], 100)
    df['EMA200'] = calculate_EMA(df['Close'], 200)


def check_EMA_crossing(df):
    """
    Check for EMA crossing conditions in the given dataframe.

    Parameters:
    - df (pd.DataFrame): DataFrame containing stock data with EMA18 and EMA50 columns.

    Returns:
    - bool: True if all conditions are met, False otherwise.
    """

    # Ensure there are enough data points for the checks
    if len(df) < 51:
        return False

    # Check if EMA18 crossed above EMA50 in the last trading day
    recent_cross = df.iloc[-1]['EMA18'] > df.iloc[-1]['EMA50'] and df.iloc[-2]['EMA18'] < df.iloc[-2]['EMA50']

    return recent_cross


def process_ema(stock):
    """
    Process a single stock: fetch its data, add EMA, and check EMA crossing.
    """
    try:
        # Get DataFrame for each stock from 1st Jan 2018
        price_chart_df = get_stock_price(stock, "2018-01-01", "2023-09-29")

        # Add EMA
        add_EMA_to_df(price_chart_df)

        # Filter out crossings
        if check_EMA_crossing(price_chart_df):
            return stock
    except Exception as e:
        return None


if __name__ == "__main__":

    # Example usage
    genm_data = get_stock_price('GENM', "2000-01-01", "2023-09-29")
    add_EMA_to_df(genm_data)
    print(genm_data)







