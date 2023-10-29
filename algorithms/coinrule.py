import os

def fast_and_slow_macd(
    self,
    close_price,
    symbol,
    macd,
    macd_signal,
    ma_7,
    ma_25,
    _send_msg,
    run_autotrade,
):
    """
    Coinrule top performance rule
    https://web.coinrule.com/share-rule/Fast-EMA-above-Slow-EMA-with-MACD-6f8653

    """

    if macd[str(len(macd) - 1)] > macd_signal[str(len(macd_signal) - 1)] and ma_7[len(ma_7) - 1] > ma_25[len(ma_25) - 1]:
        
        msg = (f"""
- [{os.getenv('ENV')}] Coinrule <strong>fast_and_slow_macd #algorithm</strong> #{symbol}
- Current price: {close_price}
- BTC 24hr change: {self.btc_change_perc}
- Trend: None
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        _send_msg(msg)
        # run_autotrade(self, symbol, "rally_pullback", False, **{"sd": sd, "current_price": close_price, "lowest_price": lowest_price, "trend": trend})

    pass