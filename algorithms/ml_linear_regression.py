from sklearn.linear_model import LinearRegression
import requests
import os

def ml_linear_regression(self,
    symbol,
    close_price,
    data,
    ma_7,
    ma_100,
    ma_25
):
    algo = "ml_linear_regression"
    candlestick = data["trace"]
    # Extract features (X) and target variable (y)
    X = [float(candlestick[2]), float(candlestick[3]), float(candlestick[4]), float(candlestick[5])]
    y = float(candlestick[1])

    # Train linear regression model
    model = LinearRegression()
    model.fit(X, y)

    # Get coefficients and intercept
    coefficients = model.coef_
    intercept = model.intercept_

    msg = (f"""
        - [{os.getenv('ENV')}] <strong>{algo} #algorithm</strong> #{symbol} 
        - Current price: {close_price}
        - Standard deviation: {self.sd}, Log volatility (log SD): {self.volatility}%
        - Linear regression: coefficients {coefficients}x + {intercept}
        - BTC 24hr change: {self.btc_change_perc}
        - Reversal? {"No reversal" if not self.market_domination_reversal else "Positive" if self.market_domination_reversal else "Negative"}
        - <a href='https://www.binance.com/en/trade/{symbol}'>Binance</a>
        - <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>
        """)

    self.send_telegram(msg)
    # self.process_autotrade_restrictions(symbol, algo, False, **{ "current_price": close_price})
