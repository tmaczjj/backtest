# -*- coding: utf-8 -*-
import datetime
from strategy.IntraDayTrendStrategy import IntraDayTrendStrategy
import multiprocessing
from strategy.breakStrategy import breakStrategy
from backtest import broker
import time
import tushare as ts
from utils.utils import load_tradedate_mongo, load_stock_daily_canuse
from utils.utils import get_backtest_times, get_backtest_records_coll
from utils.utils import save_backtest_records
from reporter.orderCal import plot_period_net_profit_daily_line as ppd
from reporter.orderCal import plot_intraday_net_profit_line as pid
from reporter.orderCal import output_periods_order_his as opo
from reporter.orderCal import output_intraday_order_his as oio
import pymongo
import pandas as pd
import warnings
import os

warnings.filterwarnings("ignore")
pro = ts.pro_api('5fc1ae2a4708570262b751312b521760932f3170201a9842b28212cc')
backtest_date = datetime.datetime.now().strftime("%Y%m%d")
backtest_time = datetime.datetime.now()


def run(tradeDate, strategy):
    code_dict = load_stock_daily_canuse(tradeDate)
    code_list = list(code_dict.keys())
    T0_broker = broker.T0BackTestBroker()
    mytest = strategy(code_list, tradeDate, broker=T0_broker, codeDict=code_dict)
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

    date_index = -1
    # 获取交易日所在的位置
    if _trade_date in trade_date_list:
        date_index = trade_date_list.index(_trade_date)

    orderHis = run(trade_date_list[date_index], trade_strategy)
    back_id = get_backtest_times(trade_strategy_name, backtest_date, bt_type="intra")
    temp_dict = {'backTestTime': backtest_time, "backId": back_id}
    for x_dict in orderHis:
        x_dict.update(temp_dict)

    coll = get_backtest_records_coll(trade_strategy_name, backtest_date, bt_type="intra")
    save_backtest_records(coll, orderHis)
    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


def backtest_period_days(test_strategy=None, trade_start_date: datetime = None, trade_end_date: datetime = None):
    trade_strategy_name = test_strategy.__name__
    tradeStrategy = test_strategy
    iterList = []
    # 判断策略是否在策略库内
    route = os.getcwd() + "\\strategy\\" + trade_strategy_name + ".py"
    if os.path.exists(route) is False:
        raise Exception("Strategy is not in the Strategy Library")

    time_start = time.time()

    _trade_start_date = trade_start_date
    _trade_end_date = trade_end_date
    trade_date_list = load_tradedate_mongo(start_date=_trade_start_date, end_date=_trade_end_date)
    trade_date_list.remove(datetime.datetime(2020, 6, 15))
    for dt in trade_date_list:
        temp = [dt, tradeStrategy]
        iterList.append(temp)

    back_id = get_backtest_times(trade_strategy_name, backtest_date, bt_type="period")
    temp_dict = {'backTestTime': backtest_time, "backId": back_id}
    coll = get_backtest_records_coll(trade_strategy.__name__, backtest_date, bt_type="period")
    cores = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=cores)
    for orderHis in pool.starmap(run, iterList):
        for x_dict in orderHis:
            x_dict.update(temp_dict)
        save_backtest_records(coll, orderHis)

    time_end = time.time()
    time_spent = time_end - time_start
    print("\n回测耗时--: {time}".format(time=time_spent))


def backtest_last_plot(back_test_type: str = None):
    if back_test_type is None:
        raise ValueError("please Enter the backtest type")
    test_strategy_name = trade_strategy.__name__
    local_client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    myclient = local_client['backTestOrder']
    coll_name = test_strategy_name + "_" + back_test_type + "_" + backtest_date
    coll = myclient[coll_name]
    result = coll.find({}, {"_id": 0}).sort("backId")
    result_df = pd.DataFrame(list(result))
    last_result_df = result_df[result_df["backId"] == result_df.iloc[-1].backId]

    if back_test_type == "period":
        df_deliver_orders = opo(last_result_df)
        ppd(df_deliver_orders)

    if back_test_type == "intra":
        df_deliver_orders = oio(last_result_df)
        pid(df_deliver_orders)


def backtest_his_plot(back_test_type: str = "period", back_test_strategy: str = "",  test_id: int = 0):
    """

    :param back_test_type:
    :param back_test_strategy:
    :param test_id:
    :return:
    """
    if test_id == 0:
        raise ValueError("Please enter the backtest id.")

    local_client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    myClient = local_client['backTestOrder']
    colls = myClient.list_collection_names()
    coll_name = back_test_strategy + "_" + back_test_type + "_" + backtest_date

    if coll_name in colls:
        coll = myClient[coll_name]
        result = coll.find({}, {"_id": 0}).sort("backId")
        result_df = pd.DataFrame(list(result))
        last_result_df = result_df[result_df["backId"] == test_id]
        if back_test_type == "period":
            df_deliver_orders = opo(last_result_df)
            ppd(df_deliver_orders)

        if back_test_type == "intra":
            df_deliver_orders = oio(last_result_df)
            pid(df_deliver_orders)
    else:
        raise ValueError("There is no any backtest result data")


if __name__ == '__main__':
    trade_strategy = breakStrategy
    ############################################################################################
    start_date = datetime.datetime(2020, 4, 2)
    end_date = datetime.datetime(2020, 7, 30)
    backtest_period_days(trade_strategy, start_date, end_date)
    ############################################################################################
    # trade_date = datetime.datetime(2020, 4, 3)
    # backtest_intra_day(trade_date)
    ############################################################################################
    backtest_type = "period"
    backtest_last_plot(back_test_type=backtest_type)
    # backtest_his_plot(backtest_type, trade_strategy.__name__, test_id=1)
    # backtest_his_plot(backtest_type, trade_strategy.__name__, test_id=2)



