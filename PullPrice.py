import numpy
import pandas as pd
import datetime
from pandas.tseries.offsets import BDay
from datetime import date
from nsepy import get_history

curr_day = datetime.datetime.today()
prev_day = curr_day - BDay(5)

sbin = get_history(symbol='SBIN', start=prev_day, end=curr_day)

