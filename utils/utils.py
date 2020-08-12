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

myclient = pymongo.MongoClient("mongodb://192.168.17.19:27017/")
myclient.admin.authenticate('NXADMIN3', 'QDuijw0K1ng2GOZk')


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


def load_from_path(fp_lst, code=None, start_date=None, end_date=None, func=None,):
    """加载文件列表的股票数据

    Parameters:
        code: str or list
                单个或者多个股票代码的列表
        fp_lst: list
                数据文件列表
        start_date: str
                起始时间字符串, 比如2018-01-01
        end_date: str
                截至时间字符串, 比如2019-01-01
        func: function
                用于过滤历史数据的函数, 接受一个Datarame对象, 并返回过滤的DataFrame对象
    """
    for fp in fp_lst:
        fp_code = path.basename(fp)[:-4]
        if code:
            if fp_code == code:
                hist = pd.read_csv(fp)
            else:
                continue
        else:
            hist = pd.read_csv(fp)

        if func:
            hist = func(hist)

        # if start_date:
        #     start_date = pd.to_datetime(start_date)
        #     hist = hist[hist.index >= start_date]

        # if end_date:
        #     end_date = pd.to_datetime(end_date)
        #     hist = hist[hist.index <= end_date]
        yield fp_code, hist


def load_hist_mongo(ts_code=None, trade_date=None):
    # myclient = pymongo.MongoClient("mongodb://192.168.17.31:27017/")
    md = myclient['Stock_Tick_Db']['Stock_Tick_Db']
    start_time = trade_date.replace(hour=9, minute=30, second=3)
    end_time = trade_date.replace(hour=14, minute=56, second=55)
    for code in ts_code:
        json = {'$and': [{"Symbol": code}, {"TradeTime": {"$gte": start_time}}, {"TradeTime": {"$lte": end_time}}]}
        a = md.find(json, {"_id": 0}).sort('TradeTime')
        hists = pd.DataFrame(list(a))
        hists = hists.set_index(hists["TradeTime"])
        # hists = hists[hists["AskPrice1"] != 0]
        yield code, hists
    myclient.close()


def load_local_hist_mongo(ts_code=None, trade_date=None):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    table_name = trade_date.strftime("%Y%m%d")
    md = myclient['Stock_Tick_Db'][table_name]
    start_time = trade_date.replace(hour=9, minute=30, second=3)
    end_time = trade_date.replace(hour=14, minute=56, second=55)
    for code in ts_code:
        json = {'$and': [{"Symbol": code}, {"TradeTime": {"$gte": start_time}}, {"TradeTime": {"$lte": end_time}}]}
        a = md.find(json, {"_id": 0}).sort('TradeTime')
        hists = pd.DataFrame(list(a))
        hists = hists.set_index(hists["TradeTime"])
        # hists = hists[hists["AskPrice1"] != 0]
        yield code, hists
    myclient.close()


def load_share_mongo(ts_code=None, trade_date=None, func=None, random=True, typ="tdx"):
    # myclient = pymongo.MongoClient("mongodb://192.168.17.31:27017/")
    md = myclient['Stock_Tick_Db']['Stock_Tick_Db']
    start_time = trade_date.replace(hour=9, minute=30)
    end_time = trade_date.replace(hour=14, minute=57)
    json = {'$and': [{"Symbol": ts_code}, {"TradeTime": {"$gte": start_time}}, {"TradeTime": {"$lte": end_time}}]}
    a = md.find(json, {"_id": 0}).sort('TradeTime')
    hists = pd.DataFrame(list(a))

    return hists


def load_tradedate_mongo(start_date=None, end_date=None):
    md = myclient['NxData']['IndexDaily']
    json = {'$and': [{"code": "000905.SH"}, {"tradeDate": {"$gte": start_date}}, {"tradeDate": {"$lte": end_date}}]}
    a = md.find(json, {"_id": 0}).sort('tradeDate')
    hists = pd.DataFrame(list(a))
    tradeDateList = list(hists["tradeDate"])
    return tradeDateList


def load_daily_price(stocklist: list = None, trade_date: datetime = None):
    md = myclient['NxData']['stockDaily']
    json = {'$and': [{"code": {"$in": stocklist}}, {"tradeDate":  trade_date}]}
    a = md.find(json, {"_id": 0}).sort('tradeDate')
    hists = pd.DataFrame(list(a))
    return hists


def load_stock_daily_weight(trade_date: datetime = None):
    md = myclient['NxDataCne6']['cne6GTA191dailyweights']
    a = md.find({"index": trade_date}, {"_id": 0})

    hists = pd.DataFrame(list(a)).iloc[0]
    code_list = [code[:6] for code, weight in hists[:-1].items() if weight > 0.002]

    return code_list


def load_stock_daily_canuse(trade_date: datetime = None):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    md = myclient['NxDataCne6']['avaliable_shares']
    a = md.find({"tradeDate": trade_date}, {"_id": 0, "tradeDate": 0})

    hists = pd.DataFrame(list(a))
    hists["code"] = hists["code"].apply(lambda x: x[:6])
    hists = hists.set_index(["code"])["available_num"].to_dict()

    return hists


def load_hist(ts_code=None, start_date=None, end_date=None, func=None, random=True, typ="tdx"):
    """加载本地历史数据

    Parameters:
        ts_code: str or list
                单个或者多个股票代码的列表
        start_date: str
                起始时间字符串, 比如2018-01-01
        end_date: str
                截至时间字符串, 比如2019-01-01
        func: function
                用于过滤历史数据的函数, 接受一个Datarame对象, 并返回过滤的DataFrame对象
        random: bool
                是否打乱加载的股票顺序, 默认为True
    """

    db_glob_lst = glob(path.join("test_data/stock", "*.csv"))
    if len(db_glob_lst) == 0:
        print("当前数据目录没有任何历史数据文件")
        return

    if random:
        np.random.shuffle(db_glob_lst)

    for fp in db_glob_lst:
        fp_ts_code = path.basename(fp)[:-4]
        if ts_code:
            if fp_ts_code in ts_code:
                hist = pd.read_csv(fp, parse_dates=["trade_date"], index_col="trade_date")
                code = hist.ts_code[0]
            else:
                continue
        else:
            hist = pd.read_csv(fp, parse_dates=["trade_date"], index_col="trade_date")
            code = hist.ts_code[0]

        if func:
            hist = func(hist)

        if start_date:
            start_date = pd.to_datetime(start_date)
            hist = hist[hist.index >= start_date]

        if end_date:
            end_date = pd.to_datetime(end_date)
            hist = hist[hist.index <= end_date]

        yield code, hist


def load_hs300_hist():
    pass


def load_all_hist():
    """加载所有历史数据, load_hist的快捷方法"""
    data = {code: hist for code, hist in load_hist()}
    return data


def load_n_hist(n):
    """获取指定数量的历史数据"""
    data = {}
    c = 0
    for code, hist in load_hist():
        c += 1
        data[code] = hist
        if c >= n:
            break
    return data


def get_order_json_list():
    ORDER_FILE_ROUTE = os.getcwd() + "\\order\\period_days\\"
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
