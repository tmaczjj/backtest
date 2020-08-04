import json
import datetime
import pandas as pd
from utils.utils import get_order_json_list
from utils.utils import get_order_single_json
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdate
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

def output_periods_order_his():
    """
    连续回测的交割单统计
    :return:
    """
    order_list = get_order_json_list()
    data_list = []
    for order_json in order_list:
        with open(order_json, "r") as rf:
            data = pd.read_json(rf)
            data_list.append(data)
    df_orders_all = pd.concat(data_list)
    df_deliver_orders = df_orders_all[(df_orders_all["type"] == "sell") | (df_orders_all["type"] == "buytocover")]\
        .reset_index()
    df_deliver_orders.drop(columns=["index"], inplace=True)
    profit_list = []
    trade_amount_list = []
    for i in range(0, len(df_deliver_orders)):
        order_deal = df_deliver_orders["deal_lst"][i][0]
        profit = order_deal["profit"]
        shares = order_deal["shares"]
        open_price = order_deal["open_price"]
        order_amount = round(shares*open_price, 2)
        trade_amount_list.append(order_amount)
        profit_list.append(round(profit, 2))
    df_deliver_orders["profit"] = profit_list
    df_deliver_orders["trade_amount"] = trade_amount_list
    data_list = list(df_deliver_orders["date"])
    trade_date = [x.strftime("%Y%m%d") for x in data_list]
    df_deliver_orders["trade_date"] = trade_date
    return df_deliver_orders


def output_intraday_order_his(stock_trade_date):
    """
    日内交易的交割单统计
    :param stock_trade_date:
    :return:
    """
    order_json = get_order_single_json(stock_trade_date)
    with open(order_json, "r") as rf:
        df_orders = pd.read_json(rf)
    df_deliver_orders = df_orders[(df_orders["type"] == "sell") | (df_orders["type"] == "buytocover")]\
        .reset_index()
    df_deliver_orders.drop(columns=["index"], inplace=True)
    profit_list = []
    trade_amount_list = []
    for i in range(0, len(df_deliver_orders)):
        order_deal = df_deliver_orders["deal_lst"][i][0]
        profit = order_deal["profit"]
        shares = order_deal["shares"]
        open_price = order_deal["open_price"]
        order_amount = round(shares * open_price, 2)
        trade_amount_list.append(order_amount)
        profit_list.append(round(profit, 2))
    df_deliver_orders["profit"] = profit_list
    df_deliver_orders["trade_amount"] = trade_amount_list

    return df_deliver_orders


def plot_period_net_profit_line():
    profit_lst = []
    cash = 1000000
    deal_lst_list = output_periods_order_his()
    # 每日盈亏统计
    profit_daily_static = deal_lst_list.groupby(['trade_date']).apply(lambda x: x.profit.sum())
    amount = deal_lst_list["trade_amount"].sum()
    # for deal in list(deal_lst_list["deal_lst"]):
    #     profit = deal[0]["profit"]
    #     cash = cash + profit
    #     profit_lst.append(cash)
    for deal in list(profit_daily_static):
        cash = cash + deal
        profit_lst.append(cash)
    # plt.plot(profit_lst)
    # plt.xticks(x_ticks, rotation=45)
    # plt.show()
    fig = plt.figure(figsize=(12, 9))
    ax = plt.subplot(111)
    # ax.xaxis.set_major_formatter(mdate.DateFormatter('%Y%m%d'))
    x_ticks = [datetime.datetime.strptime(x, "%Y%m%d") for x in profit_daily_static.keys()]
    x_ticks = [datetime.datetime.strftime(x, "%Y%m%d") for x in x_ticks]
    plt.xticks(x_ticks, rotation=45)
    ax.plot(x_ticks, profit_lst, color='r')
    plt.show()


def plot_intraday_net_profit_line(stock_trade_date):
    profit_lst = []
    cash = 1000000
    deal_lst_list = output_intraday_order_his(stock_trade_date)
    amount = deal_lst_list["trade_amount"].sum()
    for deal in list(deal_lst_list["deal_lst"]):
        profit = deal[0]["profit"]
        cash = cash + profit
        profit_lst.append(cash)
    plt.plot(profit_lst)
    plt.show()


def stock_profit_static():
    deal_lst_df = output_periods_order_his()
    # 按照股票日期排序
    temp = deal_lst_df.sort_values(by=['code', "date"]).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # 按盈亏大小排序
    temp2 = deal_lst_df.sort_values(by=['profit']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    profit_code_static = deal_lst_df.groupby(['code']).apply(lambda x: x.profit.sum())
    profit_type_static = deal_lst_df.groupby(['type']).apply(lambda x: x.profit.sum())
    x_data = [str(x) for x in list(profit_code_static.keys())]
    y_data = list(profit_code_static)
    plt.bar(x=x_data, height=y_data, label='个股盈亏统计', color='steelblue', alpha=1)
    plt.xticks(rotation=45)
    plt.show()


##############################################
# trade_date = datetime.datetime(2020, 6, 5)
# plot_intraday_net_profit_line(trade_date)
##############################################
# stock_profit_static()
plot_period_net_profit_line()

