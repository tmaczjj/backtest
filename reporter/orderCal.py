import pandas as pd
from pandas import DataFrame
from pylab import *
from matplotlib.gridspec import GridSpec
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
mpl.rcParams['font.sans-serif'] = ['SimHei']


def output_periods_order_his(order_df: DataFrame = None, cash=1000000):
    """
    连续回测的交割单统计
    :return:
    """
    df_orders_all = order_df
    df_deliver_orders = df_orders_all[((df_orders_all["type"] == "sell") | (df_orders_all["type"] == "buytocover")) &
                                      (df_orders_all["done"] == True)].reset_index()
    df_deliver_orders.drop(columns=["index"], inplace=True)
    # df_deliver_orders = df_deliver_orders[df_deliver_orders["done"] == True].reset_index()
    profit_list = []
    trade_amount_list = []
    cash_list = []
    open_time = []
    commission_list = []
    for i in range(0, len(df_deliver_orders)):
        order_deal = df_deliver_orders["deal_lst"][i][0]
        commission = order_deal["commission"]
        deal_open_time = order_deal["open_date"].strftime("%H:%M:%S")
        profit = order_deal["profit"] - commission
        shares = order_deal["shares"]
        open_price = order_deal["open_price"]
        order_amount = round(shares*open_price, 2)
        trade_amount_list.append(order_amount)
        profit_list.append(round(profit, 2))
        cash = cash + round(profit, 2)
        commission_list.append(commission)
        cash_list.append(cash)
        open_time.append(deal_open_time)
    df_deliver_orders["commission"] = commission_list
    df_deliver_orders["open_time"] = open_time
    df_deliver_orders["profit"] = profit_list
    df_deliver_orders["cash"] = cash_list
    df_deliver_orders["trade_amount"] = trade_amount_list
    data_list = list(df_deliver_orders["date"])
    trade_date = [date.strftime("%Y%m%d") for date in data_list]
    df_deliver_orders["trade_date"] = trade_date
    df_deliver_orders.drop(["id", "backId", "backTestTime", "shares", "ttl", "done"], axis=1, inplace=True)
    return df_deliver_orders


def output_intraday_order_his(order_df: DataFrame = None):
    df_orders = order_df
    df_deliver_orders = df_orders[((df_orders["type"] == "sell") | (df_orders["type"] == "buytocover")) &
                                      (df_orders["done"] == True)].reset_index()
    df_deliver_orders.drop(columns=["index"], inplace=True)
    # df_deliver_orders = df_deliver_orders[df_deliver_orders["done"] == True].reset_index()
    profit_list = []
    trade_amount_list = []
    open_time = []
    commission_list = []
    for i in range(0, len(df_deliver_orders)):
        order_deal = df_deliver_orders["deal_lst"][i][0]
        commission = order_deal["commission"]
        deal_open_time = order_deal["open_date"].strftime("%H:%M:%S")
        profit = order_deal["profit"] - commission
        shares = order_deal["shares"]
        open_price = order_deal["open_price"]
        order_amount = round(shares * open_price, 2)
        trade_amount_list.append(order_amount)
        profit_list.append(round(profit, 2))
        commission_list.append(commission)
        open_time.append(deal_open_time)
    df_deliver_orders["commission"] = commission_list
    df_deliver_orders["open_time"] = open_time
    df_deliver_orders["profit"] = profit_list
    df_deliver_orders["trade_amount"] = trade_amount_list
    data_list = list(df_deliver_orders["date"])
    trade_date = [x.strftime("%Y%m%d") for x in data_list]
    df_deliver_orders["trade_date"] = trade_date
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
    plt.xlabel(u"tradeNumbers")
    plt.ylabel(u"profit")
    plt.title(u"Strategy Profit Table")
    plt.show()


def plot_period_net_profit_daily_line(dealed_df: DataFrame = None):
    """
    连续交易每日净值走势
    :return:
    """
    def to_percent(temp, position):
        return '%.2f' % (100 * temp) + '%'
    deal_lst_list = dealed_df

    def MaxDrawdown(return_list):
        '''最大回撤率'''
        i = np.argmax((np.maximum.accumulate(return_list) - return_list) / np.maximum.accumulate(return_list))  # 结束位置
        if i == 0:
            return 0
        j = np.argmax(return_list[:i])
        return (return_list[j] - return_list[i]) / (return_list[j])

    cash = 400000
    profit_daily_long = deal_lst_list[deal_lst_list["type"] == "sell"]
    profit_daily_static_long = profit_daily_long.groupby(['trade_date']).apply(lambda x: x.profit.sum())
    profit_daily_short = deal_lst_list[deal_lst_list["type"] == "buytocover"]
    profit_daily_static_short = profit_daily_short.groupby(['trade_date']).apply(lambda x: x.profit.sum())
    profit_daily_static = deal_lst_list.groupby(['trade_date']).apply(lambda x: x.profit.sum())
    trade_amount_daily_static = deal_lst_list.groupby(['trade_date']).apply(lambda x: x.trade_amount.sum())

    profit_daily_static_return = (profit_daily_static.cumsum() + cash).pct_change().fillna(0)
    sharp_ratio = profit_daily_static_return.mean() / profit_daily_static_return.std() * 16

    profit_dict = {"profit": profit_daily_static.values}
    df_profit = pd.DataFrame(profit_dict, index=profit_daily_static.index)
    df_profit["short"] = profit_daily_static_short
    df_profit["long"] = profit_daily_static_long
    df_profit.fillna(0, inplace=True)
    profit_df = df_profit['profit'].cumsum() + cash
    profit_df_long = df_profit['long'].cumsum() + cash
    profit_df_short = df_profit['short'].cumsum() + cash

    # 年化收益率计算
    year_return = (profit_df[-1] - cash) / cash * 252 / len(profit_df)
    # 交易胜率
    win_rate = len(profit_daily_static[profit_daily_static.values > 0]) / len(profit_daily_static) * 100
    # 交易最大回撤
    max_drawdown = MaxDrawdown(profit_df)
    # 交易盈亏类型统计
    profit_type_static = deal_lst_list.groupby(['type']).apply(lambda x: x.profit.sum())
    profit_type_win_rate = deal_lst_list.groupby(['type']).apply(lambda x: x[x['profit'] > 0].shape[0]/x.shape[0] * 100)
    # 交易重塑统计
    profit_type_trade_times = deal_lst_list.groupby(['type']).apply(lambda x: int(x.shape[0]))
    # 交易数据汇总
    profit_type_df = pd.DataFrame([profit_type_static, profit_type_win_rate, profit_type_trade_times],
                                  index=["profit", "winRate", "tradeTimes"]).T

    fig = plt.figure(constrained_layout=True, dpi=100, figsize=[19.2, 10.8])
    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.90, hspace=1.5, wspace=0.15)
    gs = GridSpec(5, 3, figure=fig)

    plt.style.use("ggplot")
    ax1 = fig.add_subplot(gs[0:3, :])
    plt.grid(linestyle='-.', axis="both")
    plt.title(u"Trading Pnl", fontsize=18, fontname=['fantasy'])
    plt.xticks(rotation=50)
    plt.xlabel('Trade Date', fontsize=8, fontname=['fantasy'])
    ax1.plot(profit_df.index, profit_df.values, linewidth=2.5, label='Profit All')
    ax1.plot(profit_df_long.index, profit_df_long.values, linewidth=2.5, label='Long Profit')
    ax1.plot(profit_df_short.index, profit_df_short.values, linewidth=2.5, label='Short Profit')
    ax1_2 = ax1.twinx()
    ax1_2.set_ylim(0, (profit_df[-1] - cash) / cash)
    ax1.legend()

    plt.style.use("fivethirtyeight")
    ax2 = fig.add_subplot(gs[3:, :1])
    ax2.tick_params(labelsize=8)
    plt.xticks([])
    plt.title(u"Trade Amount", fontsize=16, fontname=['fantasy'])
    ax2.bar(trade_amount_daily_static.index, trade_amount_daily_static.values, color=['r', 'b'])

    ax3 = fig.add_subplot(gs[3:, 1:2])
    ax3.tick_params(labelsize=8)
    ax3.bar(profit_daily_static_return.index, profit_daily_static_return.values, color=['g'])
    plt.xticks([])
    plt.title(u"Daily Return", fontsize=16, fontname=['fantasy'])
    plt.gca().yaxis.set_major_formatter(FuncFormatter(to_percent))

    ax4 = fig.add_subplot(gs[3:, 2:3])
    plt.grid(b=None)
    plt.title(u"Trading Static", fontsize=16, fontname=['fantasy'])
    ax4.patch.set_alpha(0.5)
    ax4.text(0.05, 0.9, "Sharp Ratio: %.3f" % (sharp_ratio), va="center", ha="left", fontsize=13, fontname=['fantasy'])
    ax4.text(0.05, 0.7, "Net Profit: %.3f" % (profit_df[-1]-cash), va="center", ha="left", fontsize=13,
             fontname=['fantasy'],color="r")
    ax4.text(0.05, 0.5, "Long Profit: %.3f" % (profit_type_df["profit"].loc["sell"]), va="center", ha="left",
             fontsize=13, fontname=['fantasy'])
    ax4.text(0.05, 0.3, "Short Profit: %.3f" % (profit_type_df["profit"].loc["buytocover"]), va="center", ha="left",
             fontsize=13, fontname=['fantasy'])
    ax4.text(0.05, 0.1, "Winning Rate: %.3f" % (win_rate) + "%", va="center", ha="left", fontsize=13,
             fontname=['fantasy'])
    ax4.text(0.95, 0.1, "Annual Return: %.3f" % (year_return*100) + "%", va="center", ha="right",
             fontsize=13, fontname=['fantasy'])
    ax4.text(0.95, 0.7, "Max Drawdown: %.4f" % (max_drawdown*100) + "%", va="center", ha="right", fontsize=13,
             fontname=['fantasy'])
    ax4.text(0.95, 0.5, "Long TradeTimes: %.f" % (len(deal_lst_list[deal_lst_list["type"] == "sell"])),
             va="center", ha="right", fontsize=13, fontname=['fantasy'])
    ax4.text(0.95, 0.3, "Short TradeTimes: %.f" % (len(deal_lst_list[deal_lst_list["type"] == "buytocover"])),
             va="center", ha="right", fontsize=13, fontname=['fantasy'])
    ax4.text(0.95, 0.9, "Commission: %.2f" % (2 * deal_lst_list["commission"].sum()),
             va="center", ha="right", fontsize=13, fontname=['fantasy'])
    ax4.tick_params(labelbottom=False, labelleft=False)

    plt.savefig("test.png")
    plt.show()


def plot_intraday_net_profit_line(dealed_df: DataFrame = None):
    """
    单日交易主笔交易净值走势
    :return:
    """
    profit_lst = []
    cash: int = 1000000
    deal_lst_list = dealed_df
    temp = deal_lst_list.sort_values(by="code")
    amount = deal_lst_list["trade_amount"].sum()
    for deal in list(deal_lst_list["deal_lst"]):
        profit = round(deal[0]["profit"], 2)
        cash = round(cash + profit, 2)
        profit_lst.append(cash)
    print("交易盈亏: {}".format(round(profit_lst[-1] - 1000000, 2)))
    # plt.plot(profit_lst)
    # plt.show()


def stock_profit_static(dealed_df: DataFrame = None):
    """
    个股盈亏统计
    :return:
    """
    # trade_date = datetime.datetime(2020, 7, 15)
    deal_lst_df = dealed_df
    # deal_lst_df = output_periods_order_his()
    temp4 = deal_lst_df[(deal_lst_df["msg"] == "做空止损") | (deal_lst_df["msg"] == "做多止损")]
    # 按照股票日期排序
    temp = deal_lst_df.sort_values(by=['code', "date"]).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # 按盈亏大小排序
    temp2 = deal_lst_df.sort_values(by=['profit']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # 按照开仓时间排序
    temp3 = deal_lst_df.sort_values(by=['open_time']).drop(["msg", "id", "done", "shares", "ttl"], axis=1)
    # temp_30 = temp3[(temp3["open_time"] > "9:30:00") & (temp3["open_time"] < "9:31:00")]["profit"].sum()
    # temp_31 = temp3[(temp3["open_time"] > "9:31:00") & (temp3["open_time"] < "9:32:00")]["profit"].sum()
    # temp_32 = temp3[(temp3["open_time"] > "9:32:00") & (temp3["open_time"] < "9:33:00")]["profit"].sum()
    # temp_33 = temp3[(temp3["open_time"] > "9:33:00") & (temp3["open_time"] < "9:34:00")]["profit"].sum()
    # temp_34 = temp3[(temp3["open_time"] > "9:34:00") & (temp3["open_time"] < "9:35:00")]["profit"].sum()
    profit_code_static = deal_lst_df.groupby(['code']).apply(lambda x: x.profit.sum())
    x_data = [str(x) for x in list(profit_code_static.keys())]
    y_data = list(profit_code_static)
    plt.bar(x=x_data, height=y_data, label='个股盈亏统计', color='steelblue', alpha=1)
    plt.xticks(rotation=90)
    plt.subplots_adjust(top=0.96, bottom=0.06, left=0.05, right=0.95, hspace=0.1, wspace=0)
    plt.show()


