import os


def ma_candlestick_drop(
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
    p_value,
    btc_correlation
):
    """
    Opposite algorithm of ma_candletick_jump
    This algorithm detects Candlesticks that are in a downard trending motion for several periods

    Suitable for margin short trading (borrow - margin sell - buy back - repay)
    """
    if (
        float(close_price) < float(open_price)
        and sd > 0.09
        and close_price < ma_7[len(ma_7) - 1]
        and open_price < ma_7[len(ma_7) - 1]
        and close_price < ma_25[len(ma_25) - 1]
        and open_price < ma_25[len(ma_25) - 1]
        and ma_7[len(ma_7) - 1] < ma_7[len(ma_7) - 2]
        and close_price < ma_7[len(ma_7) - 2]
        and open_price < ma_7[len(ma_7) - 2]
        and close_price < ma_100[len(ma_100) - 1]
        and open_price < ma_100[len(ma_100) - 1]
        # remove high standard deviation
        and float(sd) / float(close_price) < 0.07
    ):

        msg = (f"""
- [{os.getenv('ENV')}] Candlestick <strong>#drop algorithm</strong> #{symbol}
- Current price: {close_price}
- SD {sd}
- Percentage volatility: {(sd) / float(close_price)}
- Percentage volatility x2: {sd * 2 / float(close_price)}
- Slope: {slope}
- P-value: {p_value}
- Pearson correlation with BTC: {btc_correlation["close_price"]}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        _send_msg(msg)
        print(msg)
        trend = "uptrend" if slope > 0 else "downtrend"

        run_autotrade(self, symbol, "ma_candlestick_drop", False, **{"sd": sd, "current_price": close_price, "lowest_price": lowest_price, "trend": "uptrend"})

    return
