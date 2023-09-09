import os


def top_gainers_drop(
    self,
    close_price,
    open_price,
    ma_7,
    ma_100,
    ma_25,
    symbol,
    sd,
    _send_msg,
    run_autotrade,
    lowest_price,
    slope,
    btc_correlation
):
    """
    From the list of USDT top gainers
    pick the first 4, expect them to drop at some point
    so create margin_short bot

    """
    if (
        float(close_price) < float(open_price)
        and btc_correlation["close_price"] < 0.5
        and symbol in self.top_coins_gainers
    ):

        msg = (f"""
- [{os.getenv('ENV')}] Top gainers's drop <strong>#top_gainers_drop algorithm</strong> #{symbol}
- Current price: {close_price}
- SD {sd}
- Percentage volatility: {(sd) / float(close_price)}
- Percentage volatility x2: {sd * 2 / float(close_price)}
- Slope: {slope}
- Pearson correlation with BTC: {btc_correlation["close_price"]}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        _send_msg(msg)
        print(msg)

        run_autotrade(self, symbol, "top_gainers_drop", False, **{"sd": sd, "current_price": close_price, "lowest_price": lowest_price, "trend": "downtrend"})

    return
