import os

def price_rise_15(
    self,
    close_price,
    symbol,
    run_autotrade,
    prev_price,
    p_value,
    r_value,
    btc_correlation
):
    """
    Price increase/decrease algorithm

    https://www.binance.com/en/support/faq/understanding-top-movers-statuses-on-binance-spot-trading-18c97e8ab67a4e1b824edd590cae9f16
    """
    
    algo = "price_rise_15_rally_pullback"
    price_diff = (float(close_price) - float(prev_price)) / close_price

    if 0.07 <= price_diff < 0.11:
        first_line = "<strong>Price increase</strong> over 7%"

    elif -0.07 <= price_diff < -0.11 :
        first_line = "<strong>Price decrease #algorithm</strong> over 7%"

    else:
        return
    
    if self.market_domination_trend == "losers":
        trend = "downtrend"
    else:
        trend = "uptrend"

    msg = (f"""
- [{os.getenv('ENV')}] {first_line} #{symbol}
- Current price: {close_price}
- Standard deviation: {self.sd}, Log volatility (log SD): {self.volatility}
- P-value: {p_value}
- Pearson correlation with BTC: {btc_correlation["close_price"]}
- BTC 24hr change: {self.btc_change_perc}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
    self.send_telegram(msg)

    self.process_autotrade_restrictions(symbol, "rally_pullback", False, **{"sd": self.sd, "current_price": close_price, "trend": trend})
    return
