import os

def price_rise_15(
    self,
    close_price,
    symbol,
    sd,
    _send_msg,
    run_autotrade,
    prev_price,
    p_value,
    r_value,
):
    """
    Price increase/decrease algorithm

    https://www.binance.com/en/support/faq/understanding-top-movers-statuses-on-binance-spot-trading-18c97e8ab67a4e1b824edd590cae9f16
    """
    

    price_diff = (float(close_price) - float(prev_price)) / close_price

    if 0.07 <= price_diff < 0.11:
        first_line = "<strong>Price increase</strong> over 7%"

    elif -0.07 <= price_diff < -0.11 :
        first_line = "<strong>Price decrease #algorithm</strong> over 7%"

    else:
        return

    msg = (f"""
- [{os.getenv('ENV')}] {first_line} #{symbol}
- Current price: {close_price}
- Percentage volatility: {(sd) / float(close_price)}
- Percentage volatility x2: {sd * 2 / float(close_price)}
- P-value: {p_value}
- Pearson correlation: {r_value}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
    _send_msg(msg)
    # trend = "uptrend" if slope > 0 else "downtrend"

    # run_autotrade(self, symbol, "rally_pullback", False, **{"sd": sd, "current_price": close_price, "lowest_price": lowest_price, "trend": "uptrend"})


    return
