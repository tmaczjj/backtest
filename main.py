# -*- coding: utf-8 -*-
import datetime
import json
from reporter import Plotter
from strategy.IntraDayTrendStrategy import IntraDayTrendStrategy
from strategy.breakStrategy import BreakStrategy
from backtest import broker
import time
import tushare as ts
from utils.utils import load_tradedate_mongo, load_stock_daily_weight, load_stock_daily_canuse
from joblib import Parallel, delayed
import warnings
import traceback
import logging
import sys
warnings.filterwarnings("ignore")
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')


def create_log(trade_date):
    import os
    log_time = datetime.datetime.now()
    trade_time = trade_date.strftime("%Y%m%d")
    log_date_str = log_time.strftime("%Y%m%d")
    pwd = os.getcwd() + "\\reporter\\trade_log\\" + log_date_str
    word_name = os.path.exists(pwd)
    if not word_name:
        os.makedirs(pwd)
    log_route = pwd + "\\" + trade_time
    log_file = log_route + ".log"
    with open(log_file, mode="w", encoding="utf-8") as f:
        # f.close()
        return f


def run(trade_date: datetime = None):
    # code_list = load_stock_daily_weight(trade_date)
    code_dict = load_stock_daily_canuse(trade_date)
    code_list = list(code_dict.keys())
    log_obj = create_log(trade_date)
    T0_broker = broker.T0BackTestBroker(cash=5000000, deal_price="AskPrice1", logfile=log_obj.name)
    # mytest = IntraDayTrendStrategy(code_list, trade_date, broker=T0_broker, codeDict=code_dict)
    mytest = BreakStrategy(code_list, trade_date, broker=T0_broker, codeDict=code_dict, logfile=log_obj.name)
    mytest.start()

    # 交易保存
    s = traceback.extract_stack()
    fun_name = s[-2][2]
    if fun_name == "backtest_intra_day":
        ORDER_FILE_NAME = "order_hist_" + trade_date.strftime("%Y%m%d") + ".json"
        ORDER_FILE_ROUTE = "reporter/order/intra_day/" + ORDER_FILE_NAME
        ACCOUNT_STAT_NAME = "stat_" + trade_date.strftime("%Y%m%d") + ".csv"
        ACCOUNT_STAT_ROUTE = "reporter/account/intra_day/" + ACCOUNT_STAT_NAME

    else:
        ORDER_FILE_NAME = "order_hist_" + trade_date.strftime("%Y%m%d") + ".json"
        ORDER_FILE_ROUTE = "reporter/order/period_days_2/" + ORDER_FILE_NAME
        ACCOUNT_STAT_NAME = "stat_" + trade_date.strftime("%Y%m%d") + ".csv"
        ACCOUNT_STAT_ROUTE = "reporter/account/period_days/" + ACCOUNT_STAT_NAME
    order_lst = mytest.ctx.broker.order_hist_lst
    with open(ORDER_FILE_ROUTE, "w") as wf:
        json.dump(order_lst, wf, indent=4, default=str)
    stats = mytest.stat
    stats.data.to_csv(ACCOUNT_STAT_ROUTE)
    with open(log_obj.name, mode="w", encoding="utf-8") as f:
        f.close()
    print("{}交易日交易完成".format(trade_date.strftime("%Y%m%d")))
    # sys.exit(0)
    # print("策略收益： {:.3f}%".format(stats.total_returns * 100))
    # print("最大回彻率: {:.3f}% ".format(stats.max_dropdown * 100))
    # print("年化收益: {:.3f}% ".format(stats.annual_return * 100))
    # print("夏普比率: {:.3f} ".format(stats.sharpe))
    #
    # plotter = Plotter(stats, order_lst)
    # plotter.report("reporter/report.png")


def backtest_intra_day(trade_date: datetime = None):
    """
    针对单日的交易进行回测模式
    :param code_list: 股票代码
    :param trade_date: 交易日
    """
    time_start = time.time()
    _trade_date = trade_date
    _trade_start_date = trade_date - datetime.timedelta(days=5)
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=trade_date)
    if not trade_date_list:
        raise Exception("非交易日, 请选择交易日进行回测")
    if _trade_date in trade_date_list:
        date_index = trade_date_list.index(_trade_date)
    run(trade_date_list[date_index])
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


def backtest_period_days(trade_start_date: datetime=None, trade_end_date: datetime=None):
    time_start = time.time()
    _trade_start_date = trade_start_date
    _trade_end_date = trade_end_date
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=_trade_end_date)
    trade_date_list.remove(datetime.datetime(2020, 6, 15))
    Parallel(n_jobs=12)(delayed(run)(dt) for dt in trade_date_list)
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


if __name__ == '__main__':
    print("- * - * - * - * - * - * - * 回测系统启动 - * - * - * - * - * - * - *")
    start_date = datetime.datetime(2020, 4, 2)
    end_date = datetime.datetime(2020, 7, 30)
    backtest_period_days(start_date, end_date)
    ############################################################################################
    # trade_date = datetime.datetime(2020, 4, 2)
    # backtest_intra_day(trade_date)
    ############################################################################################



