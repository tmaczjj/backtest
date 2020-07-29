from backtest import BackTest
from datetime import datetime
import sys


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, startdate, enddate, cash=cash, broker=broker, enable_stat=enable_stat)
        self.Symbols = []
        self.last_tick = None

    def initialize(self):
        self.info("Strategy--{}--策略初始化完成".format(self.__class__.__name__))

    def finish(self):
        pass

    def on_tick(self, tick):
        tick_data = self.ctx["tick_data"]
        if self.last_tick is None or tick.date() != self.last_tick.date():
            self.update_symbols(tick.date())
        holdposition = self.ctx["broker"].position
        self.last_tick = tick
        tick_time = str(tick.strftime("%H:%M:%S"))
        time_start = "09:25:00"
        time_end = "14:57:30"
        for code, hist in tick_data.items():
            if code in self.Symbols:
                if code in holdposition:
                    stockHoldInfo = holdposition[code][0]
                    if tick_time >= time_end:
                        holdNum = int(stockHoldInfo["shares"])
                        self.ctx.broker.buytocover(code, abs(holdNum), hist.BidPrice1)
                if time_start <= tick_time <= time_end:
                    if code not in holdposition:
                        # self.ctx.broker.buy(code, 500, hist.AskPrice1)
                        self.ctx.broker.sellshort(code, 3000, hist.AskPrice1)


    def update_symbols(self, date):
        if date:
            self.Symbols.append("000002")
        pass