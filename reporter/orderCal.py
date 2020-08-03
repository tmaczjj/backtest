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

    return df_deliver_orders


def output_intraday_order_his():
    trade_date = datetime.datetime(2020, 6, 3)
    order_json = get_order_single_json(trade_date)
    with open(order_json, "r") as rf:
        data = pd.read_json(rf)
        print(data)


def plot_net_profit_line():
    profit_lst = []
    cash = 1000000
    deal_lst_list = output_periods_order_his()
    amount = deal_lst_list["trade_amount"].sum()
    for deal in list(deal_lst_list["deal_lst"]):
        profit = deal[0]["profit"]
        cash = cash + profit
        profit_lst.append(cash)
    plt.plot(profit_lst)
    plt.show()


def stock_profit_static():
    deal_lst_df = output_periods_order_his()
    temp = deal_lst_df.sort_values(by=['code', "date"]).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    temp2 = deal_lst_df.sort_values(by=['profit']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    result = deal_lst_df.groupby(['code']).apply(lambda x: x.profit.sum())
    profit_static = deal_lst_df.groupby(['type']).apply(lambda x: x.profit.sum())
    x_data = [str(x) for x in list(result.keys())]
    y_data = list(result)
    plt.bar(x=x_data, height=y_data, label='个股盈亏统计', color='steelblue', alpha=1)
    plt.xticks(rotation=45)
    plt.show()


stock_profit_static()
plot_net_profit_line()

