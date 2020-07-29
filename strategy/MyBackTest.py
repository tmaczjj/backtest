# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
from datetime import datetime
from backtest.backtest import ArrayManager
import tushare as ts


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, startdate, enddate, cash=cash, broker=broker, enable_stat=enable_stat)
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
        time_end = "14:57:30"
        for code, market_data in tick_data.items():
            self.am[code].update(market_data)
            trade_volume = self.am[code].volume[-1]
            if code in hold_position:
                stock_hold_info = hold_position[code][0]
                if tick_time >= time_end:
                    hold_num = int(stock_hold_info["shares"])
                    if hold_num < 0:
                        self.ctx.broker.buytocover(code, abs(hold_num), market_data.AskPrice1, msg="做空平仓")
                    elif hold_num > 0:
                        self.ctx.broker.sell(code, hold_num, market_data.BidPrice1, msg="做多平仓")
            if code not in hold_position:
                if time_start <= tick_time <= time_end:
                    if trade_volume > self.stg_data[code]:
                        trade_amount = int(round(int(20000 / market_data.AskPrice1) / 100) * 100)
                        if self.am[code].last_price[-1] > self.am[code].last_price[-2]:
                            self.ctx.broker.buy(code, trade_amount, market_data.AskPrice1, msg="买入开仓")
                        else:
                            self.ctx.broker.sellshort(code, trade_amount, market_data.BidPrice1, msg="卖出开仓")

    def on_deal(self, order):
        self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
            stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

    def finish(self):
        pass

    def stockFliter(self):
        """
        股票筛选模块
        实现每日股票筛选
        若不需要筛选 直接return self.stocklist

        :return:     list:需要交易的股票
        """
        stock_trade_list = []
        stock_list = self.stocklist
        for stock in stock_list:
            if stock.startswith("0") or stock.startswith("3"):
                stock_trade_list.append(stock)

        return stock_trade_list

    def break_volume_cal(self, stock):
        code = stock
        trade_date = self.trade_date.strftime("%Y-%m-%d")
        df_yd = ts.get_tick_data(code, date=trade_date, src='tt')
        stock_volume = df_yd["volume"]
        volume_value = int(stock_volume.quantile(0.995))
        return volume_value