from binance.client import Client
import keys
import pandas as pd
import time
import requests
import math
from decimal import Decimal

client = Client(keys.api_key, keys.secret_key)
def top_coin():
    #filter only usdt
    all_tickers = pd.DataFrame(client.get_ticker())
    usdt = all_tickers[all_tickers.symbol.str.contains('USDT')]
    work = usdt[~((usdt.symbol.str.contains('UP')) | (usdt.symbol.str.contains('DOWN')))]
    top_coin = work[work.priceChangePercent == work.priceChangePercent.max()]
    top_coin = top_coin.symbol.values[0]
    return top_coin

def custom_order_book(symbol, custom_interval_multiplicator=10,limit=100):
    #Important: function sends order book with empty levels, so amount of rows can be more than limit
    #If you dont want to see levels with 0 quantity orders - filter data frame
    #TODO: Dont repeat yourself
    order_book=client.get_order_book(symbol=symbol,limit=limit) # spot order book
    default_interval=Decimal(order_book['bids'][0][0])-Decimal(order_book['bids'][1][0])
    custom_interval=Decimal(str(custom_interval_multiplicator))*Decimal(str(default_interval))
    print(order_book,len(order_book['asks']),len(order_book['bids']))

    # get bids data
    bids = pd.DataFrame(order_book["bids"], columns=['price', 'quantity'], dtype=float)
    bids["side"] = "buy"
    min_bid_level = math.floor(min(bids.price) / float(custom_interval)) * custom_interval
    max_bid_level = (math.ceil(max(bids.price) / float(custom_interval)) + 1) * custom_interval
    custom_orderbook_levels = [float(min_bid_level + custom_interval * x) for x in range
                                (int((max_bid_level - min_bid_level) / custom_interval) - 1)]
    bids["custom"] = pd.cut(bids.price, bins=custom_orderbook_levels, right=False, precision=10)
    bids = bids.groupby("custom").agg(quantity=("quantity", "sum"), side=("side", "first")).reset_index()
    bids["label"] = bids.custom.apply(lambda x: x.left)

    # get asks data
    asks = pd.DataFrame(order_book["asks"], columns=['price', 'quantity'], dtype=float)
    asks["side"] = "sell"
    min_ask_level = math.floor(min(asks.price) / float(custom_interval)) * custom_interval
    max_ask_level = (math.ceil(max(asks.price) / float(custom_interval)) + 1) * custom_interval
    custom_orderbook_levels = [float(min_ask_level + custom_interval * x) for x in range
                                (int((max_ask_level - min_ask_level) / custom_interval) - 1)]
    asks["custom"] = pd.cut(asks.price, bins=custom_orderbook_levels, right=False, precision=10)
    asks = asks.groupby("custom").agg(quantity=("quantity", "sum"), side=("side", "first")).reset_index()
    asks["label"] = asks.custom.apply(lambda x: x.left)

    order_book=pd.concat([asks.iloc[::-1],bids.iloc[::-1]])
    return order_book

def last_data(symbol, interval, lookback):
    frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + 'min ago UTC'))
    frame = frame.iloc[:, :6]
    frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    frame = frame.set_index('Time')
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame


def strategy(buy_amt, SL=0.985, Target=1.02, open_position=False):
    try:
        asset = top_coin()
        df = last_data(asset, '1m', '120')
    except:
        time.sleep(61)
        asset = top_coin()
        df = last_data(asset, '1m', '120')

    qty = round(buy_amt / df.Close.iloc[-1], 1)

    if ((df.Close.pct_change() + 1).cumprod()).iloc[-1] > 1:
        print(asset)
        print(df.Close.iloc[-1])
        print(qty)
        order = client.create_order(symbol=asset, side='BUY', type='MARKET', quantity=qty)
        print(order)
        buyprice = float(order['fills'][0]['price'])
        open_position = True

        while open_position:
            try:
                df = last_data(asset, '1m', '2')
            except:
                print('Restart after 1 min')
                time.sleep(61)
                df = last_data(asset, '1m', '2')

            print(f'Price ' + str(df.Close[-1]))
            print(f'Target ' + str(buyprice * Target))
            print(f'Stop ' + str(buyprice * SL))
            if df.Close[-1] <= buyprice * SL or df.Close[-1] >= buyprice * Target:
                order = client.create_order(symbol=asset, side='SELL', type='MARKET', quantity=qty)
                print(order)
                break
    else:
        print('No find')
        time.sleep(20)
    while True:
        strategy(15)

frame = pd.DataFrame(client.get_historical_klines('BSWUSDT', '5m','1500' + 'min ago UTC'))
frame = frame.iloc[:, :6]
frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
frame=frame.reset_index()
levels=[]
for index, row in frame.iterrows():
    levels.append(row['High'])
    levels.append(row['Low'])
    # levels.append(row['Close'])
    # levels.append(row['Open'])
levels=sorted(levels)
print(levels)
zones=[]
zone=[]
for i in range(0,len(levels)):
    if len(zone)==0:
        zone.append(levels[i])
        continue
    #TODO:automate step percent determining
    if float(zone[-1])*1.005>float(levels[i]):
        zone.append(levels[i])
    else:
        if len(zone)>2:
            zones.append(zone)
        zone=[]
for zone in zones:
        print(zone[0],zone[-1])
#TODO:separate low range zones=levels (determine percent) from actual zones

# print(frame)
# print(frame.loc[lambda frame: frame['Volume'].astype(float)>50000])

# ob=custom_order_book(symbol="BTCUSDT",custom_interval_multiplicator=100,limit=300)
# ob=ob[ob.quantity>6]
# print(ob)

# algorithm:
# 1) choose only top growth/fall coins
# 2) find zones and levels
# 3) check how many percent till this levels
# 4) if not much(<5%) turn on algorithm
# 5) if there is large limit orders, act long/short
# 6) if there no limit orders, wait