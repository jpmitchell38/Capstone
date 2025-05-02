from datetime import datetime
from flask import Flask, render_template, request, jsonify
from stock_trading.live_trading import stock_viewer, stock_chart, get_stock_price
from stock_trading.historical_trading import stock_viewer_historical, stock_chart_historical, get_stock_price_historical
from user_management.auth import user_sign_up, user_log_in, client
from stock_trading.transactions import buy_stock, reset, update_live_stock_price, sell_stock, next_day, buy_stock_h, sell_stock_h
from flask import session
import threading
import time

# Sets template folder to working directory, setting secret key
app = Flask(__name__)
app.secret_key = "dajsnfipsdbfpiahfosndfias"
app.add_url_rule('/stock_viewer', 'stock_viewer', stock_viewer, methods=["GET"])
app.add_url_rule('/stock_chart', 'stock_chart', stock_chart)
app.add_url_rule('/stock_viewer_historical', 'stock_viewer_historical', stock_viewer_historical, methods=["GET"])
app.add_url_rule('/stock_chart_historical', 'stock_chart_historical', stock_chart_historical)
app.add_url_rule('/user_sign_up', 'user_sign_up', user_sign_up, methods=["POST"])
app.add_url_rule('/user_log_in', 'user_log_in', user_log_in, methods=["POST"])
app.add_url_rule('/reset', 'reset', reset)
app.add_url_rule('/next_day', 'next_day', next_day)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/portfolio_live')
def portfolio_live():
    #Getting email from session
    email = session.get('email')
    if not email:
        return render_template('index.html', error_message="Please log in first.")

    #Getting user data from db for that email
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return render_template('index.html', error_message="User not found.")

    #Getting stats and transactions for portfolio overview and table
    purchases = user.get("purchases", [])
    cash = round(user.get("cash", 0), 2)
    total_invested = round(user.get("p_total", 0), 2)
    
    current_portfolio_value = 0
    for stock in purchases:
        current_portfolio_value += stock["live_price"] * stock["quantity"]
        
    percent_change = 0
    if total_invested > 0:
        percent_change = round(((current_portfolio_value - total_invested) / total_invested) * 100, 2)
    total_value = round(current_portfolio_value + cash, 2)

    #formatting so they have 2 decimal places for cents
    cash = "{:.2f}".format(round(cash, 2))
    total_invested = "{:.2f}".format(round(total_invested, 2))
    total_value = "{:.2f}".format(round(total_value, 2))
    return render_template('portfolio_live.html', purchases=purchases, cash=cash, total_invested=total_invested, total_value=total_value, percent_change=percent_change)

@app.route('/portfolio_historical')
def portfolio_historical():
    email = session.get('email')
    if not email:
        return render_template('index.html', error_message="Please log in first.")

    #Getting user data from db for that email
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    user = users_collection.find_one({"email": email})
    if not user:
        return render_template('index.html', error_message="User not found.")
    
    #Historical purchases
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

    #Format for display (2 decimal places)
    cash = "{:.2f}".format(cash)
    total_invested = "{:.2f}".format(total_invested)
    total_value = "{:.2f}".format(total_value)
    day = user.get("day", 0)
    return render_template('portfolio_historical.html', purchases=purchases, cash=cash, total_invested=total_invested, total_value=total_value, percent_change=percent_change, day=day)

@app.route('/mode_select')
def mode_select():
    return render_template('mode_select.html')

@app.route('/stock_search')
def stock_search():
    #Creating stock search graph given user inputted ticker live mode
    ticker = request.args.get('ticker', "").upper()
    price = get_stock_price(ticker) if ticker else None
    stock_chart_base64 = stock_chart(ticker) if ticker else None
    return render_template('stock_search.html', ticker=ticker, stock_price=price, stock_chart_base64=stock_chart_base64)

@app.route('/stock_search_h')
def stock_search_h():
    # Creating stock search graph given user inputted ticker historical mode
    ticker = request.args.get('ticker', "").upper()
    price = get_stock_price_historical(ticker) if ticker else None
    stock_chart_base64 = stock_chart_historical() if ticker else None
    return render_template('stock_search_h.html', ticker=ticker, stock_price=price, stock_chart_base64=stock_chart_base64)

@app.route('/buy_stock', methods=['POST'])
def buy_stock_route():
    #Getting ticker and quantity and passing to buy stock
    ticker = request.form.get('ticker', "").upper()
    quantity = request.form.get('quantity', type=int)
    result = buy_stock(ticker, quantity)
    return render_template('stock_search.html', ticker=ticker, message=result.get("success", result.get("error")), purchase_success=True)

@app.route('/buy_stock_h', methods=['POST'])
def buy_stock_route_h():
    ticker = request.form.get('ticker', "").upper()
    quantity = request.form.get('quantity', type=int)
    result = buy_stock_h(ticker, quantity)
    return render_template('stock_search_h.html', ticker=ticker, message=result.get("success", result.get("error")), purchase_success=True)

@app.route('/sell_stock', methods=['POST'])
def sell_stock_route():
    #Getting ticker and quantity and passing to sell stock
    data = request.get_json()
    ticker = data.get('ticker', "").upper()
    quantity = data.get('quantity')
    date_str = data.get("date")
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
    result = sell_stock(ticker, quantity, date)
    #chatgpt - said to use jsonify after render_template wasn't working for sell function
    return jsonify(result)

@app.route('/sell_stock_h', methods=['POST'])
def sell_stock_route_h():
    #Getting ticker and quantity and passing to sell stock
    data = request.get_json()
    ticker = data.get('ticker', "").upper()
    quantity = data.get('quantity')
    date_str = data.get("date")
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
    result = sell_stock_h(ticker, quantity, date)
    # chatgpt - said to use jsonify after render_template wasn't working for sell function
    return jsonify(result)

@app.route('/leaderboard')
def leaderboard():
    db = client["Capstone-DB"]
    users_collection = db["my_collection"]
    users = users_collection.find({}, {"email": 1, "cash": 1, "purchases": 1})
    leaderboard_data = []

    for user in users:
        email = user.get("email", "Unknown")
        cash = round(user.get("cash", 0), 2)
        purchases = user.get("purchases", [])
        live_value = 0
        for p in purchases:
            quantity = p.get("quantity", 0)
            live_price = p.get("live_price", 0)
            live_value += quantity * live_price

        total_value = round(cash + live_value, 2)

        leaderboard_data.append({
            "email": email,
            "cash": f"{cash:.2f}",
            "live_value": f"{live_value:.2f}",
            "total_value": total_value  # kept unformatted for sorting
        })

    #Chatgpt - sort list of users by live total value descending
    leaderboard_data.sort(key=lambda x: x["total_value"], reverse=True)

    # Format total_value for display
    for entry in leaderboard_data:
        entry["total_value"] = f"{entry['total_value']:.2f}"

    return render_template("leaderboard.html", leaderboard=leaderboard_data)


# ChatGPT - Every 10 minutes calls a function to update live price
def run_price_updater():
    while True:
        update_live_stock_price()
        # Sleep for 10 minutes (600 seconds), updates price every 10 mins
        time.sleep(600)

# ChatGPT - Start the background thread
threading.Thread(target=run_price_updater, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=False)
