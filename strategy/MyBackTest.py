# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
from datetime import datetime
from backtest.backtest import ArrayManager
import tushare as ts
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, trade_date=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, trade_date, cash=cash, broker=broker, enable_stat=enable_stat)
        self.am = {}
        self.stg_data = {}

    def initialize(self):
        for stock in self.stocklist:
            self.am[stock] = ArrayManager()
            self.stg_data[stock] = self.break_volume_cal(stock)
        self.info("Strategy--{}--策略初始化完成".format(self.__class__.__name__))

    def on_tick(self, tick):
        tick_data = self.ctx["tick_data"]
        hold_position = self.ctx["broker"].position
        tick_time = str(tick.strftime("%H:%M:%S"))
        time_start = "09:35:00"
        time_end = "14:56:30"
        traded_list = []
        for code, market_data in tick_data.items():
            self.am[code].update(market_data)
            trade_volume = self.am[code].volume[-1]
            vwap = self.am[code].vwap
            if code in hold_position:
                stock_hold_info = hold_position[code][0]
                trade_price = max(market_data.LastPrice, market_data.BidPrice1, market_data.AskPrice1)
                hold_num = int(stock_hold_info["shares"])
                if time_start <= tick_time < time_end:
                    open_price = stock_hold_info["open_price"]
                    long_stop_price = open_price * 0.98
                    short_stop_price = open_price * 1.02
                    if hold_num < 0:
                        if trade_price > short_stop_price:
                            self.ctx.broker.buytocover(code, abs(hold_num), round(trade_price+1, 2), msg="做空平仓")
                            traded_list.append(code)
                    if hold_num > 0:
                        if trade_price < long_stop_price:
                            self.ctx.broker.sell(code, hold_num, round(trade_price-1, 2), msg="做多平仓")
                            traded_list.append(code)

                if tick_time >= time_end:
                    if hold_num < 0:
                        self.ctx.broker.buytocover(code, abs(hold_num), round(trade_price+1, 2), msg="做空平仓")
                        traded_list.append(code)
                    if hold_num > 0:
                        self.ctx.broker.sell(code, hold_num, round(trade_price-1, 2), msg="做多平仓")
                        traded_list.append(code)

            if code not in hold_position and code not in traded_list:
                if time_start <= tick_time < time_end:
                    if trade_volume > self.stg_data[code]:
                        trade_price = max(market_data.LastPrice, market_data.BidPrice1, market_data.AskPrice1)
                        trade_amount = int(round(int(100000 / market_data.AskPrice1) / 100) * 100)
                        cond1 = self.am[code].last_price[-1] > self.am[code].last_price[-2] > vwap[-1]
                        cond2 = vwap[-1] >= vwap[-2]
                        cond3 = self.am[code].last_price[-1] < self.am[code].last_price[-2] < vwap[-1]
                        cond4 = vwap[-1] <= vwap[-2]
                        if cond1 and cond2:
                            self.ctx.broker.buy(code, trade_amount, round(trade_price+1, 2), msg="买入开仓")
                        elif cond3 and cond4:
                            self.ctx.broker.sellshort(code, trade_amount, round(trade_price-1, 2), msg="卖出开仓")

    def on_deal(self, order):
        pass
        # self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
        #     stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

    def finish(self):
        pass

    def stockFliter(self):
        """
        股票筛选模块
        实现每日股票筛选
        若不需要筛选 直接return self.stocklist

        :return:     list:需要交易的股票
        """
        trade_date = self.trade_date.strftime("%Y%m%d")
        stock_list = self.stocklist
        tushare_stock_list = [x + ".SZ" for x in stock_list]
        tushare_str = ""
        for stock in tushare_stock_list:
            tushare_str += str(stock+",")
        df = pro.query('daily', ts_code=tushare_str, trade_date=trade_date)
        df_fliter = df[df["pre_close"] > 10]
        fliterred_list = list(df_fliter["ts_code"])
        stock_trade_list = [x.split(".", 1)[0] for x in fliterred_list]
        return stock_trade_list

    def break_volume_cal(self, stock):
        import warnings
        warnings.filterwarnings("ignore")
        code = stock
        trade_date = self.trade_date.strftime("%Y-%m-%d")
        df_yd = ts.get_tick_data(code, date=trade_date, src='tt')
        stock_volume = df_yd["volume"]
        volume_value = int(stock_volume.quantile(0.995))
        return volume_value