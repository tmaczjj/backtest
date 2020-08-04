# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
from datetime import datetime
from backtest.backtest import ArrayManager
from utils.utils import load_daily_price, load_share_mongo
from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)


class IntraDayTrendStrategy(BackTest):
    def __init__(self, stocklist=None, trade_date=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, trade_date, cash=cash, broker=broker, enable_stat=enable_stat)
        self.am = {}
        self.stg_data = {}
        self.stock_buy_power = {}
        self.stock_sell_power = {}
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
        # 交易时间设定
        tick_time = str(tick.strftime("%H:%M:%S"))
        market_time_start = "09:30:20"
        trade_time_start = "09:35:00"
        trade_time_end = "14:56:30"
        traded_list = []

        for code, market_data in tick_data.items():
            self.am[code].update(market_data)
            # print("{}:{}".format(tick, code))
            trade_volume = self.am[code].volume
            trade_amount = self.am[code].amount
            vwap = self.am[code].vwap
            trade_current_avg_price = round(trade_amount[-1] / (trade_volume[-1] * 100), 2)
            trade_last_avg_price = round(trade_amount[-2] / (trade_volume[-2] * 100), 2)
            cond_trade_amount = trade_volume[-1] > self.stg_data[code]

            # ----------------------------------- 交易数据统计 ----------------------------------------- #
            if market_time_start < tick_time < trade_time_start:
                if trade_current_avg_price > trade_last_avg_price:
                    stock_amount = self.stock_buy_power[code]
                    self.stock_buy_power[code] = trade_amount[-1] + stock_amount
                elif trade_current_avg_price < trade_last_avg_price:
                    stock_amount = self.stock_sell_power[code]
                    self.stock_sell_power[code] = trade_amount[-1] + stock_amount

            # -----------------------------------  卖出  -----------------------------------------#
            if code in hold_position:
                stock_hold_info = hold_position[code][0]
                trade_price = max(market_data.LastPrice, market_data.BidPrice1, market_data.AskPrice1)

                if trade_time_start < tick_time < trade_time_end:
                    cond3 = self.am[code].last_price[-1] < self.am[code].last_price[-2]
                    # cond4 = vwap[-1] <= vwap[-2]
                    hold_num = int(stock_hold_info["shares"])
                    if hold_num > 0:
                        if cond3 and trade_price > vwap[-1] >= vwap[-2] and cond_trade_amount:
                            self.ctx.broker.sell(code, hold_num, round(trade_price-1, 2), msg="做多平仓")

                    # long_stop_price = open_price * 0.98
                    # short_stop_price = open_price * 1.02
                    # open_price = stock_hold_info["open_price"]
                    # if hold_num < 0:
                    #     if trade_price > short_stop_price:
                    #         self.ctx.broker.buytocover(code, abs(hold_num), round(trade_price+1, 2), msg="做空平仓")
                    #         traded_list.append(code)

                if tick_time >= trade_time_end:
                    hold_num = int(stock_hold_info["shares"])
                    # if hold_num < 0:
                    #     self.ctx.broker.buytocover(code, abs(hold_num), round(trade_price+1, 2), msg="做空平仓")
                    #     traded_list.append(code)
                    if hold_num > 0:
                        self.ctx.broker.sell(code, hold_num, round(trade_price-1, 2), msg="做多平仓")

            # -----------------------------------  买入  -----------------------------------------#
            if trade_time_start < tick_time < trade_time_end:
                if cond_trade_amount:
                    if code not in hold_position and code not in traded_list:
                        buy_power = self.stock_buy_power[code]
                        sell_power = self.stock_buy_power[code]
                        trade_price = max(market_data.LastPrice, market_data.BidPrice1, market_data.AskPrice1)
                        trade_amount = int(round(int(20000 / trade_price) / 100) * 100)
                        cond1 = self.am[code].last_price[-1] > self.am[code].last_price[-2]
                        cond2 = vwap[-1] >= vwap[-2]
                        if cond1 and cond2:
                            self.ctx.broker.buy(code, trade_amount, round(trade_price+1, 2), msg="买入开仓")
                            traded_list.append(code)
                        # cond3 = self.am[code].last_price[-1] < self.am[code].last_price[-2] < vwap[-1]
                        # cond4 = vwap[-1] <= vwap[-2]
                        # elif cond3 and cond4:
                        #     self.ctx.broker.sellshort(code, trade_amount, round(trade_price-1, 2), msg="卖出开仓")

    def on_deal(self, order):
        pass
        # self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
        #     stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

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
        daily_price_df = load_daily_price(local_stock_list, self.trade_date)
        df_fliter = daily_price_df[daily_price_df["close"] > 12]
        fliterred_list = list(df_fliter["code"])
        stock_trade_list = [x.split(".", 1)[0] for x in fliterred_list]
        stock_trade_list_final = []
        for stock in stock_trade_list:
            break_point = self.break_volume_cal(stock)
            if break_point >= 300:
                self.stg_data[stock] = self.break_volume_cal(stock)
                stock_trade_list_final.append(stock)
        return stock_trade_list_final

    def break_volume_cal(self, stock):
        import tushare as ts
        df_yd = ts.get_tick_data(stock, date=self.trade_date_str, src='tt')
        stock_volume = df_yd["volume"]
        volume_value = stock_volume.quantile(0.995)
        # 本地获取数据
        # df_yd = load_share_mongo(stock, self.trade_date)
        # if len(df_yd) > 0:
        #     stock_volume = df_yd["TradeVolume"]
        #     volume_value = int(stock_volume.quantile(0.995))
        # else:
        #     volume_value = 0
        return volume_value