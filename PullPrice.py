import glob
import numpy
import pandas as pd
import nsepy
import datetime
from pandas.tseries.offsets import BDay
from datetime import date
from nsepy import get_history


def get_investments():
    # get all the portfolio files and store them in input directory.

    input_files = glob.glob('data/input/*.csv')
    li = []

    # read and concat all input files
    for filename in input_files:
        concat_investments = pd.read_csv(filename, index_col=None, header=0)
        li.append(concat_investments)

    # concat to a dataframe and clean up duplicates and extra columns
    investments = pd.concat(li, axis=0, ignore_index=True)
    investments.drop_duplicates(subset='Symbol', keep='first', inplace=True)
    investments[['ticker','exchange']] = investments['Symbol'].str.split('.',n=1, expand=True)
    investments.set_index('ticker', inplace=True)
    investments.drop(investments.columns[:-1], axis=1, inplace=True)
    investments.to_csv('data/investments.csv')
    # investments will have the ticker and normalized peak / high

    return


def update_meta():
    update_investments = pd.read_csv('data/investments.csv', header=0, index_col=0)
    update_data = pd.read_csv('data/data.csv', header=0, index_col=0)

    for symbol in update_investments.index:
        if symbol in update_data.index:
            continue
        else:
            update_data.loc[symbol] = [0,0,0,'']

    update_data.to_csv('data/data.csv')

    return

def update_price():
    # get the history
    curr_day = datetime.datetime.today()
    prev_day = curr_day - BDay(5)
    ticker_hist = pd.DataFrame()

    symbol_list = pd.read_csv('data/data.csv', index_col='symbol')

    for ticker in symbol_list.index:
        ticker_hist = nsepy.get_history(symbol=ticker, start=prev_day, end=curr_day)
        # check if the normalized high from ticker_hist is greater than the one recorded in investments
        # update if the normalized close is higher than the recorded high
        symbol_list.loc[ticker, 'close'] = ticker_hist['Close'].min()
        symbol_list.loc[ticker, 'updated'] = datetime.date.today()
        if ticker_hist['Close'].min() > symbol_list.loc[ticker,'high']:
            symbol_list.loc[ticker, 'high'] = ticker_hist['Close'].min()

    symbol_list.to_csv('data/data.csv')


def notify(investments):
    # Check diff between updated last closed and updated peak
