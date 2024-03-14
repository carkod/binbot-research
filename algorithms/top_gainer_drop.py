import os
from utils import define_strategy


def top_gainers_drop(
    self,
    close_price,
    open_price,
    ma_7,
    ma_100,
    ma_25,
    symbol,
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
        
        trend = define_strategy(self)
        if not trend:
            return

        msg = (f"""
- [{os.getenv('ENV')}] Top gainers's drop <strong>#top_gainers_drop algorithm</strong> #{symbol}
- Current price: {close_price}
- Standard deviation: {self.sd}, Log volatility (log SD): {self.volatility}
- Slope: {slope}
- Pearson correlation with BTC: {btc_correlation["close_price"]}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        self.send_telegram(msg)
        self.process_autotrade_restrictions(symbol, "top_gainers_drop", False, **{"sd": self.sd, "current_price": close_price, "lowest_price": lowest_price, "trend": "downtrend"})

    return
