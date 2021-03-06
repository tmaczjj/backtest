# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
import datetime
import json
from backtest.backtest import ArrayManager
from utils.utils import load_daily_price, load_share_mongo

from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)


class IntraDayTrendStrategy(BackTest):
    """
    set params before tda
    """
    break_volume_base = 300
    stock_price_base = 10
    stock_buy_power = {}
    stock_sell_power = {}
    stop_loss_rate = 3
    traded_list = []
    ordered_code = []
    trade_current_avg_price = trade_last_avg_price = trade_last_before_last_avg_price = 0
    market_time_start = "09:30:10"
    trade_time_start = "09:35:00"
    trade_time_end = "14:56:30"
    market_time_end = "14:56:59"

    def __init__(self, stocklist=None, trade_date=None, cash=1000000, broker=None, enable_stat=True, codeDict=None):
        super().__init__(stocklist, trade_date, cash=cash, broker=broker, enable_stat=enable_stat)
        self.am = {}
        self.stg_data = {}
        self.codeDict = codeDict
        self.stocklist = self.stockFliter(stocklist)

    def initialize(self):
        for stock in self.stocklist:
            self.am[stock] = ArrayManager()
            self.stock_buy_power[stock] = 0
            self.stock_sell_power[stock] = 0
        self.info("Strategy--{}--策略初始化完成".format(self.__class__.__name__))

    def on_tick(self, tick):
        tick_data = self.ctx["tick_data"]
        hold_position = self.ctx["broker"].position
        tick_time = str(tick.strftime("%H:%M:%S"))
        for code, market_data in tick_data.items():
            self.am[code].update(market_data)
            if self.market_time_start < tick_time < self.market_time_end:
                trade_volume = self.am[code].volume
                trade_amount = self.am[code].amount
                if trade_volume[-2] > 0 and trade_volume[-1] > 0:
                    cond_trade_amount = (trade_volume[-1] + trade_volume[-2]) > self.stg_data[code]
                else:
                    cond_trade_amount = False
                # ----------------------------------------------------------------------------------------------------
                # tick价格计算
                self.trade_current_avg_price = self.am[code].tick_vwap[-1]
                self.trade_last_avg_price = self.am[code].tick_vwap[-2]
                self.trade_last_before_last_avg_price = self.am[code].tick_vwap[-3]

                # --------------------------------- Data Static Before Trading --------------------------------- #
                # if tick_time < self.trade_time_start:
                if self.trade_current_avg_price > self.trade_last_avg_price:
                    stock_amount = self.stock_buy_power[code]
                    self.stock_buy_power[code] = trade_amount[-1] + stock_amount

                elif self.trade_current_avg_price < self.trade_last_avg_price:
                    stock_amount = self.stock_sell_power[code]
                    self.stock_sell_power[code] = trade_amount[-1] + stock_amount

                # ---------------------------------------- Start Trading --------------------------------------- #
                if self.trade_time_start < tick_time < self.trade_time_end:
                    vwap = self.am[code].vwap
                    vwap_avg = vwap.mean()
                    # -----------------------------------  卖出  -----------------------------------------#
                    if code in hold_position:
                        buy_power = self.stock_buy_power[code]
                        sell_power = self.stock_sell_power[code]
                        stock_hold_info = hold_position[code][0]
                        hold_num = int(stock_hold_info["shares"])

                        # -----------------------------  盘中止盈 ----------------------------------#
                        # cond5 = self.trade_current_avg_price < self.trade_last_avg_price
                        # cond6 = self.trade_current_avg_price > self.trade_last_avg_price
                        #
                        # if hold_num > 0:
                        #     if cond5 and self.trade_current_avg_price > vwap[-1] >= vwap_avg and cond_trade_amount:
                        #         self.ctx.broker.sell(code, hold_num, round(self.trade_current_avg_price-1, 2), msg="做多平仓")
                        #         return
                        #
                        # if hold_num < 0:
                        #     if cond6 and self.trade_current_avg_price < vwap[-1] <= vwap_avg and cond_trade_amount:
                        #         self.ctx.broker.buytocover(code, abs(hold_num), round(self.trade_current_avg_price+1, 2), msg="做空平仓")
                        #         return

                        # -----------------------------  盘中止损 ----------------------------------#
                        # open_price = stock_hold_info["open_price"]
                        # long_stop_price = open_price * (100 - self.stop_loss_rate) / 100
                        # short_stop_price = open_price * (100 + self.stop_loss_rate) / 100
                        # stop_loss_cond1 = sell_power > buy_power
                        # stop_loss_cond2 = sell_power < buy_power
                        # stop_loss_cond3 = vwap[-1] < vwap[-2] < vwap_avg
                        # stop_loss_cond4 = vwap[-1] > vwap[-2] > vwap_avg
                        #
                        # if hold_num < 0:
                        #     # if self.trade_current_avg_price > short_stop_price and stop_loss_cond2 and stop_loss_cond4:
                        #     if (open_price - self.trade_current_avg_price) * hold_num > 1500:
                        #         self.ctx.broker.buytocover(code, abs(hold_num), round(self.trade_current_avg_price+1, 2), msg="做空止损")
                        #
                        # if hold_num > 0:
                        #     # if self.trade_current_avg_price < long_stop_price and stop_loss_cond2:
                        #     if (open_price - self.trade_current_avg_price) * hold_num > 1500:
                        #         self.ctx.broker.sell(code, hold_num, round(self.trade_current_avg_price-1, 2), msg="做多止损")

                    # -----------------------------------  开仓  -----------------------------------------#
                    if code not in hold_position and code not in self.traded_list:
                        if cond_trade_amount:
                            buy_power = self.stock_buy_power[code]
                            sell_power = self.stock_sell_power[code]
                            trade_amount = int(self.codeDict[code])

                            cond1 = self.trade_current_avg_price > self. trade_last_avg_price > vwap[-1]
                            cond2 = vwap[-1] >= vwap_avg
                            if cond1 and cond2 and buy_power > sell_power:
                                self.ctx.broker.buy(code, trade_amount, round(self.trade_current_avg_price+1, 2), msg="买入开仓")
                                self.traded_list.append(code)

                            cond3 = self.trade_current_avg_price < self.trade_last_avg_price < vwap[-1]
                            cond4 = vwap[-1] <= vwap_avg
                            if cond3 and cond4 and buy_power < sell_power:
                                self.ctx.broker.sellshort(code, trade_amount, round(self.trade_current_avg_price-1, 2), msg="卖出开仓")
                                self.traded_list.append(code)

                if self.trade_time_end < tick_time < self.market_time_end:
                    # -----------------------------  尾盘平仓 ----------------------------------#
                    if code in hold_position:
                        stock_hold_info = hold_position[code][0]
                        hold_num = int(stock_hold_info["shares"])
                        if hold_num < 0:
                            self.ctx.broker.buytocover(code, abs(hold_num), round(self.trade_current_avg_price+1, 2), msg="做空平仓")

                        if hold_num > 0:
                            self.ctx.broker.sell(code, hold_num, round(self.trade_current_avg_price-1, 2), msg="做多平仓")

    def on_deal(self, order):
        pass
        # self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
        #     stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

    def on_order_ok(self, order):
        pass

    def finish(self):
        pass

    def stockFliter(self, stocklist):
        """
        股票筛选模块
        实现每日股票筛选
        若不需要筛选 直接return self.stocklist

        :return:     list:需要交易的股票
        """
        stock_list = self.stocklist
        local_stock_list = [x + ".SH" if x.startswith("6") else x + ".SZ" for x in stock_list]
        daily_price_df = load_daily_price(local_stock_list, self.pre_trade_date)
        df_fliter = daily_price_df[daily_price_df["close"] > self.stock_price_base]
        fliterred_list = list(df_fliter["code"])
        stock_trade_list = [x.split(".", 1)[0] for x in fliterred_list]
        stock_trade_list_final = []
        for stock in stock_trade_list:
            break_point = self.break_volume_cal(stock)
            if break_point >= self.break_volume_base:
                self.stg_data[stock] = int(break_point)
                stock_trade_list_final.append(stock)
        ORDER_FILE_ROUTE = "reporter/stg_data/period_days/" + self.trade_date.strftime("%Y%m%d") + ".json"
        with open(ORDER_FILE_ROUTE, 'w') as f:
            json.dump({self.trade_date.strftime("%Y%m%d"): self.stg_data}, f, indent=4, default=str)
        return stock_trade_list_final

    def break_volume_cal(self, stock):
        import tushare as ts
        # df_yd = ts.get_tick_data(stock, date=self.pre_trade_date_str, src='tt')
        # stock_volume = df_yd["volume"]
        # volume_value = stock_volume.quantile(0.99)
        #本地获取数据
        df_yd = load_share_mongo(stock, self.pre_trade_date)
        if len(df_yd) > 0:
            stock_volume = df_yd["TradeVolume"]
            volume_value = int(stock_volume.quantile(0.99))
        else:
            volume_value = 0
        return volume_value