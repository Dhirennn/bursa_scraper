# Stock Screening Tool / BURSA Malaysia stock scraper

A powerful tool designed to screen stocks based on Exponential Moving Average (EMA) criteria. It fetches stock data, calculates EMA values, and identifies potential buy/sell signals.

**NOTE: THIS SCRAPER/SCREENER IS STILL IN ITS INFANCY STAGE, MORE FEATURES TO BE ADDED IN THE FUTURE!
Feel free to make any pull requests.**

## 🌟 Features

- **Data Retrieval**: Scrapes stock data from various sources like `i3investor.com` and `malaysiastock.biz`.
- **EMA Calculation**: Computes Exponential Moving Average values for stock data.
- **Parallel Processing**: Uses concurrent processing to analyze multiple stocks simultaneously, ensuring efficient performance.
- **Screening Criteria**: Filters stocks based on specific EMA criteria to identify potential buy signals.

## 🛠 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Dhirennn/bursa_scraper.git
   ```
2. Navigate to the project directory:
   ```bash
   cd bursa_scraper
   ```
3. Install required packages (it's recommended to use a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

1. Run the main script:
   ```bash
   python scraper.py
   ```
   
2. The script will fetch stock data, compute EMA values, and display stocks that meet the screening criteria.

## 🗺 Using `ticker_map.txt`
### NOTE: IF ALL YOU WANT IS A MAPPING OF THE TICKER (e.g: GENM) TO STOCK CODE (e.g: 4715), then just download this file and use it.

The `ticker_map.txt` file is essential for mapping stock tickers on BURSA Malaysia to their respective stock codes. This mapping ensures that the correct stock data is fetched from Yahoo Finance using the `yfinance` library.

### Structure:

The file has a simple structure where each line represents a mapping:
   ```bash
   TICKER : STOCK_CODE
   For example:
   GENM = 4715
   ```

### Updating the Ticker Map:

Over time, as new stocks are listed or delisted, or their codes change, you might need to update the `ticker_map.txt`:

1. Use the `update_tickers_number` function from the scraper module to fetch the latest ticker-to-stock code mappings.
2. This function will automatically update the `ticker_map.txt` file in the `data` directory.

### Note:

You do not have to update the `ticker_map.txt` file every single time as it will remain mostly the same.

Besides that, there are some tickers where their stock code is `4715` in `ticker_map.txt`, this is just the default
value because of my RegEx not working for every single scrape. There are only a few tickers affected, which I've manually modified to represent
the actual stock code. This .txt file can be found in `data/ticker_map.txt`. If you use `update_tickers_number`, you might need to go through
the file manually and fix the codes manually for affected stocks (Manually CTRL+F for 4715 and change them accordingly). 



## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📜 License

[MIT](https://github.com/Dhirennn/bursa_scraper/blob/main/LICENSE)










