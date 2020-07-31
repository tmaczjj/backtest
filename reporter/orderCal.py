import json
import datetime
import pandas as pd
from utils.utils import get_order_json_list
from utils.utils import get_order_single_json
import matplotlib.pyplot as plt


def output_periods_order_his():
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
    deal_lst_list = list(df_deliver_orders["deal_lst"])
    return deal_lst_list


def output_intraday_order_his():
    trade_date = datetime.datetime(2020, 6, 3)
    order_json = get_order_single_json(trade_date)
    with open(order_json, "r") as rf:
        data = pd.read_json(rf)
        print(data)


def plot_net_profit_line():
    profit_lst = []
    cash = 100000
    deal_lst_list = output_periods_order_his()
    for deal in deal_lst_list:
        profit = deal[0]["profit"]
        cash = cash + profit
        profit_lst.append(cash)
    plt.plot(profit_lst)
    plt.show()


plot_net_profit_line()


