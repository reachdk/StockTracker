import yfinance as yf


# get the history
    curr_day = datetime.datetime.today()
    prev_day = curr_day - BDay(5)
    ticker_hist = pd.DataFrame()
    ticker = ''

    symbol_list = pd.read_csv('data/data.csv', index_col='symbol')
    ticker_list = symbol_list.index.tolist()
    ticker_list = [sub + '' in sub for ticker_list]
    ticker = ' '.join(ticker_list)

    data = yf.download(ticker, start=prev_day, end=curr_day)
    data = data['Close']


    for column in data:
        symbol_list.loc[ticker, 'close'] = data[column].min()
        symbol_list.loc[ticker, 'updated'] = datetime.date.today()
        if data[column].min() > symbol_list.loc[ticker, 'high']:
            symbol_list.loc[ticker, 'high'] = data[column].min()



    symbol_list.to_csv('data/data.csv')