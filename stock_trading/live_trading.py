import datetime
from flask import Flask, request, render_template, send_file
import finnhub # pip install finnhub-python
import os
from dotenv import load_dotenv #pip install python-dotenv
import matplotlib
matplotlib.use('Agg') #So tkinter doesnt try opening up the plot in a tkinter window
import matplotlib.pyplot as plt
import io
import requests
import base64 

load_dotenv()
polygon_key = os.getenv("POLYGON_KEY")
finnhub_key = os.getenv("FINNHUB_KEY")

def stock_viewer():
    ticker = request.args.get("ticker", "").upper()
    return render_template("stock_search.html", ticker=ticker)

def stock_chart(ticker):
    ticker = request.args.get("ticker", "").upper()
    if not ticker:
        return "Error receiving ticker"

    try:
        today = datetime.date.today()
        last_month = today - datetime.timedelta(days=30)
        formatted_start_date = last_month.strftime("%Y-%m-%d")
        formatted_end_date = today.strftime("%Y-%m-%d")

        BASE_URL = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{formatted_start_date}/{formatted_end_date}?adjusted=true&apiKey={polygon_key}"
        response = requests.get(BASE_URL)
        data = response.json()
        if "results" not in data:
            return f"Error fetching stock data for {ticker}"

        results = data["results"]
        dates = [datetime.datetime.fromtimestamp(item["t"] / 1000).strftime('%Y-%m-%d') for item in results]
        prices = [item["c"] for item in results]
        if not dates or not prices:
            return f"No past data available for {ticker}"

        plt.style.use("seaborn-darkgrid")
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(dates, prices, marker='o', linestyle='-', color='#4A90E2', linewidth=2, label=ticker)

        #chatgpt used for styling graph
        ax.set_xticks(dates[::max(len(dates)//7, 1)])
        ax.set_xticklabels(dates[::max(len(dates)//7, 1)], rotation=45, fontsize=7)
        ax.set_xlabel("Date", fontsize=9, fontweight='bold')
        ax.set_ylabel("Closing Price (USD)", fontsize=9, fontweight='bold')
        ax.set_title(f"{ticker} Stock Price (Last 30 Days)", fontsize=10, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        # Save image
        img = io.BytesIO()
        plt.savefig(img, format="png", bbox_inches="tight", dpi=120)
        img.seek(0)
        plt.close()
        
        # Encode image to base64
        img_base64 = base64.b64encode(img.getvalue()).decode("utf-8")
        return img_base64

    except Exception as e:
        return f"Error fetching stock data: {str(e)}"


def get_stock_price(ticker):
    ticker = ticker.upper()
    url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={finnhub_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        current_price = data['c']
        return current_price
    else:
        return None