# -*- coding: utf-8 -*-
import datetime
import json
from reporter import Plotter
from strategy.MyBackTest import MyBackTest
from backtest import broker
import time
import tushare as ts
from utils.utils import load_tradedate_mongo
from joblib import Parallel, delayed
import warnings
import traceback
warnings.filterwarnings("ignore")
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')


def run(trade_date: datetime = None):
    s = traceback.extract_stack()
    fun_name = s[-2][2]
    if fun_name == "backtest_intra_day":
        ORDER_FILE_NAME = "order_hist_" + trade_date.strftime("%Y%m%d") + ".json"
        ORDER_FILE_ROUTE = "reporter/order/intra_day/" + ORDER_FILE_NAME
        ACCOUNT_STAT_NAME = "stat_" + trade_date.strftime("%Y%m%d") + ".csv"
        ACCOUNT_STAT_ROUTE = "reporter/account/intra_day/" + ACCOUNT_STAT_NAME

    else:
        ORDER_FILE_NAME = "order_hist_" + trade_date.strftime("%Y%m%d") + ".json"
        ORDER_FILE_ROUTE = "reporter/order/period_days/" + ORDER_FILE_NAME
        ACCOUNT_STAT_NAME = "stat_" + trade_date.strftime("%Y%m%d") + ".csv"
        ACCOUNT_STAT_ROUTE = "reporter/account/period_days/" + ACCOUNT_STAT_NAME

    T0_broker = broker.T0BackTestBroker(cash=100000, deal_price="AskPrice1")
    mytest = MyBackTest(codelist, trade_date, broker=T0_broker)
    mytest.start()
    order_lst = mytest.ctx.broker.order_hist_lst
    with open(ORDER_FILE_ROUTE, "w") as wf:
        json.dump(order_lst, wf, indent=4, default=str)
    stats = mytest.stat
    stats.data.to_csv(ACCOUNT_STAT_ROUTE)
    # print("策略收益： {:.3f}%".format(stats.total_returns * 100))
    # print("最大回彻率: {:.3f}% ".format(stats.max_dropdown * 100))
    # print("年化收益: {:.3f}% ".format(stats.annual_return * 100))
    # print("夏普比率: {:.3f} ".format(stats.sharpe))
    #
    # plotter = Plotter(stats, order_lst)
    # plotter.report("reporter/report.png")


def backtest_intra_day(code_list=None, trade_date: datetime = None):
    """
    针对单日的交易进行回测模式
    :param code_list: 股票代码
    :param trade_date: 交易日
    """
    time_start = time.time()
    _trade_code_list = code_list
    _trade_date = trade_date
    trade_date_list = load_tradedate_mongo(start_date=trade_date, end_date=trade_date)
    if not trade_date_list:
        raise Exception("非交易日, 请选择交易日进行回测")
    run(trade_date_list[0])
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


def backtest_period_days(code_list=None, trade_start_date: datetime=None, trade_end_date: datetime=None):
    time_start = time.time()
    _trade_code_list = code_list
    _trade_start_date = trade_start_date
    _trade_end_date = trade_end_date - datetime.timedelta(days=1)
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=_trade_end_date)
    Parallel(n_jobs=8)(delayed(run)(dt) for dt in trade_date_list)
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


if __name__ == '__main__':
    start_date = datetime.datetime(2020, 6, 1)
    end_date = datetime.datetime(2020, 6, 30)
    trade_date = datetime.datetime(2020, 6, 4)
    df = pro.index_weight(index_code='399673.SZ', start_date="20200228")
    codelist = [x.split(".")[0] for x in list(df["con_code"])]

    print("- * - * - * - * - * - * - * 回测系统启动 - * - * - * - * - * - * - *")
    print("股票持仓列表{stock_list}".format(stock_list=codelist))
    ############################################################################################
    # backtest_intra_day(codelist, trade_date)
    backtest_period_days(codelist, start_date, end_date)


