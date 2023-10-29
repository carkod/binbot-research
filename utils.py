import math
import logging

from decimal import Decimal
from time import sleep
from requests import HTTPError, Response


class BinanceErrors(Exception):
    pass

class BinbotError(Exception):
    pass

class InvalidSymbol(BinanceErrors):
    pass

def round_numbers(value, decimals=6):
    decimal_points = 10 ** int(decimals)
    number = float(value)
    result = math.floor(number * decimal_points) / decimal_points
    if decimals == 0:
        result = int(result)
    return result

def supress_notation(num: float, precision: int = 0):
    """
    Supress scientific notation
    e.g. 8e-5 = "0.00008"
    """
    num = float(num)
    if precision >= 0:
        decimal_points = precision
    else:
        decimal_points = Decimal(str(num)).as_tuple().exponent * -1
    return f"{num:.{decimal_points}f}"


def handle_binance_errors(response: Response):
    """
    Handles:
    - HTTP codes, not authorized, rate limits...
    - Bad request errors, binance internal e.g. {"code": -1013, "msg": "Invalid quantity"}
    - Binbot internal errors - bot errors, returns "errored"

    """
    response.raise_for_status()

    if 400 <= response.status_code < 500:
        print(response.status_code, response.url)
        if response.status_code == 418:
            sleep(120)
    
    # Calculate request weights and pause half of the way (1200/2=600)
    if (
        "x-mbx-used-weight-1m" in response.headers
        and int(response.headers["x-mbx-used-weight-1m"]) > 600
    ):
        print("Request weight limit prevention pause, waiting 1 min")
        sleep(120)

    content = response.json()

    try:
        if "code" in content:
            if content["code"] == 200 or content["code"] == "000000":
                return content

            if content["code"] == -1121:
                raise InvalidSymbol("Binance error, invalid symbol")
        
        if "error" in content and content["error"] == 1:
            logging.error(content["message"])

        else:
            return content
    except HTTPError:
        raise HTTPError(content["msg"])

def define_strategy(btc_change, btc_correlation):
    """
    Use BTC percengage change and correlation coin vs BTC
    to decide trend, that is, bot strategy to follow
    long or margin_short
    """
    btc_change = float(btc_change)
    correlation = btc_correlation["close_price"]
    # Strong correlation with BTC
    if btc_change > 0 and correlation > 0.6:
        trend = "uptrend"
    elif btc_change < 0 and correlation > 0.6:
        trend = "downtrend"
    # Weak correlation with BTC, go opposite
    elif btc_change > 0 and correlation < 0.1:
        trend = "downtrend"
    elif btc_change < 0 and correlation < 0.1:
        trend = "uptrend"
    else:
        trend = None

    return trend
