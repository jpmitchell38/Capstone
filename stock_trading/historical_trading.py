from flask import request, send_file, render_template, session
import matplotlib.pyplot as plt
import io
import datetime
import requests
import os
import base64
from dotenv import load_dotenv 
from pymongo.mongo_client import MongoClient #pip install pymongo
from pymongo.server_api import ServerApi

load_dotenv()
uri = os.getenv("MONGO_URI")
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
API_KEY = os.getenv("POLYGON_KEY")
APIA_KEY = os.getenv("ALPACA_KEY")
APIA_SECRET = os.getenv("ALPACA_SECRET")

def stock_viewer_historical():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return render_template("portfolio_historical.html", error="Please provide a valid stock ticker.")

    #Displaying graph on search
    try:
        price = get_stock_price_historical(ticker)
        return render_template("portfolio_historical.html", ticker=ticker, stock_price=price)
    except Exception as e:
        return render_template("portfolio_historical.html", error=f"Error fetching stock data: {str(e)}")


def stock_chart_historical():
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return "Please provide a stock ticker."

    try:       
        # Connect to DB
        email = session['email']
        db = client["Capstone-DB"]
        users_collection = db["my_collection"]
        user = users_collection.find_one({"email": email})
        if not user:
            return {"error": "User not found"}

        # Extract and clean date
        iso_date = user.get("hist_date", "")
        clean_date = iso_date.split("T")[0] if "T" in iso_date else iso_date

        # Compute date range
        end_date = clean_date
        # ChatGPT - gets last 30 days
        start_date = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        start_iso = f"{start_date}T00:00:00Z"
        end_iso = f"{end_date}T23:59:59Z"

        # Alpaca API setup
        headers = {
            'APCA-API-KEY-ID': APIA_KEY,
            'APCA-API-SECRET-KEY': APIA_SECRET
        }
        endpoint = "https://data.alpaca.markets/v2/stocks/bars"
        params = {
            'symbols': ticker,
            'start': start_iso,
            'end': end_iso,
            'timeframe': '1Day',
            'adjustment': 'raw'
        }

        #making api call
        response = requests.get(endpoint, headers=headers, params=params)
        data = response.json()

        # ChatGPT - Gathering data to graph
        if 'bars' not in data or ticker not in data['bars']:
            return f"Error: No data available for '{ticker}'."
        bars = data['bars'][ticker]
        prices = [bar['c'] for bar in bars]
        days = list(range(1, len(prices) + 1))

        #making graph
        plt.style.use("seaborn-darkgrid")
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(days, prices, marker='o', linestyle='-', color='#4A90E2', linewidth=2, label=ticker)
        ax.set_xticks([])
        plt.xlabel("Past 30 Days")
        plt.ylabel("Closing Price (USD)")
        plt.title(f"{ticker} Stock Price Last 30 days")
        plt.grid()
        img = io.BytesIO()
        plt.savefig(img, format="png", bbox_inches="tight")
        img.seek(0)
        plt.close()
        
        # Encode to base64
        encoded_img = base64.b64encode(img.read()).decode("utf-8")
        return encoded_img

    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

def get_stock_price_historical(ticker):
    # Connect to DB
    email = session['email']
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return {"error": "User not found"}

    date = user.get("hist_date", "")

    # Just update the time part to end of the day
    start_date = date
    end_date = date.replace("00:00:00Z", "23:59:59Z")

    # Alpaca API setup
    headers = {
        'APCA-API-KEY-ID': APIA_KEY,
        'APCA-API-SECRET-KEY': APIA_SECRET
    }

    params = {
        'symbols': ticker,
        'start': start_date,
        'end': end_date,
        'timeframe': '1Day',
        'adjustment': 'raw'
    }

    endpoint = "https://data.alpaca.markets/v2/stocks/bars"
    response = requests.get(endpoint, headers=headers, params=params)

    # ChatGPT - Returning price for the correct date
    if response.status_code == 200:
        data = response.json()
        if data and 'bars' in data and ticker in data['bars'] and data['bars'][ticker]:
            close_price = data['bars'][ticker][0]['c']
            return close_price
        else:
            return None
    else:
        return None