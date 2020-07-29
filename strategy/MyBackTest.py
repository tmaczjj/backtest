# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
from datetime import datetime
from backtest.backtest import ArrayManager


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, startdate, enddate, cash=cash, broker=broker, enable_stat=enable_stat)
        self.am = {}

    def initialize(self):
        for stock in self.stocklist:
            self.am[stock] = ArrayManager()
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
                    self.ctx.broker.buytocover(code, abs(hold_num), market_data.BidPrice1, msg="做空平仓")
            if code not in hold_position:
                if time_start <= tick_time <= time_end:
                    if trade_volume > 2000:
                        self.ctx.broker.sellshort(code, 1000, market_data.AskPrice1, msg="卖出开仓")

    def on_deal(self, order):
        self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
            stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

    def finish(self):
        pass
