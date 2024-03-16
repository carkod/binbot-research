import os
from utils import define_strategy, bollinguer_spreads


def fast_and_slow_macd(
    self,
    close_price,
    symbol,
    macd,
    macd_signal,
    ma_7,
    ma_25,
    ma_100,
    slope,
    intercept,
    rvalue,
    pvalue,
    stderr,
):
    """
    Coinrule top performance rule
    https://web.coinrule.com/share-rule/Fast-EMA-above-Slow-EMA-with-MACD-6f8653

    """
    algo = "coinrule_fast_and_slow_macd"
    spread = None

    if macd[str(len(macd) - 1)] > macd_signal[str(len(macd_signal) - 1)] and ma_7[len(ma_7) - 1] > ma_25[len(ma_25) - 1]:

        trend = define_strategy(self)
        if trend is None and trend == "uptrend":
            return
        
        # Second stage filtering when volatility is high
        # when volatility is high we assume that
        # difference between MA_7 and MA_25 is wide
        # if this is not the case it may fail to signal correctly
        if self.volatility > 0.8:

            # Calculate spread using bolliguer band MAs
            spread = bollinguer_spreads(ma_100, ma_25, ma_7)


        msg = (f"""
        - [{os.getenv('ENV')}] <strong>{algo} #algorithm</strong> #{symbol} 
        - Current price: {close_price}
        - Standard deviation: {self.sd}, Log volatility (log SD): {self.volatility}%
        - Bollinguer bands spread: {spread['band_1']}, {spread['band_2']}
        - Linear regression: slope {slope}x + {intercept}, correlation {rvalue}, p-value {pvalue}, stderr {stderr}
        - BTC 24hr change: {self.btc_change_perc}
        - Strategy: {trend}
        - Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
        - <a href='https://www.binance.com/en/trade/{symbol}'>Binance</a>
        - <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
        """)
        self.send_telegram(msg)
        self.process_autotrade_restrictions(symbol, algo, False, **{"spread": spread, "current_price": close_price, "trend": trend})

        pass


def buy_low_sell_high(
    self,
    close_price,
    symbol,
    rsi,
    ma_25,
    ma_7,
    ma_100,
):
    """
    Coinrule top performance rule
    https://web.coinrule.com/share-rule/Multi-Time-Frame-Buy-Low-Sell-High-Short-term-8f02df
    """

    if rsi[str(len(rsi) - 1)] < 35 and close_price > ma_25[len(ma_25) - 1]:

        spread = None
        algo = "coinrule_buy_low_sell_high"
        trend = define_strategy(self)

        if not trend:
            return

        # Second stage filtering when volatility is high
        # when volatility is high we assume that
        # difference between MA_7 and MA_25 is wide
        # if this is not the case it may fail to signal correctly
        if self.volatility > 0.8:

            # Calculate spread using bolliguer band MAs
            spread = bollinguer_spreads(ma_100, ma_25, ma_7)
        
        msg = (f"""
- [{os.getenv('ENV')}] <strong>{algo} #algorithm</strong> #{symbol}
- Current price: {close_price}
- Standard deviation: {self.sd}, Log volatility (log SD): {self.volatility}%
- Bollinguer bands spread: {spread['band_1']}, {spread['band_2']}
- BTC 24hr change: {self.btc_change_perc}
- Strategy: {trend}
- Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        self.send_telegram(msg)
        self.process_autotrade_restrictions(symbol, algo, False, **{"spread": spread, "current_price": close_price, "trend": trend})

    pass
