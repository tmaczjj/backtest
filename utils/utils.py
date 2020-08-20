# -*- coding: utf-8 -*-
# @Author: youerning
# @Email: 673125641@qq.com
import logging
import os
import sys
import numpy as np
import pandas as pd
import pymongo
from glob import glob
from os import path
import datetime
# from ..settings import config
# data_path = config["STOCK_DATA_PATH"]

local_client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
remote_client = pymongo.MongoClient("mongodb://192.168.17.19:27017/")
remote_client.admin.authenticate('NXADMIN3', 'QDuijw0K1ng2GOZk')


def init_log(name, level=30, log_to_file=False):
    logger = logging.getLogger(name)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_to_file:
        if sys.platform.startswith("linux"):
            fp = "/var/log/%s.log" % name
        else:
            fp = path.join(os.environ["HOMEPATH"], "%s.log" % name)

        file_handler = logging.FileHandler(filename=fp)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
    return logger


def read_csv(fp):
    """读取通过tushare保存的csv文件

    Parameters:
    ----------
      fp:str
            csv文件路径

    Returns
    -------
    pandas.core.frame.DataFrame
    """
    hist = pd.read_csv(fp, parse_dates=["trade_date"], index_col="trade_date")

    return hist


def load_local_hist_mongo(ts_code=None, trade_date=None):
    table_name = trade_date.strftime("%Y%m%d")
    md = local_client['Stock_Tick_Db'][table_name]
    start_time = trade_date.replace(hour=9, minute=30, second=0)
    end_time = trade_date.replace(hour=9, minute=35, second=0)
    # start_time = trade_date.replace(hour=9, minute=30, second=0)
    # end_time = trade_date.replace(hour=14, minute=57, second=0)
    for code in ts_code:
        json = {'$and': [{"Symbol": code}, {"TradeTime": {"$gte": start_time}}, {"TradeTime": {"$lte": end_time}}]}
        a = md.find(json, {"_id": 0}).sort('TradeTime')
        hists = pd.DataFrame(list(a))
        try:
            hists = hists.set_index(hists["TradeTime"])
        except:
            print("\n{code}-{trade_date}无交易日数据".format(code=code, trade_date=trade_date))
        # hists = hists[hists["AskPrice1"] != 0]
        yield code, hists
    local_client.close()


def load_share_mongo(ts_code=None, trade_date=None):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    trade_date_str = trade_date.strftime("%Y%m%d")
    md = myclient['Stock_Tick_Db'][trade_date_str]
    start_time = trade_date.replace(hour=9, minute=30)
    end_time = trade_date.replace(hour=14, minute=57)
    json = {'$and': [{"Symbol": ts_code}, {"TradeTime": {"$gte": start_time}}, {"TradeTime": {"$lte": end_time}}]}
    a = md.find(json, {"_id": 0}).sort('TradeTime')
    hists = pd.DataFrame(list(a))

    return hists


def load_tradedate_mongo(start_date=None, end_date=None):
    md = remote_client['NxData']['IndexDaily']
    json = {'$and': [{"code": "000905.SH"}, {"tradeDate": {"$gte": start_date}}, {"tradeDate": {"$lte": end_date}}]}
    a = md.find(json, {"_id": 0}).sort('tradeDate')
    hists = pd.DataFrame(list(a))
    tradeDateList = list(hists["tradeDate"])
    return tradeDateList


def load_daily_price(stocklist: list = None, trade_date: datetime = None):
    md = remote_client['NxData']['stockDaily']
    json = {'$and': [{"code": {"$in": stocklist}}, {"tradeDate":  trade_date}]}
    a = md.find(json, {"_id": 0}).sort('tradeDate')
    hists = pd.DataFrame(list(a))
    return hists


def load_stock_daily_weight(trade_date: datetime = None):
    md = remote_client['NxDataCne6']['cne6GTA191dailyweights']
    a = md.find({"index": trade_date}, {"_id": 0})

    hists = pd.DataFrame(list(a)).iloc[0]
    code_list = [code[:6] for code, weight in hists[:-1].items() if weight > 0.002]

    return code_list


def load_stock_daily_canuse(trade_date: datetime = None):
    md = local_client['NxDataCne6']['avaliable_shares']
    a = md.find({"tradeDate": trade_date}, {"_id": 0, "tradeDate": 0})

    hists = pd.DataFrame(list(a))
    hists["code"] = hists["code"].apply(lambda x: x[:6])
    hists = hists.set_index(["code"])["available_num"].to_dict()

    return hists


def get_order_json_list():
    ORDER_FILE_ROUTE = os.getcwd() + "\\order\\period_days\\"
    file_list = os.listdir(ORDER_FILE_ROUTE)
    order_json_list = [ORDER_FILE_ROUTE+file for file in file_list]
    return order_json_list


def get_order_json_list_2():
    ORDER_FILE_ROUTE = os.getcwd() + "\\order\\period_days_2\\"
    file_list = os.listdir(ORDER_FILE_ROUTE)
    order_json_list = [ORDER_FILE_ROUTE+file for file in file_list]
    return order_json_list


def get_order_single_json(trade_date):
    """
    To out
    :param trade_date:
    :return:
    """
    ORDER_FILE_ROUTE = os.getcwd() + "\\order\\intra_day\\"
    FILE_NAME = "order_hist_" + trade_date.strftime("%Y%m%d") + ".json"
    order_json = ORDER_FILE_ROUTE + FILE_NAME
    return order_json


def get_backtest_records_coll(strategy_name: str = None, backtestDate: str = None, bt_type=None):
    return strategy_name + "_" + bt_type + "_" + backtestDate


def get_backtest_times(strategy_name: str = None, backtestDate: str = None, bt_type=None):
    temp_name = strategy_name + "_" + bt_type + "_" + backtestDate
    myclient = local_client
    md = myclient['backTestOrder']
    try:
        coll = md[temp_name]
        result = coll.find()
        resultTable = pd.DataFrame(list(result))
        times = len(set(resultTable["backTestTime"])) + 1
    except:
        times = 1

    return times


def save_backtest_records(coll_name: str = None, orderHis: list = None):
    myclient = local_client['backTestOrder']
    coll = myclient[coll_name]
    coll.insert_many(orderHis)


def get_backtest_records():
    pass

# def get_ts_client():
#     ts.set_token(config["TS_TOKEN"])
#
#     return ts
#
#
# def get_pro_client():
#     ts.set_token(config["TS_TOKEN"])
#
#     return ts
