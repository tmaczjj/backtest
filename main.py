# -*- coding: utf-8 -*-
import datetime
import json
from strategy.IntraDayTrendStrategy import IntraDayTrendStrategy
import multiprocessing
from strategy.breakStrategy import breakStrategy
from backtest import broker
import time
import tushare as ts
from utils.utils import load_tradedate_mongo, load_stock_daily_canuse
from utils.utils import get_backtest_times, get_backtest_records_coll
from utils.utils import save_backtest_records
import pandas as pd
import warnings
from backtest import backtest
import pymongo
import os
warnings.filterwarnings("ignore")
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')
backtest_date = datetime.datetime.now().strftime("%Y%m%d")
backtest_time = datetime.datetime.now()

trade_strategy = breakStrategy


def run(trade_date):
    code_dict = load_stock_daily_canuse(trade_date)
    code_list = list(code_dict.keys())
    T0_broker = broker.T0BackTestBroker(cash=5000000, deal_price="AskPrice1")
    mytest = trade_strategy(code_list, trade_date, broker=T0_broker, codeDict=code_dict)
    mytest.start()

    return mytest.ctx.broker.order_hist_lst


def backtest_intra_day(trade_date: datetime = None):
    """
    针对单日的交易进行回测模式
    :param code_list: 股票代码
    :param trade_date: 交易日
    """
    time_start = time.time()
    trade_strategy_name = trade_strategy.__name__
    # 判断策略是否在策略库内
    route = os.getcwd() + "\\strategy\\" + trade_strategy_name + ".py"
    if os.path.exists(route) is False:
        raise Exception("Strategy is not in the Strategy Library")

    # 判断回测日是否为交易日
    _trade_date = trade_date
    _trade_start_date = trade_date - datetime.timedelta(days=5)
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=trade_date)
    if not trade_date_list:
        raise Exception("非交易日, 请选择交易日进行回测")

    # 获取交易日所在的位置
    if _trade_date in trade_date_list:
        date_index = trade_date_list.index(_trade_date)

    orderHis = run(trade_date_list[date_index])
    back_id = get_backtest_times(trade_strategy_name, backtest_date, bt_type="intra")
    temp_dict = {'backTestTime': backtest_time, "backId": back_id}
    for x_dict in orderHis:
        x_dict.update(temp_dict)

    coll = get_backtest_records_coll(trade_strategy_name, backtest_date, bt_type="intra")
    save_backtest_records(coll, orderHis)
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


def backtest_period_days(trade_start_date: datetime = None, trade_end_date: datetime = None):
    trade_strategy_name = trade_strategy.__name__
    # 判断策略是否在策略库内
    route = os.getcwd() + "\\strategy\\" + trade_strategy_name + ".py"
    if os.path.exists(route) is False:
        raise Exception("Strategy is not in the Strategy Library")

    time_start = time.time()

    _trade_start_date = trade_start_date
    _trade_end_date = trade_end_date
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=_trade_end_date)
    trade_date_list.remove(datetime.datetime(2020, 6, 15))

    back_id = get_backtest_times(trade_strategy_name, backtest_date, bt_type="period")
    temp_dict = {'backTestTime': backtest_time, "backId": back_id}
    coll = get_backtest_records_coll(trade_strategy.__name__, backtest_date, bt_type="period")

    cores = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=cores)
    for orderHis in pool.imap(run, trade_date_list):
        for x_dict in orderHis:
            x_dict.update(temp_dict)
        save_backtest_records(coll, orderHis)

    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


if __name__ == '__main__':
    # 选定回测策略
    # trade_strategy = IntraDayTrendStrategy
    ############################################################################################
    start_date = datetime.datetime(2020, 4, 2)
    end_date = datetime.datetime(2020, 7, 30)
    backtest_period_days(start_date, end_date)
    ############################################################################################
    # trade_date = datetime.datetime(2020, 4, 3)
    # backtest_intra_day(trade_date)
    ############################################################################################



