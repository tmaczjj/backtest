from backtest import BackTest
from datetime import datetime
import sys


class MyBackTest(BackTest):
    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        super().__init__(stocklist, startdate, enddate, cash=100000, broker=None, enable_stat=True)
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
        time_start = "09:20:00"
        # time_start = datetime.strptime(time_start)
        time_end = "14:57:30"
        for code, hist in tick_data.items():
            if code in self.Symbols:
                if code in holdposition:
                    stockHoldInfo = holdposition[code][0]
                    if time_end <= tick_time:
                        holdNum = int(stockHoldInfo["shares"])
                        self.ctx.broker.sell(code, holdNum, hist.BidPrice1)
                if time_start >= tick_time:
                    if code not in holdposition:
                        self.ctx.broker.buy(code, 500, hist.AskPrice1)

            # if hist["ma10"] > 1.05 * hist["ma20"]:

            # if hist["ma10"] < hist["ma20"] and code in self.ctx.broker.position:
            #     self.ctx.broker.sell(code, 200, hist.BidPrice1)
    # def isNewDay(self,tick):

    def update_symbols(self, date):
        if date:
            self.Symbols.append("600859")
        pass