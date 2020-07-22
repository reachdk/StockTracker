import glob
import smtplib
from email.message import EmailMessage
import sys
import pandas as pd
import nsepy
import datetime
from pandas.tseries.offsets import BDay


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
    investments[['ticker', 'exchange']] = investments['Symbol'].str.split('.', n=1, expand=True)
    investments.set_index('ticker', inplace=True)
    investments.drop(investments.columns[:-1], axis=1, inplace=True)
    investments.sort_index(inplace=True)
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
            update_data.loc[symbol] = [1, 1, 15, '']

    update_data.sort_index(inplace=True)
    update_data.to_csv('data/data.csv')

    return


def calculate_variance():
    notify_data = pd.read_csv('data/data.csv', header=0, index_col=0)
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
            msg = msg + elements[0] + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks10:
        if not subject:
            subject = "Stock Alert: 10% Breached on " + str(datetime.date.today())

        msg = msg + '10% threshold breached for: \n'
        for elements in stocks10:
            msg = msg + elements[0] + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks5:
        if not subject:
            subject = "Stock Alert: 5% Breached on " + str(datetime.date.today())

        msg = msg + '5% threshold breached for: \n'
        for elements in stocks5:
            msg = msg + elements[0] + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if subject:
        notify(subject, msg)
    #else:                          #for debugging
    #    print('Nothing to report')

    return


def notify(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = 'deepak@stockalert'
    msg['To'] = 'netmaildeepak@gmail.com'

    # Send the message via our own SMTP server.
    s = smtplib.SMTP('smtp-relay.sendinblue.com', 587)
    s.login('springfields.e704@gmail.com', 'hPJtz3wQ6fp5LaG0')
    s.send_message(msg)
    s.quit()


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
        if ticker_hist['Close'].min() > symbol_list.loc[ticker, 'high']:
            symbol_list.loc[ticker, 'high'] = ticker_hist['Close'].min()

    symbol_list.to_csv('data/data.csv')

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
