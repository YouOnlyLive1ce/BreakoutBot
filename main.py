from binance.client import Client
import keys
import pandas as pd
import math
from decimal import Decimal

def top_volatile_and_volume_coins(amount_to_show=3):
    '''return all coins and their data. Do not call this function frequently.'''
    # filter only usdt
    all_tickers = pd.DataFrame(client.get_ticker())
    work = all_tickers[all_tickers.symbol.str.contains('USDT')]
    work = work[work['quoteVolume'].astype(float) > 100000000]
    work = work[~((work.symbol.str.contains('UP')) | (work.symbol.str.contains('DOWN')))]
    work['priceChangePercent'] = pd.to_numeric(work['priceChangePercent'])
    work['absolutePriceChangePercent'] = work['priceChangePercent'].abs()
    top_coin = work.sort_values(by=['absolutePriceChangePercent'])
    top_coin = top_coin.symbol.values[-amount_to_show:]
    return top_coin


def custom_order_book(symbol, custom_interval_multiplicator=10, limit=100):
    # Important: function sends order book with empty levels, so amount of rows can be more than limit
    # If you dont want to see levels with 0 quantity orders - filter data frame
    # TODO: Dont repeat yourself
    order_book = client.get_order_book(symbol=symbol, limit=limit)  # spot order book
    default_interval = Decimal(order_book['bids'][0][0]) - Decimal(order_book['bids'][1][0])
    custom_interval = Decimal(str(custom_interval_multiplicator)) * Decimal(str(default_interval))
    print(order_book, len(order_book['asks']), len(order_book['bids']))

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

    order_book = pd.concat([asks.iloc[::-1], bids.iloc[::-1]])
    return order_book


def last_data(symbol, interval, lookback):
    frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + 'min ago UTC'))
    frame = frame.iloc[:, :6]
    frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    frame = frame.set_index('Time')
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame


# def strategy(buy_amt, SL=0.985, Target=1.02, open_position=False):
#     try:
#         asset = top_coin()
#         df = last_data(asset, '1m', '120')
#     except:
#         time.sleep(61)
#         asset = top_coin()
#         df = last_data(asset, '1m', '120')
#
#     qty = round(buy_amt / df.Close.iloc[-1], 1)
#
#     if ((df.Close.pct_change() + 1).cumprod()).iloc[-1] > 1:
#         print(asset)
#         print(df.Close.iloc[-1])
#         print(qty)
#         order = client.create_order(symbol=asset, side='BUY', type='MARKET', quantity=qty)
#         print(order)
#         buyprice = float(order['fills'][0]['price'])
#         open_position = True
#
#         while open_position:
#             try:
#                 df = last_data(asset, '1m', '2')
#             except:
#                 print('Restart after 1 min')
#                 time.sleep(61)
#                 df = last_data(asset, '1m', '2')
#
#             print(f'Price ' + str(df.Close[-1]))
#             print(f'Target ' + str(buyprice * Target))
#             print(f'Stop ' + str(buyprice * SL))
#             if df.Close[-1] <= buyprice * SL or df.Close[-1] >= buyprice * Target:
#                 order = client.create_order(symbol=asset, side='SELL', type='MARKET', quantity=qty)
#                 print(order)
#                 break
#     else:
#         print('No find')
#         time.sleep(20)
#     while True:
#         strategy(15)

def coin_levels(symbol,interval,lookback):
    frame=last_data(symbol,interval,lookback)
    levels = []
    for index, row in frame.iterrows():
        levels.append(row['High'])
        levels.append(row['Low'])
        levels.append(row['Close'])
        # levels.append(row['Open'])
    levels = sorted(levels)
    return levels


def combine_coin_levels(levels, step_percent=1.005):
    zones = []
    zone = []
    for level in levels:
        if len(zone) == 0:
            zone.append(level)
            continue
        if (Decimal(zone[-1])/Decimal(zone[0]))<step_percent:
            zone.append(level)
        else:
            if len(zone) > 2:
                zones.append(zone)
            zone = []
    return zones


def percent_change_till_zone(zone, current_price):
    # for every zone, calculate price percent change till next zone over current price
    priceChange = 0
    # if current price is lower than zone
    if (current_price / Decimal(zone[0])) < 1 and (current_price / Decimal(zone[-1])) < 1:
        priceChange = 1 / min(current_price / Decimal(zone[-1]), current_price / Decimal(zone[0]))
    # if current price is higher than zone
    elif (current_price / Decimal(zone[0])) > 1 and (current_price / Decimal(zone[-1])) > 1:
        priceChange = -max(current_price / Decimal(zone[0]), current_price / Decimal(zone[-1])) + 1
    # if current price is into consolidation
    elif (current_price / Decimal(zone[0])) > 1 and (current_price / Decimal(zone[-1])) < 1:
        priceChange = min(current_price / Decimal(zone[-1]) - 1, 1 / current_price / Decimal(zone[0]))
    return priceChange

def clear_coin_zones_data(symbol,zones,rewardrisk,step_percent=1.005):
    # determine max percent of zone
    priceChangePercent = Decimal(client.get_ticker(symbol=symbol)['priceChangePercent']) / rewardrisk
    for zone in zones:
        if (zone[-1]/zone[0])>1+priceChangePercent/1000:
            splitted_zone=combine_coin_levels(zone,step_percent-0.001)
            splitted_zone=filter(lambda zone:len(zone)>3,splitted_zone)
            zones.remove(zone)
            for little_zone in splitted_zone:
                zones.append(little_zone)
    return zones
    # current_price = Decimal(client.get_avg_price(symbol=symbol)['price'])
    # percent_change_till_zone_data=[]
    # for zone in zones:
    #     percent_change_till_zone_data.append([zone[0],zone[-1],percent_change_till_zone(zone,current_price)])
    # return percent_change_till_zone_data

client = Client(keys.api_key, keys.secret_key)
# top_coins = top_volatile_and_volume_coins()
# for coin in top_coins:
#     zones=coin_levels(coin,'15m','2000')
#     zones=combine_coin_levels(zones)
#
symbol = 'STORJUSDT'
rewardrisk = 3
zones=coin_levels(symbol,'15m','2000')
zones=combine_coin_levels(zones)
for zone in zones:
    print(zone)
zones=clear_coin_zones_data(symbol,zones,rewardrisk)
current_price=Decimal(client.get_avg_price(symbol=symbol)['price'])
for zone in zones:
    print(zone[0],zone[-1],percent_change_till_zone(zone,current_price))


# >1.00'dailycahge'% delete zones

# ob=custom_order_book(symbol="BTCUSDT",custom_interval_multiplicator=100,limit=300)
# ob=ob[ob.quantity>6]
# print(ob)

# algorithm:
# 1) choose only top volatile+large volume coins
# 2) find zones and levels
# 3) check how many percent till these levels
# 4) if not much(<5%) turn on algorithm
# 5) if there is large limit orders, act long/short
# 6) if there is no limit orders, wait
