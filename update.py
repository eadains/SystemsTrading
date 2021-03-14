from data import update_fundamentals, update_prices, update_tickers

if __name__ == "__main__":
    update_tickers()
    print("Tickers updated.")
    update_prices()
    print("Prices updated.")
    update_fundamentals()
    print("Fundamentals updated.")
    