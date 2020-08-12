import json
import datetime
import pandas as pd
from utils.utils import get_order_json_list
from utils.utils import get_order_single_json
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdate
from pylab import *
mpl.rcParams['font.sans-serif'] = ['SimHei']
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


def output_periods_order_his(cash=1000000):
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
    df_deliver_orders = df_orders_all[((df_orders_all["type"] == "sell") | (df_orders_all["type"] == "buytocover")) &
                                      (df_orders_all["done"] == True)].reset_index()
    df_deliver_orders.drop(columns=["index"], inplace=True)
    # df_deliver_orders = df_deliver_orders[df_deliver_orders["done"] == True].reset_index()
    profit_list = []
    trade_amount_list = []
    cash_list = []
    open_time = []
    for i in range(0, len(df_deliver_orders)):
        order_deal = df_deliver_orders["deal_lst"][i][0]
        commission = order_deal["commission"]
        deal_open_time = order_deal["open_date"][-8:]
        profit = order_deal["profit"] - commission
        shares = order_deal["shares"]
        open_price = order_deal["open_price"]
        order_amount = round(shares*open_price, 2)
        trade_amount_list.append(order_amount)
        profit_list.append(round(profit, 2))
        cash = cash + round(profit, 2)
        cash_list.append(cash)
        open_time.append(deal_open_time)
    df_deliver_orders["open_time"] = open_time
    df_deliver_orders["profit"] = profit_list
    df_deliver_orders["cash"] = cash_list
    df_deliver_orders["trade_amount"] = trade_amount_list
    data_list = list(df_deliver_orders["date"])
    trade_date = [x.strftime("%Y%m%d") for x in data_list]
    df_deliver_orders["trade_date"] = trade_date
    return df_deliver_orders


def output_intraday_order_his(stock_trade_date):
    """
    单日交易的交割单统计
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


def plot_period_net_profit_trade_line():
    """
    连续交易主笔交易净值走势
    :return:
    """
    deal_lst_list = output_periods_order_his()
    profit_lst = deal_lst_list["profit"].cumsum()

    plt.plot(profit_lst, mec='g', mfc='w', label=u'test')
    plt.grid(True, linestyle='-.')
    plt.xlabel(u"tradeNumbers")  # X轴标签
    plt.ylabel(u"profit")  # Y轴标签
    plt.title(u"Strategy Profit Table")  # 标题
    plt.show()


def plot_period_net_profit_daily_line():
    """
    连续交易每日净值走势
    :return:
    """
    deal_lst_list = output_periods_order_his()
    profit_daily_static_2 = deal_lst_list.sort_values(by="trade_date")
    profit_daily_static = deal_lst_list.groupby(['trade_date']).apply(lambda x: x.profit.sum())
    trade_amount_daily_static = deal_lst_list.groupby(['trade_date']).apply(lambda x: x.trade_amount.sum())
    daily_return = profit_daily_static / trade_amount_daily_static * 100
    profit_dict = {"date": profit_daily_static.index, "profit": profit_daily_static.values}
    df_profit = pd.DataFrame(profit_dict, index=profit_daily_static.index)
    profit_df = df_profit['profit'].cumsum()

    plt.figure(16)

    plt.style.use("ggplot")
    plt.subplot(311)
    plt.plot(profit_df.index, profit_df.values, linewidth=2.5)
    plt.xticks(rotation=45)
    plt.xticks([])
    plt.grid(linestyle='-.', axis="both")
    plt.title(u"交易盈亏", fontsize=10)
    plt.legend(["profit"], loc='upper left', fontsize=12)
    plt.ylabel('profit', size=10)
    plt.tick_params(labelsize=8)

    plt.style.use("fivethirtyeight")
    plt.subplot(312)
    plt.bar(trade_amount_daily_static.index, trade_amount_daily_static.values, color=['r', 'b'])
    plt.legend(["trade_volume"], loc='upper left', fontsize=12)
    plt.xticks([])
    plt.ylabel('volume', size=10)
    plt.title(u"日成交量", fontsize=10)

    plt.tick_params(labelsize=6)

    plt.subplot(313)
    plt.bar(daily_return.index, daily_return.values, color=['g'])
    plt.xticks(rotation=60)
    plt.legend(["daily_return_percentage"], loc='upper left', fontsize=12)
    plt.tick_params(labelsize=9)
    plt.title(u"每日盈亏百分比", fontsize=10)
    plt.rcParams['axes.unicode_minus'] = False
    plt.subplots_adjust(top=0.96, bottom=0.06, left=0.1, right=0.9, hspace=0.1, wspace=0)
    plt.show()


def plot_intraday_net_profit_line(stock_trade_date):
    """
    单日交易主笔交易净值走势
    :return:
    """
    profit_lst = []
    cash = 1000000
    deal_lst_list = output_intraday_order_his(stock_trade_date)
    temp = deal_lst_list.sort_values(by="code")
    amount = deal_lst_list["trade_amount"].sum()
    for deal in list(deal_lst_list["deal_lst"]):
        profit = deal[0]["profit"]
        cash = cash + profit
        profit_lst.append(cash)
    plt.plot(profit_lst)
    plt.show()


def stock_profit_static():
    """
    个股盈亏统计
    :return:
    """
    deal_lst_df = output_periods_order_his()
    temp4 = deal_lst_df[(deal_lst_df["msg"] == "做空止损") | (deal_lst_df["msg"] == "做多止损")]
    # 按照股票日期排序
    temp = deal_lst_df.sort_values(by=['code', "date"]).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # 按盈亏大小排序
    temp2 = deal_lst_df.sort_values(by=['profit']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # 按照开仓时间排序
    temp3 = deal_lst_df.sort_values(by=['open_time']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # temp_30 = temp3[(temp3["open_time"] > "13:00:00")]["profit"].sum()
    # temp_31 = temp3[(temp3["open_time"] > "13:01:00")]["profit"].sum()
    # temp_32 = temp3[(temp3["open_time"] > "13:02:00")]["profit"].sum()
    # temp_33 = temp3[(temp3["open_time"] > "13:03:00")]["profit"].sum()
    # temp_34 = temp3[(temp3["open_time"] > "13:04:00")]["profit"].sum()
    profit_code_static = deal_lst_df.groupby(['code']).apply(lambda x: x.profit.sum())
    profit_type_static = deal_lst_df.groupby(['type']).apply(lambda x: x.profit.sum())
    x_data = [str(x) for x in list(profit_code_static.keys())]
    y_data = list(profit_code_static)
    plt.bar(x=x_data, height=y_data, label='个股盈亏统计', color='steelblue', alpha=1)
    plt.xticks(rotation=90)
    plt.subplots_adjust(top=0.96, bottom=0.06, left=0.05, right=0.95, hspace=0.1, wspace=0)
    plt.show()


##############################################
# trade_date = datetime.datetime(2020, 6, 1)
# plot_intraday_net_profit_line(trade_date)
##############################################
stock_profit_static()
plot_period_net_profit_trade_line()
plot_period_net_profit_daily_line()

