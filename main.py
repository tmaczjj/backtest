# -*- coding: utf-8 -*-
import datetime
import json
from reporter import Plotter
from strategy.MyBackTest import MyBackTest
from backtest import broker
import time
import warnings
import tushare as ts
from utils.utils import load_tradedate_mongo
import sys
from joblib import Parallel, delayed
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')
warnings.filterwarnings("ignore")

if __name__ == '__main__':
    time_start = time.time()
    start_date = datetime.datetime(2020, 6, 1)
    end_date = datetime.datetime(2020, 6, 30)
    df = pro.index_weight(index_code='399673.SZ', start_date="20200228")
    codelist = [x.split(".")[0] for x in list(df["con_code"])]
    T0_broker = broker.T0BackTestBroker(cash=100000, deal_price="AskPrice1")
    mytest = MyBackTest(codelist, start_date, end_date, broker=T0_broker)
    mytest.start()

    order_lst = mytest.ctx.broker.order_hist_lst
    with open("reporter/order_hist.json", "w") as wf:
        json.dump(order_lst, wf, indent=4, default=str)
    stats = mytest.stat
    stats.data.to_csv("reporter/stat.csv")
    print("策略收益： {:.3f}%".format(stats.total_returns * 100))
    print("最大回彻率: {:.3f}% ".format(stats.max_dropdown * 100))
    print("年化收益: {:.3f}% ".format(stats.annual_return * 100))
    print("夏普比率: {:.3f} ".format(stats.sharpe))

    plotter = Plotter(stats, order_lst)
    plotter.report("reporter/report.png")
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))
