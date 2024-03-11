import os
from utils import define_strategy, round_numbers

def ma_candlestick_jump(
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
    btc_correlation,
):
    """
    Candlesticks are in an upward trending motion for several periods
    This algorithm checks last close prices > MAs to decide whether to trade

    Intercept: the larger the value, the higher the potential for growth
        e.g. Given predictor y = 0.123x + 2.5, for x = 1, y = 0.123 + 2.5 = 2.623
             Given predictor y = 0.123x + 10, for x = 1, y = 0.123 + 10 = 10.123

    Chaikin_diff: positive values indicate overbought, negative values indicate oversold
    - Buy when oversold, sell when overbought

    SD: standard deviation of 0.006 seems to be a good threshold after monitoring signals,
    whereas it is possible to get around 3% increase to actually make a profit
    """
    if (
        float(close_price) > float(open_price)
        and sd > 0.09
        and close_price > ma_7[len(ma_7) - 1]
        and open_price > ma_7[len(ma_7) - 1]
        and close_price > ma_25[len(ma_25) - 1]
        and open_price > ma_25[len(ma_25) - 1]
        and ma_7[len(ma_7) - 1] > ma_7[len(ma_7) - 2]
        and close_price > ma_7[len(ma_7) - 2]
        and open_price > ma_7[len(ma_7) - 2]
        and close_price > ma_100[len(ma_100) - 1]
        and open_price > ma_100[len(ma_100) - 1]
    ):

        trend = define_strategy(self)
        if not trend:
            return
        
        msg = (f"""
- [{os.getenv('ENV')}] Candlestick <strong>#jump algorithm</strong> #{symbol}
- Current price: {close_price}
- %threshold based on volatility: {round_numbers(self.volatility * 100, 6)}%
- SD {sd}
- Percentage volatility: {(sd) / float(close_price)}
- Percentage volatility x2: {sd * 2 / float(close_price)}
- Slope: {slope}
- P-value: {p_value}
- Pearson correlation with BTC: {btc_correlation["close_price"]}
- Trend: {trend}
- Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
- BTC 24hr change: {self.btc_change_perc}
- https://www.binance.com/en/trade/{symbol}
- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
""")
        _send_msg(msg)
        run_autotrade(self, symbol, "ma_candlestick_jump", False, **{"sd": sd, "current_price": close_price, "lowest_price": lowest_price, "trend": trend })

    return
