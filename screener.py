from time import time
import concurrent.futures
from scraper import get_stock_list
from exponential_moving_average import process_ema
from tqdm import tqdm





def main():
    start_time = time()

    # get the full stock list
    stock_list = get_stock_list()

    # Use ThreadPoolExecutor to process stocks in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_ema, stock_list), total=len(stock_list)))

    # Filter out None values from results
    screened_list = [stock for stock in results if stock]

    print('Time taken: ', time() - start_time)
    print(
        "These stocks have been filtered based on:\na) EMA18 higher than EMA50 on last trading day\nb) EMA18 is lower than EMA50 on previous day\nc) Stock has more than 50 candles")

    for stock in screened_list:
        print(stock)




if __name__ == "__main__":
    main()