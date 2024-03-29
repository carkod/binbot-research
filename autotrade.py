import copy
import math
import logging
import requests

from datetime import datetime
from enums import Strategy
from apis import BinbotApi
from utils import InvalidSymbol, handle_binance_errors, round_numbers, supress_notation

class AutotradeError(Exception):
    def __init__(self, message) -> None:
        self.message = message
    pass


class Autotrade(BinbotApi):
    def __init__(
        self, pair, settings, algorithm_name, db_collection_name="paper_trading"
    ) -> None:
        """
        Initialize automatic bot trading.
        This hits the same endpoints as the UI terminal.binbot dashboard,
        but it's triggered by signals

        There are two types of autotrade: autotrade and test_autotrade. The test_autotrade uses
        the paper_trading db collection and it doesn't use real quantities.

        Args:
        settings: autotrade/test_autotrade settings
        algorithm_name: usually the filename
        db_collection_name: Mongodb collection name ["paper_trading", "bots"]
        """
        self.pair = pair
        self.settings = settings # both settings and test_settings
        self.decimals = self.price_precision(pair)
        current_date = datetime.now().strftime("%Y-%m-%dT%H:%M")
        self.algorithm_name = algorithm_name
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": f"{algorithm_name}_{current_date}",
            "mode": "autotrade",
            "balance_size_to_use": settings["balance_size_to_use"],
            "balance_to_use": settings["balance_to_use"],
            "base_order_size": settings["base_order_size"],
            "candlestick_interval": settings["candlestick_interval"],
            "take_profit": settings["take_profit"],
            "trailling": settings["trailling"],
            "trailling_deviation": settings["trailling_deviation"],
            "trailling_profit": 0, # Trailling activation (first take profit hit)
            "orders": [],
            "stop_loss": settings["stop_loss"],
            "safety_orders": [],
            "strategy": settings["strategy"],
            "short_buy_price": 0,
            "short_sell_price": 0,
            "errors": [],
            "dynamic_trailling": False
        }
        self.db_collection_name = db_collection_name
        self.blacklist: list | None = None
        blacklist_res = self.get_blacklist()
        if not "error" in blacklist_res:
            self.blacklist = blacklist_res["data"]

    def _set_bollinguer_spreads(self, kwargs):
        if "spread" in kwargs and kwargs["spread"]:
            band_1 = kwargs["spread"]["band_1"]
            band_2 = kwargs["spread"]["band_2"]

            self.default_bot["take_profit"] = band_1 * 100
            self.default_bot["stop_loss"] = (band_1 + band_2)
            self.default_bot["trailling"] = True
            self.default_bot["trailling_deviation"] = band_1 * 100

    def handle_error(self, msg):
        """
        Submit errors to event logs of the bot
        """
        try:
            self.settings["system_logs"].append(msg)
        except AttributeError:
            self.settings["system_logs"] = []
            self.settings["system_logs"].append(msg)

        res = requests.put(url=self.bb_autotrade_settings_url, json=self.settings)
        result = handle_binance_errors(res)
        return result

    def submit_bot_event_logs(self, bot_id, message):
        res = requests.post(url=f"{self.bb_submit_errors}/{bot_id}", json=message)
        return res

    def add_to_blacklist(self, symbol, reason=None):
        data = {"symbol": symbol, "reason": reason}
        res = requests.post(url=self.bb_blacklist_url, json=data)
        result = handle_binance_errors(res)
        return result

    def clean_margin_short(self, pair):
        """
        Liquidate and disable margin_short trades
        """
        res = requests.get(url=f'{self.bb_liquidation_url}/{pair}')
        result = handle_binance_errors(res)
        return result
    
    def delete_bot(self, bot_id):
        res = requests.delete(url=f"{self.bb_bot_url}", params={"id": bot_id})
        result = handle_binance_errors(res)
        return result

    def set_margin_short_values(self, kwargs):
        """
        Set up values for margin_short
        this overrides the settings in research_controller autotrade settings
        """

        # Binances forces isolated pair to go through 24hr deactivation after traded
        self.default_bot["cooldown"] = 1440
        self.default_bot["margin_short_reversal"] = True

        self._set_bollinguer_spreads(**kwargs)

        # Override for top_gainers_drop
        if self.algorithm_name == "top_gainers_drop":
            self.default_bot["stop_loss"] = 5
            self.default_bot["trailling_deviation"] = 3.2

        
    def set_bot_values(self, **kwargs):
        """
        Set values for default_bot
        """
        self.default_bot["base_order_size"] = self.settings["base_order_size"]
        self.default_bot[
            "balance_to_use"
        ] = "USDT"  # For now we are always using USDT. Safest and most coins/tokens
        self.default_bot["cooldown"] = 360 # Avoid cannibalization of profits
        self.default_bot["margin_short_reversal"] = True

        self._set_bollinguer_spreads(kwargs)
            

    def handle_price_drops(
        self,
        balances,
        price,
        per_deviation=1.2,
        exp_increase=1.2,
        total_num_so=3,
        trend="upward",  # ["upward", "downward"] Upward trend is for candlestick_jumps and similar algorithms. Downward trend is for panic sells in the market
        lowest_price=0,
        sd=0,
    ):
        """
        Sets the values for safety orders, short sell prices to hedge from drops in price.

        Safety orders here are designed to use qfl for price bounces: prices drop a bit but then overall the trend is bullish
        However short sell uses the short strategy: it sells the asset completely, to buy again after a dip.
        """
        available_balance = next(
            (
                b["free"]
                for b in balances["data"]
                if b["asset"] == self.default_bot["balance_to_use"]
            ),
            None,
        )
        initial_so = 10  # USDT

        if not available_balance:
            print(f"Not enough {self.default_bot['balance_to_use']} for safety orders")
            return

        if trend == "downtrend":
            down_short_buy_spread = total_num_so * (per_deviation / 100)
            down_short_sell_price = round_numbers(price - (price * 0.05))
            down_short_buy_price = round_numbers(
                down_short_sell_price - (down_short_sell_price * down_short_buy_spread)
            )
            self.default_bot["short_sell_price"] = down_short_sell_price

            if lowest_price > 0 and lowest_price <= down_short_buy_price:
                self.default_bot["short_buy_price"] = lowest_price
            else:
                self.default_bot["short_buy_price"] = down_short_buy_price

            # most likely goes down, so no safety orders
            return

        for index in range(total_num_so):
            count = index + 1
            threshold = count * (per_deviation / 100)

            if index > 0:
                price = self.default_bot["safety_orders"][index - 1]["buy_price"]

            buy_price = round_numbers(price - (price * threshold))
            so_size = round_numbers(initial_so**exp_increase)
            initial_so = copy.copy(so_size)

            if count == total_num_so:
                # Increases price diff between short_sell_price and short_buy_price
                short_sell_spread = 0.05
                short_buy_spread = threshold
                short_sell_price = round_numbers(price - (price * threshold))
                short_buy_price = round_numbers(
                    short_sell_price - (short_sell_price * threshold)
                )

                if sd >= 0 and lowest_price > 0:
                    sd_buy_price = round_numbers(short_sell_price - (sd * 2))
                    if lowest_price < sd_buy_price or sd == 0:
                        short_buy_price = lowest_price
                    else:
                        short_buy_price = sd_buy_price

                self.default_bot["short_sell_price"] = short_sell_price
                self.default_bot["short_buy_price"] = short_buy_price
            else:
                self.default_bot["safety_orders"].append(
                    {
                        "name": f"so_{count}",
                        "status": 0,
                        "buy_price": float(buy_price),
                        "so_size": float(so_size),
                        "so_asset": "USDT",
                        "errors": [],
                        "total_commission": 0,
                    }
                )
        return
    
    def set_paper_trading_values(self, balances, qty):

        self.default_bot["base_order_size"] = "15"  # min USDT order = 15
        # Get balance that match the pair
        # Check that we have minimum binance required qty to trade
        for b in balances["data"]:
            if self.pair.endswith(b["asset"]):
                qty = supress_notation(b["free"], self.decimals)
                if self.min_amount_check(self.pair, qty):
                    # balance_size_to_use = 0.0 means "Use all balance". float(0) = 0.0
                    if float(self.default_bot["balance_size_to_use"]) != 0.0:
                        if b["free"] < float(
                            self.default_bot["balance_size_to_use"]
                        ):
                            # Display warning and continue with full balance
                            print(
                                f"Error: balance ({qty}) is less than balance_size_to_use ({float(self.default_bot['balance_size_to_use'])}). Autotrade will use all balance"
                            )
                        else:
                            qty = float(self.default_bot["balance_size_to_use"])

                    self.default_bot["base_order_size"] = qty
                    break
            # If we have GBP we can trade anything
            # And we have roughly the min BTC equivalent amount
            if (
                self.settings["balance_to_use"] == "GBP"
                and b["asset"] == "GBP"
                # Trading with less than 40 GBP will not be profitable
                and float(b["free"]) > 40
            ):
                base_asset = self.find_quoteAsset(self.pair)
                # e.g. XRPBTC
                if base_asset == "GBP":
                    self.default_bot["base_order_size"] = b["free"]
                    break
                try:
                    rate = self.ticker_price(f"{base_asset}GBP")
                except InvalidSymbol:
                    msg = f"Cannot trade {self.pair} with GBP. Adding to blacklist"
                    self.handle_error(msg)
                    self.add_to_blacklist(self.pair, msg)
                    print(msg)
                    return

                rate = rate["price"]
                qty = supress_notation(b["free"], self.decimals)
                # Round down to 6 numbers to avoid not enough funds
                base_order_size = (
                    math.floor((float(qty) / float(rate)) * 10000000) / 10000000
                )
                self.default_bot["base_order_size"] = supress_notation(
                    base_order_size, self.decimals
                )
                pass

    def activate_autotrade(self, **kwargs):
        """
        Run autotrade
        2. Create bot with given parameters from research_controller
        3. Activate bot
        """
        logging.info(f"{self.db_collection_name} Autotrade running with {self.pair}...")
        if self.blacklist:
            for item in self.blacklist:
                if item["pair"] == self.pair:
                    logging.info(f"Pair {self.pair} is blacklisted")
                    return
            
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)
        balances = handle_binance_errors(res)
        qty = 0
        self.default_bot["strategy"] = self.settings["strategy"]

        if "trend" in kwargs:
            if kwargs["trend"] == "downtrend":
                self.default_bot["strategy"] = Strategy.margin_short
                # self.default_bot["close_condition"] = CloseConditions.market_reversal
            else:
                self.default_bot["strategy"] = Strategy.long

        if self.db_collection_name == "paper_trading":
            # Dynamic switch to real bot URLs
            bot_url = self.bb_test_bot_url
            activate_url = self.bb_activate_test_bot_url

            if self.default_bot["strategy"] == "margin_short":
                self.set_margin_short_values(**kwargs)
                pass
            else:
                self.set_paper_trading_values(balances, qty)
                pass
            
        # Can't get balance qty, because balance = 0 if real bot is trading
        # Base order set to default 1 to avoid errors
        # and because there is no matching engine endpoint to get market qty
        # So deal base_order should update this to the correct amount
        if self.db_collection_name == "bots":
            bot_url = self.bb_bot_url
            activate_url = self.bb_activate_bot_url

            if self.default_bot["strategy"] == "margin_short":
                ticker = self.ticker_price(self.default_bot["pair"])
                initial_price = ticker["price"]
                estimate_qty = float(self.default_bot["base_order_size"]) / float(initial_price)
                stop_loss_price_inc = (float(initial_price) * (1 + (self.default_bot["stop_loss"] / 100)))
                # transfer quantity required to cover losses
                transfer_qty = stop_loss_price_inc * estimate_qty
                balances = self.balance_estimate()
                if balances < transfer_qty:
                    logging.error(f"Not enough funds to autotrade margin_short bot. Unable to cover potential losses. balances: {balances}. transfer qty: {transfer_qty}")
                    return
                self.set_margin_short_values(**kwargs)
                pass
            else:
                self.set_bot_values(**kwargs)
                pass

        # Create bot
        create_bot_res = requests.post(url=bot_url, json=self.default_bot)
        create_bot = handle_binance_errors(create_bot_res)

        if "error" in create_bot and create_bot["error"] == 1:
            print(
                f"Autotrade: {create_bot['message']}",
                f"Pair: {self.pair}.",
            )
            return

        # Activate bot
        botId = create_bot["botId"]
        res = requests.get(url=f"{activate_url}/{botId}")
        bot = res.json()

        if "error" in bot and bot["error"] > 0:
            # Failed to activate bot so: 
            # (1) Add to blacklist/exclude from future autotrades
            # (2) Submit error to event logs
            # (3) Delete inactive bot
            # this prevents cluttering UI with loads of useless bots
            message = bot["message"]
            self.submit_bot_event_logs(botId, message)
            self.blacklist.append(self.default_bot["pair"])
            if self.default_bot["strategy"] == "margin_short":
                self.clean_margin_short(self.default_bot["pair"])
            self.delete_bot(botId)
            raise AutotradeError(message)

        else:
            message = f"Succesful {self.db_collection_name} autotrade, opened with {self.pair}!"
            self.submit_bot_event_logs(botId, message)
