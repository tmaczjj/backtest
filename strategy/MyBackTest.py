# -*- coding: utf-8 -*-
from backtest import BackTest
from datetime import datetime


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, startdate, enddate, cash=cash, broker=broker, enable_stat=enable_stat)
        self.Symbols = []

    def initialize(self):
        self.info("Strategy--{}--策略初始化完成".format(self.__class__.__name__))

    def on_tick(self, tick):
        tick_data = self.ctx["tick_data"]
        hold_position = self.ctx["broker"].position
        tick_time = str(tick.strftime("%H:%M:%S"))
        time_start = "09:25:00"
        time_end = "14:57:30"
        for code, hist in tick_data.items():
            # if code in self.Symbols:
            if code in hold_position:
                stock_hold_info = hold_position[code][0]
                if tick_time >= time_end:
                    hold_num = int(stock_hold_info["shares"])
                    self.ctx.broker.buytocover(code, abs(hold_num), hist.BidPrice1, msg="平空")
            if code not in hold_position:
                if time_start <= tick_time <= time_end:
                    self.ctx.broker.sellshort(code, 1000, hist.AskPrice1, msg="卖出开仓")


    def finish(self):
        pass
