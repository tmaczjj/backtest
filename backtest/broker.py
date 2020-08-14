# -*- coding: utf-8 -*-
# from collections import defaultdict
from abc import ABC, abstractmethod
from collections import defaultdict
from .utils import loggerFunc


class Base(ABC):
    """交易平台的基类"""

    def initialize(self):
        pass

    @abstractmethod
    def buy(self, code, shares, price=None, msg=None):
        pass

    @abstractmethod
    def sell(self, code, shares, price=None, msg=None):
        pass

    @abstractmethod
    def sellshort(self, code, shares, price=None, msg=None):
        """ 卖出做空 """
        pass

    @abstractmethod
    def buytocover(self, code, shares, price=None, msg=None):
        """ 买入平空 """
        pass

    @abstractmethod
    def run(self, tick):
        pass

    def finish(self):
        pass


class BackTestBroker(Base):
    """
    由于回测的虚拟交易平台。
    默认以当前bar的收盘价买入，即使是15:00的时间也能买入！
    因为这里假设交易成交价在电脑下单的情况下时间极短，价格波动极短，所以回测忽略此波动。

    Parameters:
    ----------
      cash:int
            初始资金
      cm_rate:float
            交易手续费率
      deal_price:str
            用于回测的股价类型(open, high, low, close), 默认为close

    回测示例
                            buy     sell    pos         total
    broker      2012-01-04  1
    backtest    2012-01-04  1
    broker      2012-01-05  1               +100        100
    backtest    2012-01-05  2
    broker      2012-01-06  2               +100        200
    backtest    2012-01-06  3       4
    broker      2012-01-09  3       4       +100/-200   100
    backtest    2012-01-09  5
    broker      2012-01-20  5               +100        100
    backtest    2012-01-20  6       7
    broker      2012-01-30  6       7       +100/-200   100
    backtest    2012-01-30  8
    """

    def __init__(self, cash, cm_rate=0.0014, deal_price="close"):
        """
        postion: {
                "code": [{
                    "price": 持仓价格,
                    "date": 建仓时间,
                    "shares": 头寸数量,
                    "commission", 持仓手续费
                    },...]}
        """
        self.cash = cash
        self.available_cash = cash
        self.cm_rate = cm_rate
        self.order_lst = []
        self.order_hist_lst = []
        self.deal_price = deal_price
        # 持仓
        self.position = defaultdict(list)
        # 用于跟踪交易订单情况
        self._id = 0

    def run(self, tick):
        tick_data = self.ctx["tick_data"]

        new_order_lst = []
        for order in self.order_lst:
            if order["ttl"] == 0:
                if not order["done"]:
                    self.ctx.bt.on_order_timeout(order)
                continue

            # 每一轮tick将ttl减一，用于控制订单超时
            if order["ttl"] > 0:
                order["ttl"] -= 1

            # 如果当前tick，该股票有报价
            if order["code"] in tick_data:
                self.execute(order, tick_data)

            new_order_lst.append(order)
        self.order_lst = new_order_lst

    def execute(self, order):
        """执行有效状态的订单"""
        # TODO:
        # 可以将买卖逻辑抽离出来用额外的两个函数_buy,_sell函数单独处理
        self.order_hist_lst.append(order)
        trade_time = self.ctx["now"]
        tick_data = self.ctx["tick_data"]
        order_code = order["code"]
        order_price = order["price"]
        order_shares = order["shares"]
        stock_info = tick_data[order_code]
        stock_price = stock_info[self.deal_price]

        if order_price is None:
            order_price = stock_price

        if order["type"] == "buy" and order_price >= stock_price:
            trade_price = stock_price
            cost = trade_price * order["shares"]
            commission = cost * self.cm_rate
            if commission < 5:
                commission = 5

            if cost + commission > self.cash:
                # TODO:
                # 完成部分成交逻辑
                self.logger.info("{}: 资金余额不足".format(trade_time))
                return

            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            deal = {"open_id": order["id"],
                    "open_price": stock_price,
                    "open_date": self.ctx.now,
                    "commission": commission,
                    "shares": order["shares"]}

            pos = {"open_id": order["id"],
                   "open_price": stock_price,
                   "open_date": self.ctx.now,
                   "shares": order["shares"]}

            self.cash = self.cash - cost - commission
            order["deal_lst"].append(deal)
            self.position[order_code].append(pos)

            order["ttl"] = 0
            order["done"] = True
            self.ctx.bt.on_deal(order)

        elif order["type"] == "sell" and order_price <= stock_price and order_code in self.position:
            trade_price = stock_price
            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            tmp = order_shares
            deal_lst = []
            commission = 0
            new_pos_lst = []
            for pos in self.position[order_code]:
                time_diff = order["date"] - pos["open_date"]
                # 15:00 - 09:30 = 19800 secs
                # A股T+1交易
                if time_diff.total_seconds() <= 19800:
                    return

                if tmp == 0:
                    new_pos_lst.append(pos)
                    continue

                time_diff = self.ctx.now - pos["open_date"]
                # 防止对当天完成的交易进行交易
                if time_diff.total_seconds() <= 19800:
                    new_pos_lst.append(pos)
                    continue

                if pos["shares"] <= tmp:
                    # 计算手续费等
                    new_cash = pos["shares"] * trade_price
                    commission += new_cash * self.cm_rate
                    deal_lst.append({
                                    "open_id": pos["open_id"],
                                    "open_price": pos["open_price"],
                                    "open_date": pos["open_date"],
                                    "close_id": order["id"],
                                    "close_price": trade_price,
                                    "close_date": self.ctx.now,
                                    "commission": None,
                                    "shares": pos["shares"],
                                    "profit": None})

                    tmp -= pos["shares"]
                else:
                    # 计算手续费等
                    new_cash = tmp * trade_price
                    commission += new_cash * self.cm_rate
                    deal_lst.append({
                                    "open_id": pos["open_id"],
                                    "open_price": pos["open_price"],
                                    "open_date": pos["open_date"],
                                    "close_id": order["id"],
                                    "close_price": trade_price,
                                    "close_date": self.ctx.now,
                                    "commission": None,
                                    "shares": tmp,
                                    "profit": None})

                    pos["shares"] -= tmp
                    tmp = 0
                    new_pos_lst.append(pos)

            # 防止刚好仓位为0并且tmp == 0
            if tmp == 0:
                order["ttl"] = 0
                order["done"] = True

            if new_pos_lst:
                self.position[order_code] = new_pos_lst
            else:
                self.position.pop(order_code)

            order["shares"] = tmp
            if commission < 5:
                commission = 5

            deal_shares = sum([deal["shares"] for deal in deal_lst])
            for deal in deal_lst:
                deal["commission"] = commission * (deal["shares"] / deal_shares)
                deal["profit"] = (deal["close_price"] - deal["open_price"]) * deal["shares"] - deal["commission"]
                new_cash = deal["shares"] * deal["close_price"]
                self.cash = self.cash + new_cash
            

            self.cash -= commission
            order["deal_lst"].extend(deal_lst)
            self.ctx.bt.on_deal(order)


    @property
    def stock_value(self):
        value = 0
        for code in self.position:
            latest_price = self.ctx.latest_price[code]
            for pos in self.position[code]:
                value += pos["shares"] * latest_price

        return value

    @property
    def assets_value(self):
        return self.cash + self.stock_value

    def get_shares(self, code):
        """返回指定股票代码的持仓数量"""
        return sum([pos["shares"] for pos in self.position[code]])

    def get_drapdown(self):
        """返回最大回撤"""
        pass

    def get_return(self):
        """计算年化收益"""
        pass

    def submit(self, order):
        self.order_lst.append(order)
        self.order_hist_lst.append(order)

    def buy(self, code, shares, price=None, msg=None):
        # TODO:
        # 设置可用资金或者是订单提交过程同步, 不然会有提交过多的购买订单，而没有现金购买
        """
        提交买入订单

        Parameters
        ---------
        code : str
            股票代码
        price : float or None
            最高可买入的价格, 如果为None则按市价买入
        shares : int
            买入股票数量
        msg : str
            额外的信息, 用于跟踪买入的原因

        Returns
        ---------
        dict
             {
                "id": 订单ID,
                "type": 订单类型, "buy",
                "code": 股票代码,
                "date": 提交日期,
                "shares": 目标股份数量,
                "price": 目标价格,
                "done": 是否完成, 默认为False,
                "msg": 买入信号一,
                "deal_lst": 交易成功的历史数据，如
                    [{
                      "open_id": 订单ID,
                      "open_price": 成交价格,
                      "open_date": 成交时间,
                      "commission": 交易手续费,
                      "shares": 成交份额
                    }]
                ""
            }
        """
        if shares % 100 != 0:
            raise ValueError("买入股票数量只能是100的整数倍")
        if shares <= 0:
            raise ValueError("买入股票数量必须大于0")
        
        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]
        
        order = {
            "id": self._id,
            "type": "buy",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        self.logger.info("{} 柜台接受[{}]买入委托".format(self.ctx["now"], code))
        self.execute(order)
        return order

    def sell(self, code, shares, price=None, msg=None):
        """
        提交卖出订单

        Parameters
        ---------
        code : str
            股票代码
        price : float or None
            最低可卖出的价格, 如果为None则按市价卖出
        shares : int
            卖出股票数量
        msg : str
            额外的信息, 用于跟踪卖出的原因

        Returns
        ---------
        dict
             {
                "id": 订单ID,
                "type": 订单类型, "sell",
                "code": 股票代码,
                "date": 提交日期,
                "shares": 目标股份数量,
                "init_shares": 最初请求交易份额,
                "price": 目标价格,
                "done": 是否完成, 默认为False,
                "msg": 卖出信号一,
                "deal_lst": 交易成功的历史数据，如
                    [{
                      "open_id": 开仓订单ID,
                      "open_price": 开仓价格,
                      "open_date": 持仓时间,
                      "close_price": 成交价格,
                      "close_date": 成交时间,
                      "close_id": 平仓订单ID,
                      "commission": 交易手续费,
                      "shares": 成交份额,
                      "profit": 交易收益}]
                ""
            }
        """
        if shares % 100 != 0:
            raise ValueError("买入股票数量只能是100的整数倍")

        if code not in self.position:
            return

        pos_date_lst = [pos["open_date"] for pos in self.position[code]]
        time_diff = self.ctx.now - min(pos_date_lst)
        # if time_diff.total_seconds() <= 21600:
        #     return

        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]
        order = {
            "id": self._id,
            "type": "sell",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": shares,
            "init_shares": shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        self.logger.info("{} 柜台接受[{}]卖出委托".format(self.ctx["now"], code))
        self.execute(order)
        return order

    def sellshort(self, code, shares, price=None, msg=None):
        """ 卖出做空 """
        pass

    def buytocover(self, code, shares, price=None, msg=None):
        """ 买入平空 """
        pass

    def sell_all(self, code, **kwargs):
        """
        清空所有持仓

        Parameters
        ---------
        Parameters:
        code:str
            股票代码
        price:float or None
            最低可卖出的价格, 如果为None则按市价卖出
        kwargs:
            传递给sell的函数

        Returns
        ---------
        dict
            返回提交的订单

        """
        if code in self.position:
            shares = self.get_shares(code)
            return self.sell(code, shares, **kwargs)

    # def stop_loss(self, code, price):
    #     """止损

    #     当价格低于指定价格卖出所有股票
    #     """
    #     self.sell_all(code, price)
    # def stop_profit(self, code, price):
    #     """止盈"""
    #     if code in self._pos_dict:
    #         shares = self._pos_dict[code].shares

    #     self.sell(code, price, shares)


class T0BackTestBroker(Base):
    """
    由于回测的虚拟交易平台。
    默认以当前bar的收盘价买入，即使是15:00的时间也能买入！
    因为这里假设交易成交价在电脑下单的情况下时间极短，价格波动极短，所以回测忽略此波动。

    Parameters:
    ----------
      cash:int
            初始资金
      cm_rate:float
            交易手续费率
      deal_price:str
            用于回测的股价类型(open, high, low, close), 默认为close

    回测示例
                            buy     sell    pos         total
    broker      2012-01-04  1
    backtest    2012-01-04  1
    broker      2012-01-05  1               +100        100
    backtest    2012-01-05  2
    broker      2012-01-06  2               +100        200
    backtest    2012-01-06  3       4
    broker      2012-01-09  3       4       +100/-200   100
    backtest    2012-01-09  5
    broker      2012-01-20  5               +100        100
    backtest    2012-01-20  6       7
    broker      2012-01-30  6       7       +100/-200   100
    backtest    2012-01-30  8
    """

    """
    # 订单结构
    Parameters
    ---------
    code : str
        股票代码
    price : float or None
        最高可买入的价格, 如果为None则按市价买入
    shares : int
        买入股票数量
    msg : str
        额外的信息, 用于跟踪买入的原因

    Returns
    ---------
    dict
         {
            "id": 订单ID,
            "type": 订单类型, "buy",
            "code": 股票代码,
            "date": 提交日期,
            "shares": 目标股份数量,
            "price": 目标价格,
            "done": 是否完成, 默认为False,
            "msg": 买入信号一,
            "deal_lst": 交易成功的历史数据，如
                [{
                  "open_id": 订单ID,
                  "open_price": 成交价格,
                  "open_date": 成交时间,
                  "commission": 交易手续费,
                  "shares": 成交份额
                }]
            ""
        }
    """
    def __init__(self, cash, cm_rate=0.0007, deal_price="close", logfile=None):
        """
        postion: {
                "code": [{
                    "price": 持仓价格,
                    "date": 建仓时间,
                    "shares": 头寸数量,
                    "commission", 持仓手续费
                    },...]}
        """
        self.cash = cash
        self.available_cash = cash
        self.cm_rate = cm_rate
        self.order_lst = []
        self.order_hist_lst = []
        self.deal_price = deal_price
        # 持仓
        self.position = defaultdict(list)
        self.logger = loggerFunc(logfile)
        # 用于跟踪交易订单情况
        self._id = 0

    def run(self, tick):
        tick_data = self.ctx["tick_data"]

        new_order_lst = []
        for order in self.order_lst:
            if order["ttl"] == 0:
                if not order["done"]:
                    self.ctx.bt.on_order_timeout(order)
                continue

            # 每一轮tick将ttl减一，用于控制订单超时
            if order["ttl"] > 0:
                order["ttl"] -= 1

            # 如果当前tick，该股票有报价
            if order["code"] in tick_data:
                self.execute(order, tick_data)

            new_order_lst.append(order)
        self.order_lst = new_order_lst

    def execute(self, order):
        """执行有效状态的订单"""
        # TODO:
        # 可以将买卖逻辑抽离出来用额外的两个函数_buy,_sell函数单独处理
        self.order_hist_lst.append(order)
        trade_time = self.ctx["now"]
        tick_data = self.ctx["tick_data"]
        order_code = order["code"]
        order_price = order["price"]
        order_shares = order["shares"]
        stock_info = tick_data[order_code]
        if stock_info["LastPrice"] != 0:
            stock_price = stock_info["LastPrice"]
        else:
            stock_price = max(stock_info["AskPrice1"], stock_info["BidPrice1"])

        if order_price is None:
            order_price = stock_price

        if order["type"] == "buy" and order_price >= stock_price:
            trade_price = stock_price
            cost = trade_price * order["shares"]
            commission = round(cost * self.cm_rate, 2)
            if commission < 5:
                commission = 5

            if cost + commission > self.cash:
                # TODO:
                # 完成部分成交逻辑
                self.logger.info("{}: 资金余额不足".format(trade_time))
                return

            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            deal = {"open_id": order["id"],
                    "open_price": stock_price,
                    "open_date": self.ctx.now,
                    "commission": commission,
                    "shares": order["shares"]}

            pos = {"open_id": order["id"],
                   "open_price": stock_price,
                   "open_date": self.ctx.now,
                   "shares": order["shares"]}

            self.cash = self.cash - cost - commission
            order["deal_lst"].append(deal)
            self.position[order_code].append(pos)

            order["ttl"] = 0
            order["done"] = True
            self.ctx.bt.on_deal(order)

        elif order["type"] == "sell" and order_price <= stock_price and order_code in self.position:
            trade_price = stock_price
            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            tmp = order_shares
            deal_lst = []
            commission = 0
            new_pos_lst = []
            for pos in self.position[order_code]:
                if tmp == 0:
                    new_pos_lst.append(pos)
                    continue

                if pos["shares"] <= tmp:
                    # 计算手续费等
                    new_cash = pos["shares"] * trade_price
                    commission += round(new_cash * self.cm_rate, 2)
                    deal_lst.append({
                        "open_id": pos["open_id"],
                        "open_price": pos["open_price"],
                        "open_date": pos["open_date"],
                        "close_id": order["id"],
                        "close_price": trade_price,
                        "close_date": self.ctx.now,
                        "commission": None,
                        "shares": pos["shares"],
                        "profit": None})

                    tmp -= pos["shares"]
                else:
                    # 计算手续费等
                    new_cash = tmp * trade_price
                    commission += round(new_cash * self.cm_rate, 2)
                    deal_lst.append({
                        "open_id": pos["open_id"],
                        "open_price": pos["open_price"],
                        "open_date": pos["open_date"],
                        "close_id": order["id"],
                        "close_price": trade_price,
                        "close_date": self.ctx.now,
                        "commission": None,
                        "shares": tmp,
                        "profit": None})

                    pos["shares"] -= tmp
                    tmp = 0
                    new_pos_lst.append(pos)

            # 防止刚好仓位为0并且tmp == 0
            if tmp == 0:
                order["ttl"] = 0
                order["done"] = True

            if new_pos_lst:
                self.position[order_code] = new_pos_lst
            else:
                self.position.pop(order_code)

            order["shares"] = tmp
            deal_shares = sum([deal["shares"] for deal in deal_lst])
            for deal in deal_lst:
                deal["commission"] = round(commission * (deal["shares"] / deal_shares), 2)
                deal["profit"] = (deal["close_price"] - deal["open_price"]) * deal["shares"] - deal["commission"]
                new_cash = deal["shares"] * deal["close_price"]
                self.cash = self.cash + new_cash

            self.cash -= commission
            order["deal_lst"].extend(deal_lst)
            self.ctx.bt.on_deal(order)

        elif order["type"] == "sellshort" and order_price <= stock_price:
            trade_price = stock_price
            cost = -1 * trade_price * order["shares"]
            commission = round(cost * self.cm_rate)

            # if cost + commission > self.cash:
            #     # TODO:
            #     # 完成部分成交逻辑
            #     self.logger.info("{}: 资金余额不足".format(trade_time))
            #     return

            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            deal = {"open_id": order["id"],
                    "open_price": stock_price,
                    "open_date": self.ctx.now,
                    "commission": commission,
                    "shares": order["shares"]}

            pos = {"open_id": order["id"],
                   "open_price": stock_price,
                   "open_date": self.ctx.now,
                   "shares": order["shares"]}

            self.cash = self.cash + cost - commission
            order["deal_lst"].append(deal)
            self.position[order_code].append(pos)

            order["ttl"] = 0
            order["done"] = True
            self.ctx.bt.on_deal(order)

        elif order["type"] == "buytocover" and order_price >= stock_price and order_code in self.position:
            trade_price = stock_price
            # 符合条件开始交易
            if not self.ctx.bt.before_trade(order):
                return

            tmp = -1 * order_shares
            deal_lst = []
            commission = 0
            new_pos_lst = []
            for pos in self.position[order_code]:
                if tmp == 0:
                    new_pos_lst.append(pos)
                    continue

                if pos["shares"] >= tmp:
                    # 计算手续费等
                    new_cash = pos["shares"] * trade_price
                    commission += round(abs(new_cash * self.cm_rate),2)
                    deal_lst.append({
                        "open_id": pos["open_id"],
                        "open_price": pos["open_price"],
                        "open_date": pos["open_date"],
                        "close_id": order["id"],
                        "close_price": trade_price,
                        "close_date": self.ctx.now,
                        "commission": None,
                        "shares": abs(pos["shares"]),
                        "profit": None})

                    tmp -= pos["shares"]
                else:
                    # 计算手续费等
                    new_cash = tmp * trade_price
                    commission += round(new_cash * self.cm_rate, 2)
                    deal_lst.append({
                        "open_id": pos["open_id"],
                        "open_price": pos["open_price"],
                        "open_date": pos["open_date"],
                        "close_id": order["id"],
                        "close_price": trade_price,
                        "close_date": self.ctx.now,
                        "commission": None,
                        "shares": tmp,
                        "profit": None})

                    pos["shares"] -= tmp
                    tmp = 0
                    new_pos_lst.append(pos)

            # 防止刚好仓位为0并且tmp == 0
            if tmp == 0:
                order["ttl"] = 0
                order["done"] = True

            if new_pos_lst:
                self.position[order_code] = new_pos_lst
            else:
                self.position.pop(order_code)

            order["shares"] = tmp

            deal_shares = sum([deal["shares"] for deal in deal_lst])
            for deal in deal_lst:
                deal["commission"] = round(commission * (deal["shares"] / deal_shares), 2)
                deal["profit"] = (deal["open_price"] - deal["close_price"]) * deal["shares"] - deal["commission"]
                new_cash = deal["shares"] * deal["close_price"]
                self.cash = self.cash - new_cash

            self.cash -= commission
            order["deal_lst"].extend(deal_lst)
            self.ctx.bt.on_deal(order)

    @property
    def stock_value(self):
        value = 0
        for code in self.position:
            latest_price = self.ctx.latest_price[code]
            for pos in self.position[code]:
                value += pos["shares"] * latest_price
        return value

    @property
    def assets_value(self):
        return self.cash + self.stock_value

    def get_shares(self, code):
        """返回指定股票代码的持仓数量"""
        return sum([pos["shares"] for pos in self.position[code]])

    def get_drapdown(self):
        """返回最大回撤"""
        pass

    def get_return(self):
        """计算年化收益"""
        pass

    def submit(self, order):
        self.order_lst.append(order)
        self.order_hist_lst.append(order)

    def buy(self, code, shares, price=None, msg=None):
        if shares % 100 != 0:
            raise ValueError("买入开仓数量只能是100的整数倍")
        if shares <= 0:
            raise ValueError("买入开仓股票数量必须大于0")

        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]

        order = {
            "id": self._id,
            "type": "buy",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        # self.logger.info("{trade_time} 柜台接受[{stock_code}]买入委托".format(trade_time=self.ctx["now"], stock_code=code))
        self.execute(order)
        return order

    def sell(self, code, shares, price=None, msg=None):
        if shares % 100 != 0:
            raise ValueError("卖出平仓股票数量只能是100的整数倍")

        if shares <= 0:
            raise ValueError("卖出平仓股票数量必须大于0")

        if code not in self.position:
            raise ValueError("{stock_code}并未持多仓，平多失败".format(stock_code=code))

        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]

        order = {
            "id": self._id,
            "type": "sell",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": shares,
            "init_shares": shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        # self.logger.info("{trade_time} 柜台接受[{stock_code}]卖出委托".format(trade_time=self.ctx["now"], stock_code=code))
        self.execute(order)
        return order

    def sellshort(self, code, shares, price=None, msg=None):
        if shares % 100 != 0:
            raise ValueError("卖空开仓股票数量只能是100的整数倍")

        if shares <= 0:
            raise ValueError("卖空开仓股票数量必须大于0")

        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]

        order = {
            "id": self._id,
            "type": "sellshort",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": -1 * shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        # self.logger.info("{trade_time} 柜台接受[{stock_code}]卖空委托".format(trade_time=self.ctx["now"], stock_code=code))
        self.execute(order)
        return order

    def buytocover(self, code, shares, price=None, msg=None):
        if shares % 100 != 0:
            raise ValueError("买入平仓股票数量只能是100的整数倍")

        if shares <= 0:
            raise ValueError("买入平仓股票数量必须大于0")

        if code not in self.position:
            raise ValueError("{stock_code}并未持空仓，平空失败".format(stock_code=code))

        self._id += 1
        if price is None:
            price = self.ctx.latest_price[code]
        order = {
            "id": self._id,
            "type": "buytocover",
            "code": code,
            "date": self.ctx.now,
            "msg": msg,
            "shares": shares,
            "init_shares": shares,
            "price": price,
            "done": False,
            "deal_lst": []
        }
        # self.logger.info("{trade_time} 柜台接受[{stock_code}]平空委托".format(trade_time=self.ctx["now"], stock_code=code))
        self.execute(order)

        return order

    # def stop_loss(self, code, price):
    #     """止损

    #     当价格低于指定价格卖出所有股票
    #     """
    #     self.sell_all(code, price)
    # def stop_profit(self, code, price):
    #     """止盈"""
    #     if code in self._pos_dict:
    #         shares = self._pos_dict[code].shares

    #     self.sell(code, price, shares)
