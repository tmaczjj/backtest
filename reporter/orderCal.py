import json
import datetime
import pandas as pd
from utils.utils import get_order_json_list
from utils.utils import get_order_single_json


def output_periods_order_his():
    order_list = get_order_json_list()
    print(order_list)
    for order_json in order_list:
        with open(order_json, "r") as rf:
            data = pd.read_json(order_json)
            print(data)


def output_intraday_order_his():
    trade_date = datetime.datetime(2020, 6, 3)
    order_json = get_order_single_json(trade_date)
    with open(order_json, "r") as rf:
        data = pd.read_json(order_json)
        print(data)


output_periods_order_his()


