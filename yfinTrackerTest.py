import glob
import smtplib, ssl
from email.message import EmailMessage
from csv import reader
import sys
import yfinance as yf
import pandas as pd
import datetime
from pandas.tseries.offsets import BDay
from mailin import Mailin
import requests
import json
#Sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


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
    investments.to_csv('data/yfin_investments.csv')
    return


def update_meta():
    update_investments = pd.read_csv('test/yfin_investments.csv', header=0, index_col=0)
    update_data = pd.read_csv('test/yfin_data.csv', header=0, index_col=0)
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
    update_data.to_csv('test/yfin_data.csv')

    return delete_symbols


def update_price():
    curr_day = datetime.datetime.today()
    prev_day = curr_day - BDay(5)

    symbol_list = pd.read_csv('data/yfin_data.csv', index_col='symbol')
    ticker_list = symbol_list.index.tolist()
    ticker_list = [sub + ' ' for sub in ticker_list]
    ticker = ' '.join(ticker_list)
    # todebug print(symbol_list)
    ticker_hist = yf.download(ticker, start=prev_day, end=curr_day)
    ticker_hist = ticker_hist['Close']
    # todebug print(ticker_hist)

    for column in ticker_hist:
        symbol_list.loc[column, 'close'] = ticker_hist[column].min()
        symbol_list.loc[column, 'updated'] = datetime.date.today()
        if ticker_hist[column].min() > symbol_list.loc[column, 'high']:
            symbol_list.loc[column, 'high'] = ticker_hist[column].min()

    symbol_list.to_csv('data/yfin_data.csv')


def calculate_variance():
    notify_data = pd.read_csv('data/yfin_data.csv', header=0, index_col=0)
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

        # if subject:
        # print('Sending Email')
        #notify(subject, msg)
    # else:
    # print('Nothing to report')
    return

def notify_sendgrid_api():
    message = Mail(
        from_email='springfield.e704@gmail.com',
        to_emails='netmaildeepak@gmail.com',
        subject='Sending with Twilio SendGrid is Fun',
        html_content='<strong>and easy to do anywhere, even with Python</strong>')

    readpass = pd.read_csv('Ignore for Inclusion/details_sendgrid_html.csv', header=None)
    login_id = str(readpass.iloc[0, 0])
    login_pass = str(readpass.iloc[0, 1])

    try:
        sg = SendGridAPIClient(login_pass)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)

def notify():
    msg = EmailMessage()
    msg.set_content('Consider selling now')  # msg.set_content(body)
    msg['Subject'] = 'Stock Alert'  # msg['Subject'] = subject
    msg['From'] = 'springfields.e704@gmail.com'
    msg['To'] = 'netmaildeepak@gmail.com'

    from_addr = 'springfields.e704@gmail.com'
    to_addr = 'netmaildeepak@gmail.com'
    #message = 'From:springfields.e704@gmail.com\n Test message here'
    #message = 'Subject: {Stock Alert}\n\n{}'.format(SUBJECT, TEXT)

    message = """From: Ghar Springfields <springfields.e704@gmail.com>
    To: Deepak Kumar <netmaildeepak@gmail.com>
    MIME-Version: 1.0
    Content-type: text/html
    Subject: Stock Tracker alert testing

    Consider selling this.
    
    """

    readpass = pd.read_csv('Ignore for Inclusion/details_elastic.csv', header=None)

    login_id = str(readpass.iloc[0, 0])
    login_pass = str(readpass.iloc[0, 1])

    server = smtplib.SMTP('smtp.elasticemail.com', 2525)
    # incorporate this
    server.login(login_id, login_pass)
    server.sendmail(from_addr, to_addr, message)
    server.sendmail(msg)
    server.quit()





    # Send the message via our own SMTP server.

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=ssl_context) as server:
        server.login(login_id, login_pass)
        server.sendmail(msg)


def notify_oldest(subject, body):
    sender_email = 'springfields.e704@gmail.com'
    sender_name = 'Deepak Kumar'
    to_email = 'kdeepu@gmail.com'
    to_name = 'Deepak Kumar'
    replyTo_name = 'Deepak Kumar'
    replyTo_email = 'springfields.e704@gmail.com'
    mail_subject = 'Stock Alert'
    mail_body = 'Consider Selling now'

    construct_payload = {
        "sender": {
            "email": sender_email,
            "name": sender_name},
        "to": {
            "email": 'kdeepu@gmail.com',
            "name": to_name},
        "replyTo": {
            "email": replyTo_email,
            "name": replyTo_name},
        "textContent": mail_body,
        "subject": mail_subject}

    data = {"to": {to_email: to_name},
            "from": ["from@email.com", "from email!"],
            "subject": "My subject",
            "html": "This is the <h1>HTML</h1>",
            }

    payload = json.dumps(construct_payload)

    # Send the message via our own SMTP server.
    s = Mailin("https://api.sendinblue.com/v2.0", "<key>>")
    response = s.send_email(data)
    print(response)


def notify_older():
    sender_email = 'springfields.e704@gmail.com'
    sender_name = 'Deepak Kumar'
    to_email = 'netmaildeepak@gmail.com'
    to_name = 'Deepak Kumar'
    replyTo_name = 'Deepak Kumar'
    replyTo_email = 'springfields.e704@gmail.com'
    mail_subject = 'Stock Alert'
    mail_body = 'Consider Selling now'

    url = "https://api.sendinblue.com/v3/smtp/email"

    construct_payload = {
        "sender": {
            "email": sender_email,
            "name": sender_name},
        "to": {
            "email": to_email},
        # "name": to_name},
        "replyTo": {
            "email": replyTo_email,
            "name": replyTo_name},
        "textContent": mail_body,
        "subject": mail_subject}

    # convert into JSON:
    payload = json.dumps(construct_payload)

    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'api-key': "<here>>",
    }

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.text)


def main():
    args = sys.argv
    if args == '--u':
        get_investments()
        update_meta()
    update_price()
    calculate_variance()


if __name__ == '__main__':
    main()
