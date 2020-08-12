# -*- coding: utf-8 -*-
from backtest.backtest import BackTest
from datetime import datetime
import json
from backtest.backtest import ArrayManager
from utils.utils import load_daily_price, load_share_mongo
from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)


class BreakStrategy(BackTest):
    """
    set params before tda
    """
    break_volume_base = 400
    stock_price_base = 10
    stop_win_rate = 10
    market_time_start = "09:30:03"
    trade_time_start = "09:30:10"
    trade_time_end = "09:33:00"
    market_time_end = "09:34:56"

    stock_buy_power = {}
    stock_sell_power = {}
    traded_list = []
    ordered_code = []
    win_dict = {}

    def __init__(self, stocklist=None, trade_date=None, cash=1000000, broker=None, enable_stat=True, codeDict=None):
        super().__init__(stocklist, trade_date, cash=cash, broker=broker, enable_stat=enable_stat)
        self.am = {}
        self.stg_data = {}
        self.codeDict = codeDict
        self.stocklist = self.stockFliter(stocklist)

    def initialize(self):
        for stock in self.stocklist:
            self.am[stock] = ArrayManager()
            self.stock_buy_power[stock] = 0
            self.stock_sell_power[stock] = 0

        self.info("Strategy--{}--策略初始化完成".format(self.__class__.__name__))

    def on_tick(self, tick):
        tick_data = self.ctx["tick_data"]
        hold_position = self.ctx["broker"].position
        tick_time = str(tick.strftime("%H:%M:%S"))
        for code, market_data in tick_data.items():
            self.am[code].update(market_data)
            trade_volume = self.am[code].volume
            trade_amount = self.am[code].amount
            if trade_volume[-3] > 0 and trade_volume[-2] > 0 and trade_volume[-1] > 0:
                cond_trade_amount = (trade_volume[-1] + trade_volume[-2] + trade_volume[-3]) > self.stg_data[code]
            else:
                cond_trade_amount = False
            # ----------------------------------------------------------------------------------------------------
            # tick价格计算
            # tick_price = tick_amount / tick_volume
            # 当计算出现错误时 取买一卖一均价
            try:
                trade_current_avg_price = round(trade_amount[-1] / (trade_volume[-1] * 100), 2)
            except:
                # print(self.trade_date)
                trade_current_avg_price = round((self.am[code].AskPrice1[-1] + self.am[code].BidPrice1[-1]) / 2, 2)

            # ----------------------------------------------------------------------------------------------------
            bid_book = {market_data.BidPrice1: market_data.BidVolume1, market_data.BidPrice2: market_data.BidVolume2,
                        market_data.BidPrice3: market_data.BidVolume3, market_data.BidPrice4: market_data.BidVolume4,
                        market_data.BidPrice5: market_data.BidVolume5}

            ask_book = {market_data.AskPrice1: market_data.AskVolume1, market_data.AskPrice2: market_data.AskVolume2,
                        market_data.AskPrice3: market_data.AskVolume3, market_data.AskPrice4: market_data.AskVolume4,
                        market_data.AskPrice5: market_data.AskVolume5}
            best_bid_price = max(zip(bid_book.values(), bid_book.keys()))[1]
            best_ask_price = max(zip(ask_book.values(), ask_book.keys()))[1]

            # -----------------------------------  卖出  -----------------------------------------#
            if code in hold_position:
                stock_hold_info = hold_position[code][0]
                hold_num = int(stock_hold_info["shares"])
                open_price = stock_hold_info["open_price"]
                stop_win_long_price = open_price * (100 + self.stop_win_rate) / 100
                stop_win_short_price = open_price * (100 + self.stop_win_rate) / 100

            # 跟踪止盈设定
                # -------------------------  reach to the stop-win-price -----------------------------#
                if code not in self.win_dict.keys():
                    # 做多初始止盈价格设置
                    if hold_num > 0 and trade_current_avg_price > stop_win_long_price:
                        self.win_dict[code] = best_bid_price
                    # 做空初始止盈价格设置
                    if hold_num < 0 and trade_current_avg_price < stop_win_short_price:
                        self.win_dict[code] = best_ask_price

                # -------------------------  update the stop-win-price -----------------------------#
                elif code in self.win_dict.keys():
                    # 做多止盈价格更新
                    if hold_num > 0 and best_bid_price > self.win_dict[code]:
                        self.win_dict[code] = best_bid_price

                    # 做空止盈价格更新
                    if hold_num < 0 and best_ask_price < self.win_dict[code]:
                        self.win_dict[code] = best_ask_price

                if self.trade_time_start < tick_time < self.trade_time_end:
                    # -----------------------------  盘中止盈 ----------------------------------#
                    cond5 = self.am[code].last_price[-1] < self.am[code].last_price[-2]
                    cond6 = self.am[code].last_price[-1] > self.am[code].last_price[-2]
                    # 做多止盈
                    if hold_num > 0 and code in self.win_dict.keys():
                        if cond5 and trade_current_avg_price < self.win_dict[code]:
                            self.ctx.broker.sell(code, hold_num, round(trade_current_avg_price-1, 2), msg="做多平仓")
                            return
                    # 做空止盈
                    if hold_num < 0 and code in self.win_dict.keys():
                        if cond6 and trade_current_avg_price > self.win_dict[code]:
                            self.ctx.broker.buytocover(code, abs(hold_num), round(trade_current_avg_price+1, 2), msg="做空平仓")
                            return
                    # -----------------------------  盘中止损 ----------------------------------#
                    # open_price = stock_hold_info["open_price"]
                    # long_stop_price = open_price * (100 - self.stop_loss_rate) / 100
                    # short_stop_price = open_price * (100 + self.stop_loss_rate) / 100
                    # if hold_num < 0:
                    #     if trade_price > short_stop_price:
                    #         self.ctx.broker.buytocover(code, abs(hold_num), round(trade_price+1, 2), msg="做空止损")
                    # if hold_num > 0:
                    #     if trade_price < long_stop_price:
                    #         self.ctx.broker.sell(code, hold_num, round(trade_price-1, 2), msg="做多止损")

                # -----------------------------  尾盘平仓 ----------------------------------#
                if tick_time >= self.market_time_end:
                    if hold_num < 0:
                        self.ctx.broker.buytocover(code, abs(hold_num), round(trade_current_avg_price+1, 2), msg="做空平仓")
                    if hold_num > 0:
                        self.ctx.broker.sell(code, hold_num, round(trade_current_avg_price-1, 2), msg="做多平仓")

            # -----------------------------------  开仓  -----------------------------------------#
            if self.trade_time_start < tick_time < self.trade_time_end:
                if cond_trade_amount:
                    if code not in hold_position and code not in self.traded_list:
                        try:
                            trade_current_avg_price = round(trade_amount[-1] / (trade_volume[-1] * 100), 2)
                        except:
                            trade_current_avg_price = round((self.am[code].AskPrice1[-1] +
                                                             self.am[code].BidPrice1[-1]) / 2, 2)
                        try:
                            trade_last_avg_price = round(trade_amount[-2] / (trade_volume[-2] * 100), 2)
                        except:
                            trade_last_avg_price = round((self.am[code].AskPrice1[-2] +
                                                          self.am[code].BidPrice1[-2]) / 2, 2)
                        try:
                            trade_last_before_last_avg_price = round(trade_amount[-3] / (trade_volume[-3] * 100), 2)
                        except:
                            trade_last_before_last_avg_price = round((self.am[code].AskPrice1[-3] +
                                                                      self.am[code].BidPrice1[-3]) / 2, 2)

                        # trade_amount = int(round(int(20000 / trade_current_avg_price) / 100) * 100)
                        trade_amount = int(self.codeDict[code])
                        current_sum_ask_volume = market_data.AskVolume1 + market_data.AskVolume2 + \
                            market_data.AskVolume3 + market_data.AskVolume4 + market_data.AskVolume5

                        current_sum_bid_volume = market_data.BidVolume1 + market_data.BidVolume2 + \
                            market_data.BidVolume3 + market_data.BidVolume4 + market_data.BidVolume5

                        # 做多条件
                        cond1 = trade_current_avg_price > trade_last_avg_price > trade_last_before_last_avg_price
                        cond_ask_bid_buy = current_sum_bid_volume > current_sum_ask_volume * 2

                        if cond1 and cond_ask_bid_buy:
                            self.ctx.broker.buy(code, trade_amount, round(trade_current_avg_price+1, 2), msg="买入开仓")
                            self.traded_list.append(code)

                        # 做空条件
                        cond2 = trade_current_avg_price < trade_last_avg_price < trade_last_before_last_avg_price
                        cond_ask_bid_sell = current_sum_bid_volume * 2 < current_sum_ask_volume

                        if cond2 and cond_ask_bid_sell:
                            self.ctx.broker.sellshort(code, trade_amount, round(trade_current_avg_price-1, 2), msg="卖出开仓")
                            self.traded_list.append(code)

    def on_deal(self, order):
        pass
        # self.info("{stock_code}{trade_type}成交，成交价格{deal_price}".format(
        #     stock_code=order["code"], trade_type=order["msg"], deal_price=order["price"]))

    def on_order_ok(self, order):
        pass

    def finish(self):
        pass

    def stockFliter(self, stocklist):
        """
        股票筛选模块
        实现每日股票筛选
        若不需要筛选 直接return self.stocklist

        :return:     list:需要交易的股票
        """
        stock_list = self.stocklist
        local_stock_list = [x + ".SH" if x.startswith("6") else x + ".SZ" for x in stock_list]
        daily_price_df = load_daily_price(local_stock_list, self.trade_date)
        df_fliter = daily_price_df[daily_price_df["close"] > self.stock_price_base]
        fliterred_list = list(df_fliter["code"])
        stock_trade_list = [x.split(".", 1)[0] for x in fliterred_list]
        stock_trade_list_final = []
        for stock in stock_trade_list:
            break_point = self.break_volume_cal(stock)
            if break_point >= self.break_volume_base:
                self.stg_data[stock] = int(break_point)
                stock_trade_list_final.append(stock)
        ORDER_FILE_ROUTE = "reporter/stg_data/period_days/" + self.trade_date.strftime("%Y%m%d") + ".json"
        with open(ORDER_FILE_ROUTE, 'w') as f:
            json.dump({self.trade_date.strftime("%Y%m%d"): self.stg_data}, f, indent=4, default=str)
        return stock_trade_list_final

    def break_volume_cal(self, stock):
        import tushare as ts
        df_yd = ts.get_tick_data(stock, date=self.trade_date_str, src='tt')
        stock_volume = df_yd["volume"]
        volume_value = stock_volume.quantile(0.995)
        # 本地获取数据
        # df_yd = load_share_mongo(stock, self.trade_date)
        # if len(df_yd) > 0:
        #     stock_volume = df_yd["TradeVolume"]
        #     volume_value = int(stock_volume.quantile(0.995))
        # else:
        #     volume_value = 0
        return volume_value