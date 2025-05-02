from pymongo.mongo_client import MongoClient #pip install pymongo
from pymongo.server_api import ServerApi
from dotenv import load_dotenv 
import os
from flask import request, render_template
#pip install bcrypt
import bcrypt
from flask import session

load_dotenv()
uri = os.getenv("MONGO_URI")
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))


def user_sign_up():
    #Getting user input for email/password
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    re_password = request.form.get("re-password", "")
    if password != re_password:
        error_message = "Passwords do not match, please try again."
        return render_template('register.html', error_message=error_message)

    #Connecting to db and checking if email already exists
    db = client["Capstone-DB"]
    collection = db["my_collection"]
    existing_user = collection.find_one({"email": email})
    session["email"] = email
    if existing_user:
        error_message = "Email already registered. Please log in."
        return render_template("register.html", error_message=error_message)

    # ChatGPT - Hashed password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    # Creating new account blank portfolio
    user_data = {
        "email": email,
        "password": hashed_password.decode("utf-8"),
        "cash": 10000,
        "cash_h": 10000,
        "p_total": 0,
        "p_total_h": 0,
        "hist_date": '2022-01-03T00:00:00Z',
        "day": 1,
        "purchases": [],
        "purchases_h":[]  
    }
    collection.insert_one(user_data)
    return render_template("mode_select.html")


def user_log_in():
    #Getting user input email/password
    email = request.form.get("email", "")
    password = request.form.get("password", "")

    #Connecting to db checking if user is registered
    db = client["Capstone-DB"]
    collection = db["my_collection"]
    user = collection.find_one({"email": email})
    session["email"] = email
    if not user:
        error_message = "Email not found. Please register first."
        return render_template("index.html", error_message=error_message)

    # ChatGPT - Checking if password matches whats stored in db
    stored_hashed_password = user.get("password", "")
    if bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
        return render_template("mode_select.html")  
    else:
        error_message = "Invalid password. Please try again."
        return render_template("index.html", error_message=error_message)