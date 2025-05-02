from stock_trading.live_trading import get_stock_price
from stock_trading.historical_trading import get_stock_price_historical
from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient #pip install pymongo
from pymongo.server_api import ServerApi
import os
from flask import session, render_template
from dotenv import load_dotenv 
import requests
load_dotenv()
uri = os.getenv("MONGO_URI")
t_uri = os.getenv("TIINGO_API")
APIA_KEY = os.getenv("ALPACA_KEY")
APIA_SECRET = os.getenv("ALPACA_SECRET")
client = MongoClient(uri, server_api=ServerApi('1'))


def buy_stock(ticker, quantity):
    #calculating price
    ticker = ticker.upper()
    price = get_stock_price(ticker)  
    total_cost = price * quantity

    #Connecting to db
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}

    #Checking if user has enough cash to complete transaction
    if user["cash"] < total_cost:
        return {"error": "Insufficient funds"}

    #If valid buy adding purchase details to db
    users_collection.update_one(
        {"email": email},
        {
            "$push": {
                "purchases": {
                    "ticker": ticker,
                    "quantity": quantity,
                    "price_bought": price,
                    "live_price": price,
                    "date": datetime.utcnow()
                }
            },
            "$inc": {"cash": -total_cost,
            "p_total": total_cost}
        }
    )
    return {"success": f"Bought {quantity} shares of {ticker} at ${price:.2f} each."}


def reset():
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}

    #Setting user cash back to 10k empty purchases
    users_collection.update_one(
        {"email": email},
        {"$set": {"cash": 10000, "p_total": 0, "purchases": []}}
    )
    return render_template("mode_select.html")



def update_live_stock_price():
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]

    BASE_URL = "https://api.tiingo.com/iex/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {t_uri}"
    }
    users = users_collection.find({}, {"purchases": 1})

    # Collect unique tickers from all purchases
    tickers = set()
    for user in users:
        for purchase in user.get("purchases", []):
            tickers.add(purchase["ticker"])

    tickers = list(tickers)
    batch_size = 100

    # ChatGPT - Looping through tickers and calling tiingo api to get its live price
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        tickers_str = ",".join(batch)
        url = f"{BASE_URL}?tickers={tickers_str}&token={t_uri}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return
        
        try:
            data = response.json()
            price_map = {stock["ticker"]: stock["tngoLast"] for stock in data if "tngoLast" in stock}

            # ChatGPT - Update live_price in MongoDB
            for user in users_collection.find({}, {"purchases": 1}):
                updated_purchases = []
                for purchase in user.get("purchases", []):
                    ticker = purchase["ticker"]
                    if ticker in price_map:
                        purchase["live_price"] = price_map[ticker]
                    updated_purchases.append(purchase)
                
                # Update user's purchases in the database
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"purchases": updated_purchases}}
                )
        except requests.exceptions.JSONDecodeError:
            print("Invalid JSON response.")


def sell_stock(ticker, quantity, date):
    ticker = ticker.upper()
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}
    purchases = user.get("purchases", [])

    #Using the date to match transaction user clicked sell on
    matched = None
    for purchase in purchases:
        if purchase["ticker"] == ticker and purchase["date"] == date:
            matched = purchase
            break

    if not matched:
        return {"error": "Purchase not found"}
    if matched["quantity"] < quantity:
        return {"error": "Not enough shares in this purchase"}

    current_price = get_stock_price(ticker)
    sell_value = current_price * quantity
    invested = quantity * matched["price_bought"]

    # Update quantity or remove the purchase if all shares are sold
    if matched["quantity"] == quantity:
        purchases.remove(matched)
    else:
        matched["quantity"] -= quantity

    #Calculating new total invested
    new_p_total = user["p_total"] - invested
    if new_p_total < 0:
        new_p_total = 0

    #Updating db
    users_collection.update_one(
        {"email": email},
        {
            "$set": {
                "purchases": purchases,
                "p_total": new_p_total
            },
            "$inc": {"cash": sell_value}
        }
    )
    return {"success": f"Sold {quantity} shares of {ticker} at ${current_price:.2f} each."}


def next_day():
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}
    
    # Increment the 'day' field by 1
    users_collection.update_one(
        {"email": email},
        {"$inc": {"day": 1}}
    )
    
    hist_date_str = user.get("hist_date")
    hist_date = datetime.strptime(hist_date_str, "%Y-%m-%dT%H:%M:%SZ")

    # Advance the date by one calendar day, skipping weekends
    next_date = hist_date + timedelta(days=1)
    while next_date.weekday() >= 5 or not market_is_open(next_date):  
        next_date += timedelta(days=1)

    # ChatGPT - formatting
    next_date_str = next_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    #Updating date in db to track where user is
    users_collection.update_one(
        {"email": email},
        {"$set": {"hist_date": next_date_str}}
    )
    
    #Update purchases_h with new historical prices
    purchases_h = user.get("purchases_h", [])
    tickers = list({purchase["ticker"] for purchase in purchases_h})
    if not tickers:
        return render_template("mode_select.html")

    #Format date for Alpaca
    start_date = next_date_str
    end_date = next_date_str.replace("00:00:00Z", "23:59:59Z")

    headers = {
        'APCA-API-KEY-ID': APIA_KEY,
        'APCA-API-SECRET-KEY': APIA_SECRET
    }
    params = {
        'symbols': ",".join(tickers),
        'start': start_date,
        'end': end_date,
        'timeframe': '1Day',
        'adjustment': 'raw'
    }

    # ChatGPT - calls the api with the appropriate headers and params
    response = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=headers, params=params)
    if response.status_code != 200:
        return render_template("mode_select.html")

    # ChatGPT - maps symbols to the closing price
    try:
        data = response.json()
        price_map = {
            symbol: bars[0]['c'] for symbol, bars in data.get("bars", {}).items() if bars
        }

        #Update current_price in purchases_h
        updated_purchases = []
        for purchase in purchases_h:
            ticker = purchase["ticker"]
            if ticker in price_map:
                purchase["current_price"] = price_map[ticker]
            updated_purchases.append(purchase)

        users_collection.update_one(
            {"email": email},
            {"$set": {"purchases_h": updated_purchases}}
        )

    except requests.exceptions.JSONDecodeError:
        pass
    
    #Update users info after the day
    user = users_collection.find_one({"email": email})

    #Calculating stats to pass to portfolio historical so stats update on next day
    purchases = user.get("purchases_h", [])
    cash = round(user.get("cash_h", 0), 2)
    total_invested = round(user.get("p_total_h", 0), 2)
    current_portfolio_value = 0
    for stock in purchases:
        current_portfolio_value += stock["current_price"] * stock["quantity"]
    percent_change = 0
    if total_invested > 0:
        percent_change = round(((current_portfolio_value - total_invested) / total_invested) * 100, 2)
    total_value = round(current_portfolio_value + cash, 2)
    cash = "{:.2f}".format(cash)
    total_invested = "{:.2f}".format(total_invested)
    total_value = "{:.2f}".format(total_value)
    day = user.get("day", 0)

    return render_template('portfolio_historical.html', purchases=purchases, cash=cash, total_invested=total_invested, total_value=total_value, percent_change=percent_change, day=day)

# ChatGPT - calling api to see if market was open on this day (for holidays)
def market_is_open(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    response = requests.get(
        "https://paper-api.alpaca.markets/v2/calendar",
        params={"start": date_str, "end": date_str},
        headers={
            "APCA-API-KEY-ID": APIA_KEY,
            "APCA-API-SECRET-KEY": APIA_SECRET
        }
    )
    # True if market was open
    return len(response.json()) > 0

def buy_stock_h(ticker, quantity):
    #Calculating price
    ticker = ticker.upper()
    price = get_stock_price_historical(ticker)
    total_cost = price * quantity
    
    #Connecting to DB
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}
    
    #Checking for sufficient funds
    if user["cash_h"] < total_cost:
        return {"error": "Insufficient funds"}
    
    #If valid, update DB under purchases_historical
    users_collection.update_one(
        {"email": email},
        {
            "$push": {
                "purchases_h": {
                    "ticker": ticker,
                    "quantity": quantity,
                    "price_bought": price,
                    "current_price": price,
                    "date": datetime.utcnow()
                }
            },
            "$inc": {
                "cash_h": -total_cost,
                "p_total_h": total_cost
            }
        }
    )

    return {"success": f"(Historical) Bought {quantity} shares of {ticker} at ${price:.2f} each."}

def sell_stock_h(ticker, quantity, date):
    ticker = ticker.upper()
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}
    purchases = user.get("purchases_h", [])

    #Using the date to match transaction user clicked sell on
    matched = None
    current_price = 0
    for purchase in purchases:
        if purchase["ticker"] == ticker and purchase["date"] == date:
            matched = purchase
            current_price = purchase["current_price"]
            break

    if not matched:
        return {"error": "Purchase not found"}
    if matched["quantity"] < quantity:
        return {"error": "Not enough shares in this purchase"}

    sell_value = current_price * quantity
    invested = quantity * matched["price_bought"]

    # Update quantity or remove the purchase if all shares are sold
    if matched["quantity"] == quantity:
        purchases.remove(matched)
    else:
        matched["quantity"] -= quantity

    #Calculating new total invested
    new_p_total = user["p_total_h"] - invested
    if new_p_total < 0:
        new_p_total = 0

    #Updating db
    users_collection.update_one(
        {"email": email},
        {
            "$set": {
                "purchases_h": purchases,
                "p_total_h": new_p_total
            },
            "$inc": {"cash_h": sell_value}
        }
    )
    return {"success": f"Sold {quantity} shares of {ticker} at ${current_price:.2f} each."}