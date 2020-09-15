from tda import auth, client
import os.path
from os import path
import json
import config
import datetime
import pandas as pd
import tda
import time

try:
        c = auth.client_from_token_file(config.token_path, config.api_key)
except FileNotFoundError:
        from selenium import webdriver
        with webdriver.Chrome(executable_path='/Users/Jonathan Hou/Desktop/TDAmeritrade/chromedriver') as driver:
            c = auth.client_from_login_flow(
                driver, config.api_key, config.redirect_uri, config.token_path)

x=datetime.datetime.now()

if not path.exists("DMResults.txt"):
    f = open("DMResults.txt", "w")
else:
    f = open("DMResults.txt", "a")
    f.write("\n***********************************************************************************\n")
    f.write("\n===================="+str(x.strftime("%a %B-%d-%Y %I:%M %p"))+"====================\n")
    f.write("\n***********************************************************************************\n")
    print()
    print("\n***********************************************************************************\n")
    print("\n===================="+str(x.strftime("%a %B-%d-%Y %I:%M %p"))+"====================\n")
    print("\n***********************************************************************************\n")


def main():

    summary()
    
    #Set hedge variables
    hedge = "AAPL"
    
    #Set stocks we want to buy
    etfs = [
            "SPXL", # Daily S&P 500 Bull 3X Shares
            "AMZN", # Amazon
            "TSLA", # Tesla
            "AAPL", # Apple
            "AMD"   # AMD
    ]
    etfs.sort()
    state = 1
    highestPortfolio = 0
    target_leverage = 1
    
    #Set array for scores
    weightList = {}

    for i in etfs:
        #Get price history for each stock above
        his = c.get_price_history(i,
            period_type=client.Client.PriceHistory.PeriodType.YEAR,
            period=client.Client.PriceHistory.Period.ONE_YEAR,
            frequency_type=client.Client.PriceHistory.FrequencyType.DAILY,
            frequency=client.Client.PriceHistory.Frequency.DAILY)
        
        #Calculate scores and update weightList
        data = pd.read_json(json.dumps(his.json()['candles'], indent=4))
        one = (pd.DataFrame(data).tail(1).head(1)['close']).values[0]
        twentyone = (pd.DataFrame(data).tail(21).head(1)['close']).values[0]
        sixtythree = (pd.DataFrame(data).tail(63).head(1)['close']).values[0]
        onetwentysix = (pd.DataFrame(data).tail(126).head(1)['close']).values[0]
        weightList.update({i: one/twentyone*.43 + one/sixtythree * .33 + one/onetwentysix * .24 })
    #Print all scores for all stocks
    printWeightList(weightList)

    assert his.ok, his.raise_for_status()

    #Get maxValue of scores and print maxValue with score
    maxValue = max(weightList, key=weightList.get)
    
    #If maxValue of scores are less than 0 then set to hedge
    if max(weightList.values())<=0:
        maxValue = hedge

    print("Max Value: "+maxValue + " score @ " + str(max(weightList.values())))
    f.write("\nMax Value: "+maxValue + " score @ " + str(max(weightList.values())))

    printTrade()
    buyStock(maxValue, target_leverage)

def buyStock(maxValue, target_leverage):
    curr_positions = c.get_accounts(fields=[c.Account.Fields.POSITIONS])
    position = curr_positions.json()[0]['securitiesAccount']

    instrument = []
    temp = curr_positions.json()[0]['securitiesAccount']
    if "positions" in temp:
        instruments = json.loads(json.dumps(curr_positions.json()[0]['securitiesAccount']['positions']))
        for position in instruments:
            instrument.append(position["instrument"]["symbol"])    
    
    if len(instrument)==0 or (len(instrument)==1 and "MMDA1" in instrument): #If holding, positions substring will appear in json, otherwise, not holding positions
        temp_curr_price = c.get_quote(maxValue).json()[maxValue]["regularMarketLastPrice"]
        curr_equity = curr_positions.json()[0]['securitiesAccount']['currentBalances']['availableFunds']
        number_of_shares = int(curr_equity/temp_curr_price*target_leverage)
        
        print("Buying " + str(number_of_shares)+" shares of "+maxValue + " at $"+str(temp_curr_price) + " each")
        f.write("\nBuying " + str(number_of_shares)+" shares of "+maxValue + " at $"+str(temp_curr_price) + " each\n")
        #Build the order spec and place the order. MARKET, NORMAL, DAY, BUY
        placeBuyOrder(maxValue, number_of_shares)
        
    elif ((len(instrument)==2) and ("MMDA1" in instrument) and (maxValue in instrument)) or ((len(instrument)==1) and maxValue in instrument): #If own existing stock to buy, buy more of same one
        temp_curr_price = c.get_quote(maxValue).json()[maxValue]["regularMarketLastPrice"]
        curr_equity = curr_positions.json()[0]['securitiesAccount']['currentBalances']['availableFunds']
        number_of_shares = int(curr_equity/temp_curr_price*target_leverage)
        
        if "MMDA1" in instrument:
            instrument.remove("MMDA1")
            old_stocks = instrument[0]
        elif len(instrument)==1 and maxValue in instrument:
            old_stocks = instrument[0]
        
        for position in instruments:
            if(position["instrument"]["symbol"]==old_stocks):
                old_holdings = position["longQuantity"]

        if number_of_shares > 0:
            print("Owned " + str(old_holdings)+" shares of "+old_stocks)
            f.write("\nOwned " + str(old_holdings)+" shares of "+old_stocks)

            print("Buying " + str(number_of_shares)+" more shares of "+maxValue + " at current $"+str(temp_curr_price) + " each.")
            f.write("\nBuying " + str(number_of_shares)+" more shares of "+maxValue + " at current $"+str(temp_curr_price) + " each.")
            #Build the order spec and place the order. MARKET, NORMAL, DAY, BUY
            placeBuyOrder(maxValue, number_of_shares)
        else:
            print("Holding same stock and cannot increase holdings.")
            f.write("\nHolding same stock and cannot increase holdings.")

    else: #Sell old stocks, buy new stock
        if "MMDA1" in instrument:
            instrument.remove("MMDA1")
            old_stocks = instrument[0]
        elif len(instrument)==1 and "MMDA1" not in instrument:
            old_stocks = instrument[0]

        old_quantity=0
        for position in instruments:
            if(position["instrument"]["symbol"]==old_stocks):
                old_quantity = position["longQuantity"]

        #print(json.dumps(curr_positions.json()[0]['securitiesAccount']['positions'][-1], indent=4))
        print("Selling " + str(old_quantity)+" shares of "+old_stocks)
        f.write("\nSelling " + str(old_quantity)+" shares of "+old_stocks)
        #Build the order spec and place the order. MARKET, NORMAL, DAY, BUY
        placeSellOrder(old_stocks, old_quantity)

        temp_curr_price = c.get_quote(maxValue).json()[maxValue]["regularMarketLastPrice"]
        curr_equity2 = curr_positions.json()[0]['securitiesAccount']['currentBalances']['availableFunds']
        number_of_shares = int(curr_equity2/temp_curr_price*target_leverage)

        while(number_of_shares<=0):
            curr_positions = c.get_accounts(fields=[c.Account.Fields.POSITIONS])
            curr_equity2 = curr_positions.json()[0]['securitiesAccount']['currentBalances']['availableFunds']
            number_of_shares = int(curr_equity2/temp_curr_price*target_leverage)
            time.sleep(2)

        print("Buying " + str(number_of_shares)+" shares of "+maxValue + " at $"+str(temp_curr_price) + " each")
        f.write("\nBuying " + str(number_of_shares)+" shares of "+maxValue + " at $"+str(temp_curr_price) + " each")
        #Build the order spec and place the order. MARKET, NORMAL, DAY, BUY
        placeBuyOrder(maxValue, number_of_shares)

    endsummary()

def placeBuyOrder(maxValue, number_of_shares):
    acct = c.get_accounts()
    acct_id = str(acct.json()[0]['securitiesAccount']['accountId'])
    builder = tda.orders.EquityOrderBuilder(maxValue, number_of_shares)
    builder.set_instruction(builder.Instruction.BUY)
    builder.set_order_type(builder.OrderType.MARKET)
    builder.set_duration(tda.orders.Duration.DAY)
    builder.set_session(tda.orders.Session.NORMAL)
    order = builder.build()
    
    r = c.place_order(acct_id, order)
    time.sleep(2)
    assert r.ok, r.raise_for_status()
    
    response = client.Client.get_orders_by_query(c, max_results=10)
    new_str = response.content.decode('utf-8')
    status = json.dumps(json.loads(new_str)[0]["status"]).replace("\"","")
    #print(json.dumps(json.loads(new_str)[0]["status"], indent=4))
    exit_condition = 0
    while status != "FILLED" and exit_condition < 10:
        print("WAITING....."+str(status))
        f.write("\nWAITING....."+str(status))
        time.sleep(2)
        response = client.Client.get_orders_by_query(c, max_results=10)
        new_str = response.content.decode('utf-8')
        status = json.dumps(json.loads(new_str)[0]["status"]).replace("\"","")
        exit_condition = exit_condition+1

    print("DONE....."+str(status))
    f.write("\nDONE....."+str(status)+"\n")

def placeSellOrder(maxValue, number_of_shares):
    acct = c.get_accounts()
    acct_id = str(acct.json()[0]['securitiesAccount']['accountId'])
    builder = tda.orders.EquityOrderBuilder(maxValue, number_of_shares)
    builder.set_instruction(builder.Instruction.SELL)
    builder.set_order_type(builder.OrderType.MARKET)
    builder.set_duration(tda.orders.Duration.DAY)
    builder.set_session(tda.orders.Session.NORMAL)
    order = builder.build()
    
    r = c.place_order(acct_id, order)
    time.sleep(2)
    assert r.ok, r.raise_for_status()
    
    response = client.Client.get_orders_by_query(c, max_results=10)
    new_str = response.content.decode('utf-8')
    status = json.dumps(json.loads(new_str)[0]["status"]).replace("\"","")
    #print(json.dumps(json.loads(new_str)[0]["status"], indent=4))
    exit_condition = 0
    while status != "FILLED" and exit_condition < 10:
        print("WAITING....."+str(status))
        f.write("\nWAITING....."+str(status))
        time.sleep(2)
        response = client.Client.get_orders_by_query(c, max_results=10)
        new_str = response.content.decode('utf-8')
        status = json.dumps(json.loads(new_str)[0]["status"]).replace("\"","")
        exit_condition = exit_condition+1

    print("DONE....."+str(status))
    f.write("\nDONE....."+str(status)+"\n")

def printTrade():
    print("\n\n-------------ACTIVITY REPORT-------------------")
    f.write("\n\n-------------ACTIVITY REPORT-------------------")

def summary():
    acct = c.get_accounts()
    acct_id = str(acct.json()[0]['securitiesAccount']['accountId'])
    #print(json.dumps(acct.json(), indent=4))
    print('\n-------------TRADING SUMMARY-----------------')
    print('Account NUMBER: ' + acct_id)
    print('Current EQUITY: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['equity']))
    print('Current CASH BALANCE: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['availableFunds']) +'\n')
    f.write('\n-------------TRADING SUMMARY-----------------')
    f.write('\nAccount NUMBER: ' + acct_id)
    f.write('\nCurrent EQUITY: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['equity']))
    f.write('\nCurrent CASH BALANCE: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['availableFunds']) +'\n')

def endsummary():
    acct = c.get_accounts()
    acct_id = str(acct.json()[0]['securitiesAccount']['accountId'])
    print('\n\n-------------ENDING SUMMARY-----------------')
    print('Current EQUITY: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['equity']))
    print('Current CASH BALANCE: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['availableFunds']) +'\n')
    f.write('\n\n-------------ENDING SUMMARY-----------------')
    f.write('\nCurrent EQUITY: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['equity']))
    f.write('\nCurrent CASH BALANCE: ' + str(acct.json()[0]['securitiesAccount']['currentBalances']['availableFunds']) +'\n')
    print('\nEnd of trading for current hour...'+str(x.strftime("%a %B-%d-%Y %I:%M %p"))+'\n')
    f.write('\nEnd of trading for current hour...'+str(x.strftime("%a %B-%d-%Y %I:%M %p"))+'\n')
    
def printWeightList(weightList):
    print('-------------DM SUMMARY-------------------')
    print(json.dumps(weightList, indent=4))
    print('---------------------------------------------\n')
    f.write('\n-------------DM SUMMARY-------------------')
    f.write(json.dumps(weightList, indent=4))
    f.write('---------------------------------------------\n')

main()
