from reporter.orderCal import output_periods_order_his as opo
from reporter.orderCal2 import output_periods_order_his as opo2
from pandas.testing import assert_frame_equal
import pandas as pd
deal_lst_1 = opo()
deal_lst_2 = opo2()
assert_frame_equal(deal_lst_1, deal_lst_2)
