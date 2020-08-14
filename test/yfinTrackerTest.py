import glob
import sys
import yfinance as yf
import pandas as pd
import datetime
from pandas.tseries.offsets import BDay
import emailIntegrationTest



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
    # Commenting next line since it is no longer necessary to strip the .NS suffix
    # investments[['ticker', 'exchange']] = investments['Symbol'].str.split('.', n=1, expand=True)
    investments.drop(investments.columns[1:], axis=1, inplace=True)
    investments.set_index('Symbol', inplace=True)
    investments.sort_index(inplace=True)
    investments.to_csv('yfin_investments.csv')

    return


def update_meta():
    update_investments = pd.read_csv('yfin_investments.csv', header=0, index_col=0)
    update_data = pd.read_csv('yfin_data.csv', header=0, index_col=0)
    delete_symbols = []

    # Update the symbols that are available in investment input dumps from yahoo fin
    for symbol in update_investments.index:
        if symbol in update_data.index:
            continue
        else:
            update_data.loc[symbol] = [1, 1, 15, '']

    # delete the records that need to be removed from the portfolio since they no longer appear in the investments
    for symbol in update_data.index:
        if symbol in update_investments.index:
            continue
        else:
            delete_symbols.append(symbol)

    update_data.drop(delete_symbols, inplace=True)
    update_data.sort_index(inplace=True)
    update_data.to_csv('yfin_data.csv')

    return delete_symbols


def update_price():
    curr_day = datetime.datetime.today()
    prev_day = curr_day - BDay(5)

    symbol_list = pd.read_csv('yfin_data.csv', index_col='symbol')
    ticker_list = symbol_list.index.tolist()
    ticker_list = [sub + ' ' for sub in ticker_list]
    ticker = ' '.join(ticker_list)
    ticker_hist = yf.download(ticker, start=prev_day, end=curr_day)
    ticker_hist = ticker_hist['Close']

    for column in ticker_hist:
        symbol_list.loc[column, 'close'] = ticker_hist[column].min()
        symbol_list.loc[column, 'updated'] = datetime.date.today()
        if ticker_hist[column].min() > symbol_list.loc[column, 'high']:
            symbol_list.loc[column, 'high'] = ticker_hist[column].min()

    symbol_list.to_csv('yfin_data.csv')


def calculate_variance():
    notify_data = pd.read_csv('yfin_data.csv', header=0, index_col=0)
    stocks5 = []
    stocks10 = []
    stocksbreach = []
    subject = ''
    msg = ''

    for index, row in notify_data.iterrows():
        diff = ((row['high'] - row['close']) / row['high']) * 100
        if diff < 5:
            continue
        elif 5 < diff < 10:
            stocks5.append([row.name, diff])
        elif diff > 10:
            stocks10.append([row.name, diff])

        if diff > row['tolerance']:
            stocksbreach.append([row.name, diff])

    if stocksbreach:
        subject = "Stock Alert: Tolerance Breach on " + str(datetime.date.today())
        msg = 'Consider selling: \n' + ''
        for elements in stocksbreach:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks10:
        if not subject:
            subject = "Stock Alert: 10% Breached on " + str(datetime.date.today())

        msg = msg + '10% threshold breached for: \n'
        for elements in stocks10:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks5:
        if not subject:
            subject = "Stock Alert: 5% Breached on " + str(datetime.date.today())

        msg = msg + '5% threshold breached for: \n'
        for elements in stocks5:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if subject:
        notify(subject, msg)

    return


def notify(subject, msg):
    sender_email = 'springfields.e704@gmail.com'
    sender_name = 'Deepak Kumar'
    to_email = 'netmaildeepak@gmail.com'
    # to_name = 'Deepak Kumar'
    # replyTo_name = 'Deepak Kumar'
    # replyTo_email = 'springfields.e704@gmail.com'
    mail_subject = subject
    html_body = ''
    mail_body = msg

    mail_response = emailIntegrationTest.Send(mail_subject, sender_email, sender_name, to_email, html_body, mail_body, True)
    print(mail_response)

    return


def main():
    args = sys.argv
    if args == '--u':
        get_investments()
        update_meta()
    update_price()
    calculate_variance()


if __name__ == '__main__':
    main()
