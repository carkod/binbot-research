import os
from utils import define_strategy, round_numbers

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
    algo = "coinrule_fast_and_slow_macd"

    if macd[str(len(macd) - 1)] > macd_signal[str(len(macd_signal) - 1)] and ma_7[len(ma_7) - 1] > ma_25[len(ma_25) - 1]:

        trend = define_strategy(self)
        if trend is None and trend == "uptrend":
            return

        msg = (f"""
        - [{os.getenv('ENV')}] <strong>{algo} #algorithm</strong> #{symbol}
        - Current price: {close_price}
        - %threshold based on volatility: {round_numbers(self.volatility * 100, 6)}%
        - BTC 24hr change: {self.btc_change_perc}
        - Strategy: {trend}
        - Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
        - https://www.binance.com/en/trade/{symbol}
        - <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
        """)
        _send_msg(msg)
        print(msg)
        run_autotrade(self, symbol, algo, False, **{"current_price": close_price, "trend": trend})

    pass


def buy_low_sell_high(
    self,
    close_price,
    symbol,
    rsi,
    ma_25,
    _send_msg,
    run_autotrade,
):
    """
    Coinrule top performance rule
    https://web.coinrule.com/share-rule/Multi-Time-Frame-Buy-Low-Sell-High-Short-term-8f02df
    """

    if rsi[str(len(rsi) - 1)] < 35 and close_price > ma_25[len(ma_25) - 1]:

        trend = define_strategy(self)
        if not trend:
            return
        algo = "coinrule_buy_low_sell_high"
        
        msg = (f"""
- [{os.getenv('ENV')}] <strong>{algo} #algorithm</strong> #{symbol}
- Current price: {close_price}
- %threshold based on volatility: {round_numbers(self.volatility * 100, 6)}%
- BTC 24hr change: {self.btc_change_perc}
- Strategy: {trend}
- Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        _send_msg(msg)
        run_autotrade(self, symbol, algo, False, **{"current_price": close_price, "trend": trend})

    pass
