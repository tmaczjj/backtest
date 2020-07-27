# -*- coding: utf-8 -*-
# @Time    : 2020/7/16 10:34
# @Author  : WangYang
import datetime
import json
from reporter import Plotter
from strategy.MyBackTest import MyBackTest
from backtest import T0broker

if __name__ == '__main__':
    from utils import load_hist_mongo
    feed = {}
    start_date = datetime.datetime(2020, 6, 1)
    end_date = datetime.datetime(2020, 6, 15)
    lista = []
    lista.append("000002")
    lista.append("600859")
    T0_broker = T0broker.T0BackTestBroker(cash=100000, deal_price="AskPrice1")
    mytest = MyBackTest(lista, start_date, end_date, broker=T0_broker)
    mytest.start()
    order_lst = mytest.ctx.broker.order_hist_lst
    with open("reporter/order_hist.json", "w") as wf:
        json.dump(order_lst, wf, indent=4, default=str)
    stats = mytest.stat
    stats.data.to_csv("reporter/stat.csv")
    #print("策略cash： {:.d}%".format( mytest.ctx.broker.cash))
    print("策略收益： {:.3f}%".format(stats.total_returns * 100))
    print("最大回彻率: {:.3f}% ".format(stats.max_dropdown * 100))
    print("年化收益: {:.3f}% ".format(stats.annual_return * 100))
    print("夏普比率: {:.3f} ".format(stats.sharpe))

    plotter = Plotter(feed, stats, order_lst)
    plotter.report("reporter/report.png")
