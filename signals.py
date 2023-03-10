import math
import os
import random
from datetime import datetime, timedelta
from logging import info
from time import sleep, time

import numpy
import pandas as pd
import requests
from algorithms.ma_candlestick_drop import ma_candlestick_drop
from algorithms.ma_candlestick_jump import ma_candlestick_jump
from apis import BinbotApi
from autotrade import process_autotrade_restrictions
from binance import AsyncClient, BinanceSocketManager
from scipy import stats
from telegram_bot import TelegramBot
from utils import handle_binance_errors, round_numbers


class SetupSignals(BinbotApi):
    def __init__(self):
        self.interval = "15m"
        self.markets_streams = None
        self.skipped_fiat_currencies = [
            "DOWN",
            "UP",
            "AUD",
        ]  # on top of blacklist
        self.telegram_bot = TelegramBot()
        self.max_request = 950  # Avoid HTTP 411 error by separating streams
        self.active_symbols = []
        self.active_test_bots = []
        self.blacklist_data = []
        self.test_autotrade_settings = {}
        self.settings = {}

    def _send_msg(self, msg):
        """
        Send message with telegram bot
        To avoid Conflict - duplicate Bot error
        /t command will still be available in telegram bot
        """
        if not hasattr(self.telegram_bot, "updater"):
            self.telegram_bot.run_bot()

        self.telegram_bot.send_msg(msg)
        return

    def blacklist_coin(self, pair, msg):
        res = requests.post(
            url=self.bb_blacklist_url, json={"pair": pair, "reason": msg}
        )
        result = handle_binance_errors(res)
        return result

    def load_data(self):
        """
        Load controller data

        - Global settings for autotrade
        - Updated blacklist
        """
        info("Loading controller and blacklist data...")
        if self.settings and self.test_autotrade_settings:
            info("Settings and Test autotrade settings already loaded, skipping...")
            return

        settings_res = requests.get(url=f"{self.bb_autotrade_settings_url}")
        settings_data = handle_binance_errors(settings_res)
        blacklist_res = requests.get(url=f"{self.bb_blacklist_url}")
        blacklist_data = handle_binance_errors(blacklist_res)

        # Show webscket errors
        if "error" in (settings_data, blacklist_res) and (
            settings_data["error"] == 1 or blacklist_res["error"] == 1
        ):
            print(settings_data)

        # Remove restart flag, as we are already restarting
        if (
            "update_required" not in settings_data
            or settings_data["data"]["update_required"]
        ):
            settings_data["data"]["update_required"] = False
            research_controller_res = requests.put(
                url=self.bb_autotrade_settings_url, json=settings_data["data"]
            )
            handle_binance_errors(research_controller_res)

        # Logic for autotrade
        research_controller_res = requests.get(url=self.bb_autotrade_settings_url)
        research_controller = handle_binance_errors(research_controller_res)
        self.settings = research_controller["data"]

        test_autotrade_settings = requests.get(url=f"{self.bb_test_autotrade_url}")
        test_autotrade = handle_binance_errors(test_autotrade_settings)
        self.test_autotrade_settings = test_autotrade["data"]

        self.settings = settings_data["data"]
        self.blacklist_data = blacklist_data["data"]
        self.interval = self.settings["candlestick_interval"]
        self.max_request = int(self.settings["max_request"])

        # if autrotrade enabled and it's not an already active bot
        # this avoids running too many useless bots
        # Temporarily restricting to 1 bot for low funds
        bots_res = requests.get(
            url=self.bb_bot_url, params={"status": "active", "no_cooldown": True}
        )
        active_bots = handle_binance_errors(bots_res)["data"]
        self.active_symbols = [bot["pair"] for bot in active_bots]

        paper_trading_bots_res = requests.get(
            url=self.bb_test_bot_url, params={"status": "active", "no_cooldown": True}
        )
        paper_trading_bots = handle_binance_errors(paper_trading_bots_res)
        self.active_test_bots = [item["pair"] for item in paper_trading_bots["data"]]
        pass

    def post_error(self, msg):
        res = requests.put(
            url=self.bb_autotrade_settings_url, json={"system_logs": msg}
        )
        handle_binance_errors(res)
        return

    def reached_max_active_autobots(self, db_collection_name: str) -> bool:
        """
        Check max `max_active_autotrade_bots` in controller settings

        Args:
        - db_collection_name: Database collection name ["paper_trading", "bots"]

        If total active bots > settings.max_active_autotrade_bots
        do not open more bots. There are two reasons for this:
        - In the case of test bots, infininately opening bots will open hundreds of bots
        which will drain memory and downgrade server performance
        - In the case of real bots, opening too many bots could drain all funds
        in bots that are actually not useful or not profitable. Some funds
        need to be left for Safety orders
        """
        if db_collection_name == "paper_trading":
            if not self.test_autotrade_settings:
                self.load_data()

            active_bots_res = requests.get(
                url=self.bb_test_bot_url, params={"status": "active"}
            )
            active_bots = handle_binance_errors(active_bots_res)
            active_count = len(active_bots["data"])
            if active_count > self.test_autotrade_settings["max_active_autotrade_bots"]:
                return True

        if db_collection_name == "bots":
            if not self.settings:
                self.load_data()
            active_bots_res = requests.get(
                url=self.bb_bot_url, params={"status": "active"}
            )
            active_bots = handle_binance_errors(active_bots_res)
            active_count = len(active_bots["data"])
            if active_count > self.settings["max_active_autotrade_bots"]:
                return True

        return False


class ResearchSignals(SetupSignals):
    def __init__(self):
        info("Started research signals")
        self.last_processed_kline = {}
        self.market_analyses_timestamp = datetime.now()
        self.market_trend = None
        super().__init__()

    def new_tokens(self, projects) -> list:
        check_new_coin = (
            lambda coin_trade_time: (
                datetime.now() - datetime.fromtimestamp(coin_trade_time)
            ).days
            < 1
        )

        new_pairs = [
            item["rebaseCoin"] + item["asset"]
            for item in projects["data"]["completed"]["list"]
            if check_new_coin(int(item["coinTradeTime"]) / 1000)
        ]

        return new_pairs

    async def setup_client(self):
        client = await AsyncClient.create(
            os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"]
        )
        socket = BinanceSocketManager(client)
        return socket

    async def _run_streams(self, params, index):
        socket = await self.setup_client()
        klines = socket.multiplex_socket(params)
        async with klines as k:
            while True:
                res = await k.recv()

                if "result" in res:
                    print(f'Subscriptions: {res["result"]}')

                if "data" in res:
                    if "e" in res["data"] and res["data"]["e"] == "kline":
                        self.process_kline_stream(res["data"])
                    else:
                        print(f'Error: {res["data"]}')

    async def start_stream(self):
        self.load_data()
        raw_symbols = self.ticker_price()
        if not raw_symbols:
            print("No symbols provided by ticket_price", raw_symbols)

        black_list = [x["pair"] for x in self.blacklist_data]
        markets = set(
            [
                item["symbol"]
                for item in raw_symbols
                if item["symbol"].endswith(self.settings["balance_to_use"])
            ]
        )
        subtract_list = set(black_list)
        list_markets = markets - subtract_list
        # Optimal setting below setting greatly reduces the websocket load
        # To make it faster to scan and reduce chances of being blocked by Binance
        if self.settings and self.settings["balance_to_use"] != "GBP":
            list_markets = [
                item for item in list_markets if self.settings["balance_to_use"] in item
            ]

        params = []
        for market in list_markets:
            params.append(f"{market.lower()}@kline_{self.interval}")

        total_threads = math.floor(len(list_markets) / self.max_request) + (
            1 if len(list_markets) % self.max_request > 0 else 0
        )
        # It's not possible to have websockets with more 950 pairs
        # So set default to max 950
        stream = params[:950]

        if total_threads > 1 or not self.max_request:
            for index in range(total_threads - 1):
                stream = params[(self.max_request + 1) :]
                if index == 0:
                    stream = params[: self.max_request]
                await self._run_streams(stream, index)
        else:
            await self._run_streams(stream, 1)

    def market_analyses(self):
        """
        Use gainers and losers endpoint to analyze market trends

        We want to know when it's more suitable to do long positions
        when it's more suitable to do short positions
        For now setting threshold to 70% i.e.
        if > 70% of assets in a given market (USDT) are uptrend
        if < 70% of assets in a given market are downtrend
        Establish the timing
        """
        data = self.gainers_a_losers()
        gainers = 0
        losers = 0
        for item in data["data"]:
            if float(item["priceChangePercent"]) > 0:
                gainers += 1
            elif float(item["priceChangePercent"]) == 0:
                continue
            else:
                losers += 1

        total = gainers + losers
        perc_gainers = (gainers / total) * 100
        perc_losers = (losers / total) * 100

        if perc_gainers > 70:
            self.market_trend = "gainers"
            return

        if perc_losers > 70:
            self.market_trend = "losers"
            return

        self.market_trend = None
        return

    def process_kline_stream(self, result):
        """
        Updates market data in DB for research
        """
        # Sleep 1 hour because of snapshot account request weight
        if datetime.now().time().hour == 0 and datetime.now().time().minute == 0:
            sleep(3600)

        symbol = result["k"]["s"]
        if (
            symbol
            and "k" in result
            and "s" in result["k"]
            and symbol not in self.active_symbols
            and symbol not in self.last_processed_kline
        ):
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            data = self._get_candlestick(symbol, self.interval, stats=True)

            df = pd.DataFrame(
                {
                    "date": data["trace"][0]["x"],
                    "close": numpy.array(data["trace"][0]["close"]).astype(float),
                }
            )
            slope, intercept, rvalue, pvalue, stderr = stats.linregress(
                df["date"], df["close"]
            )

            if "error" in data and data["error"] == 1:
                return

            ma_100 = data["trace"][1]["y"]
            ma_25 = data["trace"][2]["y"]
            ma_7 = data["trace"][3]["y"]

            if len(ma_100) == 0:
                msg = f"Not enough ma_100 data: {symbol}"
                print(msg)
                return

            # Average amplitude
            msg = None
            list_prices = numpy.array(data["trace"][0]["close"])
            sd = round_numbers((numpy.std(list_prices.astype(numpy.single))), 2)

            # historical lowest for short_buy_price
            lowest_price = numpy.min(
                numpy.array(data["trace"][0]["close"]).astype(numpy.single)
            )

            if self.market_trend == "gainers":
                ma_candlestick_jump(
                    self,
                    close_price,
                    open_price,
                    ma_7,
                    ma_100,
                    ma_25,
                    symbol,
                    sd,
                    self._send_msg,
                    process_autotrade_restrictions,
                    lowest_price,
                    slope=slope,
                    p_value=pvalue,
                    r_value=rvalue,
                )

            if self.market_trend == "losers":
                ma_candlestick_drop(
                    self,
                    close_price,
                    open_price,
                    ma_7,
                    ma_100,
                    ma_25,
                    symbol,
                    sd,
                    self._send_msg,
                    process_autotrade_restrictions,
                    lowest_price,
                    slope=slope,
                    p_value=pvalue,
                    r_value=rvalue,
                )

            if datetime.now() >= self.market_analyses_timestamp:
                self.market_analyses()
                print(
                    f"[{datetime.now()}] Current USDT market trend is: {self.market_trend}"
                )
                self._send_msg(
                    f"[{datetime.now()}] Current USDT market #trend is dominated by {self.market_trend}"
                )
                self.market_analyses_timestamp = datetime.now() + timedelta(minutes=15)

            self.last_processed_kline[symbol] = time()

        # If more than 6 hours passed has passed
        # Then we should resume sending signals for given symbol
        if (
            symbol in self.last_processed_kline
            and (float(time()) - float(self.last_processed_kline[symbol])) > 6000
        ):
            del self.last_processed_kline[symbol]
        pass
