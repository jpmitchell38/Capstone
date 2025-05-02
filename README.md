# Introduction

This project is a **Stock Market Simulation Game** that lets users experience trading stocks with two different modes

### Live Market Mode
- Simulates real-time trading by following the **live stock market**.
- Users can buy and sell stocks just like in real-world paper trading.
- Starts with a virtual **$10,000** balance.

### Historical Mode
- Allows users to trade using **historical stock data**.
- Users can control the flow of time with an **Advance Day** button.
- Starts with a virtual **$10,000** balance.

### User Authentication
- Full **login** and **sign-up** functionality.
- Allows users to save their progress and continue playing anytime.

# Installation

Follow these steps to set up the project on your local machine:

### Clone the Repository

Clone the repository and cd into that directory

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Set up Environment Variables

Create a `.env` file in the root directory of the project and add the following:

```ini
FINNHUB_KEY=your_finnhub_api_key
POLYGON_KEY=your_polygon_api_key
TIINGO_API=your_tiingo_api_key
MONGO_URI=your_mongodb_connection_string
ALPACA_KEY=your_alpaca_api_key
ALPACA_SECRET=your_alpaca_secret_key
```

### Run the Application

```bash
python app.py
```

### Access the Website

Open your browser and go to:

```
http://127.0.0.1:5000/
```