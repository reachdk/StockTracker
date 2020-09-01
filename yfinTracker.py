import glob
import sys
import yfinance as yf
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import BDay
import emailIntegration


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)


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
    investments.drop(investments.columns[1:], axis=1, inplace=True)
    # Set symbol as the index, all comparison operations will be easier on unique indexes.
    investments.set_index('Symbol', inplace=True)
    investments.sort_index(inplace=True)

    # write back to the investments file that will be input for daily updates
    investments.to_csv('data/yfin_investments.csv')

    return


def update_meta():
    # Update data file in case the list of investments has changed. To reflect new purchases or sales
    update_investments = pd.read_csv('data/yfin_investments.csv', header=0, index_col=0)
    update_data = pd.read_csv('data/yfin_data.csv', header=0, index_col=0)
    delete_symbols = []

    # Update the symbols that are available in investment input dumps from yahoo fin
    for symbol in update_investments.index:
        if symbol in update_data.index:
            continue
        else:
            update_data.loc[symbol] = [1, '', 1, 15, '']

    # delete the records that need to be removed from the portfolio since they no longer appear in the investments
    for symbol in update_data.index:
        if symbol in update_investments.index:
            continue
        else:
            delete_symbols.append(symbol)
    update_data.drop(delete_symbols, inplace=True)

    # sort and write the data back to be consumed for daily updates
    update_data.sort_index(inplace=True)
    update_data.to_csv('data/yfin_data.csv')

    return delete_symbols


def update_price():
    # Update price based on last 5 days of data from yahoo finance
    curr_day = datetime.today()
    prev_day = curr_day - BDay(5)

    symbol_list = pd.read_csv('data/yfin_data.csv', index_col='symbol')
    ticker_list = symbol_list.index.tolist()
    ticker_list = [sub + ' ' for sub in ticker_list]
    ticker = ' '.join(ticker_list)

    # fetch history from yahoo finance for the list of tickers
    ticker_hist = yf.download(ticker, start=prev_day, end=curr_day)
    ticker_hist = ticker_hist['Close']

    for column in ticker_hist:
        # Update the lowest close price in the last 5 trading days
        symbol_list.loc[column, 'close'] = ticker_hist[column].min()
        symbol_list.loc[column, 'updated'] = datetime.now().date()

        # update historic high price if the lowest close of the last 5 days is
        # higher than currently recorded historic high
        if ticker_hist[column].min() > symbol_list.loc[column, 'high']:
            symbol_list.loc[column, 'high'] = ticker_hist[column].min()
            symbol_list.loc[column, 'high_date'] = datetime.now().date()

    symbol_list.to_csv('data/yfin_data.csv')
    return


def calculate_variance():
    # calculate if any of the notification thresholds have breached due to downward price movement
    notify_data = pd.read_csv('data/yfin_data.csv', header=0, index_col=0)
    # define threshold groups and subject and message to be passed in the notification
    stocks5 = []
    stocks10 = []
    stocksbreach = []
    stagnant = []
    subject = ''
    msg = ''

    # Check if any of the thresholds have been breached.
    for index, row in notify_data.iterrows():
        diff = ((row['high'] - row['close']) / row['high']) * 100
        stagnating = days_between(str(row['updated']), str(row['high_date']))

        if diff > row['tolerance']:
            stocksbreach.append([row.name, diff])

        if stagnating > 45:
            stagnant.append([row.name, stagnating])

        if diff < 5:
            continue
        elif 5 < diff < 10:
            stocks5.append([row.name, diff])
        elif diff > 10:
            stocks10.append([row.name, diff])

    # Construct the subject and message if there is a breach
    if stocksbreach:
        subject = "Stock Alert: Tolerance Breach on " + str(datetime.today())
        msg = 'Consider selling: \n' + ''
        for elements in stocksbreach:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks10:
        if not subject:
            subject = "Stock Alert: 10% Breached on " + str(datetime.today())
        msg = msg + '10% threshold breached for: \n'
        for elements in stocks10:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stocks5:
        if not subject:
            subject = "Stock Alert: 5% Breached on " + str(datetime.today())

        msg = msg + '5% threshold breached for: \n'
        for elements in stocks5:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + '\n'
        msg = msg + '\n'

    if stagnant:
        if not subject:
            subject = "Stocks stagnating"

        msg = msg + 'Following stocks have been stagnating, time to re-look at the portfolio? \n'
        for elements in stagnant:
            msg = msg + str(elements[0]) + ':       ' + str(elements[1]) + ' days since peak' + '\n'
        msg = msg + '\n'

    # call notify function
    if subject:
        notify(subject, msg)

    return


def notify(subject, msg):
    # Construct the notification payload
    sender_email = 'springfields.e704@gmail.com'
    sender_name = 'Deepak Kumar'
    to_email = 'netmaildeepak@gmail.com'
    # to_name = 'Deepak Kumar'
    # replyTo_name = 'Deepak Kumar'
    # replyTo_email = 'springfields.e704@gmail.com'
    mail_subject = subject
    html_body = ''
    mail_body = msg

    # call elastic mail email api to send the email notification
    mail_response = emailIntegration.Send(mail_subject, sender_email, sender_name, to_email, html_body, mail_body, True)
    print(mail_response)

    return


def main():
    if len(sys.argv) == 2:
        if sys.argv[1] == '--u':
            get_investments()
            update_meta()
    update_price()
    calculate_variance()


if __name__ == '__main__':
    main()
