# -*- coding: utf-8 -*-
# @Author: youerning
# @Email: 673125641@qq.com

# import numpy as np
# import pandas as pd
import sys
import numpy as np
from abc import ABC, abstractmethod
import pandas as pd
from collections import UserDict
from itertools import chain
import datetime
from pandas.tseries.frequencies import to_offset
from pandas.tseries.offsets import Hour, Day
from .broker import Base as BrokerBase
from .broker import BackTestBroker
from .utils import logger
from .hooks import Stat
from utils.utils import load_hist_mongo
from utils.utils import load_tradedate_mongo


class Context(UserDict):
    def __getattr__(self, key):
        # 让调用这可以通过索引或者属性引用皆可
        return self[key]

    def set_currnet_time(self, tick):
        """设置回测循环中的当前时间"""
        self["now"] = tick

        tick_data = {}
        # 获取当前所有有报价的股票报价
        # 好像没法更快了
        # loc大概306 µs ± 9.28 µs per loop
        # 字典索引的时间大概是254 ns ± 1.6 µs per loop
        for code, hist in self["feed"].items():
            bar = hist.get(tick)
            if bar is not None:
                tick_data[code] = bar
                try:
                    self.latest_price[code] = bar[self.broker.deal_price]
                except:
                    # print(bar.iloc[:, 1][self.broker.deal_price])
                    self.latest_price[code] = bar.iloc[:, 1][self.broker.deal_price]
                if self.latest_price[code] == 0:
                    self.latest_price[code] = max(bar["BidPrice1"], bar["AskPrice1"], bar["LastPrice"])
        self["tick_data"] = tick_data


class Scheduler(object):
    """
    整个回测过程中的调度中心, 通过一个个时间刻度(tick)来驱动回测逻辑

    所有被调度的对象都会绑定一个叫做ctx的Context对象,由于共享整个回测过程中的所有关键数据,
    可用变量包括:
        ctx.feed: {code1: pd.DataFrame, code2: pd.DataFrame}对象
        ctx.now: 循环所处时间
        ctx.tick_data: 循环所处时间的所有有报价的股票报价
        ctx.trade_cal: 交易日历
        ctx.broker: Broker对象
        ctx.bt/ctx.backtest: Backtest对象
    """

    def __init__(self):
        """"""
        self.ctx = Context()
        self._pre_hook_lst = []
        self._post_hook_lst = []
        self._runner_lst = []

    def add_feed(self, feed):
        self.ctx["feed"] = feed

    def add_hook(self, hook, typ="post"):
        if typ == "post" and hook not in self._post_hook_lst:
            self._post_hook_lst.append(hook)
        elif typ == "pre" and hook not in self._pre_hook_lst:
            self._pre_hook_lst.append(hook)

    def add_broker(self, broker):
        self.ctx["broker"] = broker
        broker.ctx = self.ctx

    def add_backtest(self, backtest):
        self.ctx["backtest"] = backtest
        # 简写
        self.ctx["bt"] = backtest

    def add_runner(self, runner):
        if runner in self._runner_lst:
            return
        self._runner_lst.append(runner)

    def add_trade_cal(self):
        """增加交易日历"""
        import pandas as pd
        x = pd.Series()
        for hist in self.ctx["feed"]:
            hists = self.ctx["feed"][hist].T
            aa = hists["TradeTime"]
            x = x.append(aa)
        mask = x.duplicated()
        trade_cal = x[~mask].sort_index()
        self.ctx["trade_cal"] = trade_cal

    def run(self):
        # 缓存每只股票的最新价格
        self.ctx["latest_price"] = {}
        # runner指存在可调用的initialize, finish, run(tick)的对象
        runner_lst = list(chain(self._pre_hook_lst, self._runner_lst, self._post_hook_lst))
        # 循环开始前为broker, backtest, hook等实例绑定ctx对象及调用其initialize方法
        for runner in runner_lst:
            runner.ctx = self.ctx
            runner.initialize()

        # 开始结束时间
        # 按天取数据 对齐trade_cal
        # 通过遍历交易日历的时间依次调用runner
        # 首先调用所有pre-hook的run方法
        # 然后调用broker,backtest的run方法
        # 最后调用post-hook的run方法
        bt = self.ctx.bt
        last_tick = self.ctx["now"] = self.ctx.trade_cal[0]
        is_market_start = True

        for tick in self.ctx.trade_cal:
            self.ctx.set_currnet_time(tick)

            # 策略初始化只执行一次
            if is_market_start:
                bt.on_market_start()
                is_market_start = False

            for runner in runner_lst:
                runner.run(tick)

        bt.on_market_close()
        # 循环结束后调用所有runner对象的finish方法
        for runner in runner_lst:
            runner.finish()


class BackTest(ABC):
    """
    回测引擎的基类
    提供回测的大致框架, 提供各个事件的钩子函数

    Parameters:
      feed:dict
                股票代码历史数据， 如{"000001.SZ": {Timestamp('2018-04-20 10:30:00'): {"open": 10.67, "close": 10.89}}, ....}
      cash:int
                用于股票回测的初始资金, 默认为10w
      broker:Broker
                提供buy, sell方法的交易平台对象
      trade_cal:list
                以时间戳为元素的序列
      enable_stat:bool
                开启统计功能, 默认开启
    """

    def __init__(self, stocklist=None, startdate=None, enddate=None, cash=100000, broker=None, enable_stat=True):
        print("- * - * - * - * - * 回测系统启动 - * - * - * - * - *")
        self.startdate = startdate
        self.enddate = enddate
        self._sch = Scheduler()
        self._logger = logger
        self.stocklist = stocklist

        if isinstance(broker, BrokerBase):
            broker = broker
        else:
            broker = BackTestBroker(cash, deal_price="AskPrice1")

        # 设置backtest, broker对象, 以及将自身实例放在调度器的runner_list中
        self._sch.add_runner(self)
        self._sch.add_backtest(self)
        self._sch.add_broker(broker)
        self.stat = Stat()
        if enable_stat:
            self._sch.add_hook(self.stat)

    def info(self, msg):
        self._logger.info(msg)

    def add_hook(self, *agrs, **kwargs):
        self._sch.add_hook(*agrs, **kwargs)

    def initialize(self):
        """在回测开始前的初始化"""
        pass
    
    def on_market_start(self):
        trade_date = self.ctx["now"].strftime("%Y-%m-%d")
        self.info("{}交易日开始".format(trade_date))

    def on_market_close(self):
        trade_date = self.ctx["now"].strftime("%Y-%m-%d")
        self.info("{}交易日结束".format(trade_date))
        self.info("- * - * - * - * - * - * - * - * - * - * - * - * - * - * - *")

    def before_on_tick(self, tick):
        pass

    def after_on_tick(self, tick):
        pass

    def before_trade(self, order):
        """在交易之前会调用此函数
        可以在此放置资金管理及风险管理的代码
        如果返回True就允许交易，否则放弃交易
        """
        return True

    def on_order_ok(self, order):
        """当订单执行成功后调用"""
        pass

    def on_order_timeout(self, order):
        """当订单超时后调用"""
        pass

    def finish(self):
        """在回测结束后调用"""
        pass

    def run(self, tick):
        self.before_on_tick(tick)
        self.on_tick(tick)
        self.after_on_tick(tick)

    def start(self):
        start_date = self.startdate
        end_date = self.enddate - datetime.timedelta(days=1)
        tradeDateList = load_tradedate_mongo(start_date=start_date, end_date=end_date)
        for dt in tradeDateList:
            feed = {}
            for code, hist in load_hist_mongo(self.stocklist, trade_date=dt):
                feed[code] = hist.T
            self.info("{}交易日股票数据导入完成".format(dt.strftime("%Y-%m-%d")))
            # 添加交易数据
            self._sch.add_feed(feed)
            # 设置交易日历
            self._sch.add_trade_cal()
            self._sch.run()

    @abstractmethod
    def on_tick(self, tick):
        """
        回测实例必须实现的方法，并编写自己的交易逻辑
        """
        pass
