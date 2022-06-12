import os
import requests
import urllib.parse

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime

db = SQL("sqlite:///finance.db")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def getBalance():
    amount = 0
    id = session.get("user_id")

    # Check if table financial_movement exist
    checkTableFinancialMovement()

    row = db.execute("SELECT balance FROM wallet where user_id = ? ORDER BY id DESC LIMIT 1", id)

    if len(row) > 0 :
        amount = row[0]["balance"]
    else:
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute("INSERT INTO wallet (user_id, symbol, name, shares, price, type, buy_date, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", id, 0, 0, 0, 0, 0, today, 10000)
        amount = 10000
    return amount


def checkTableFinancialMovement():
    # created table if not exist
    sql = "CREATE TABLE IF NOT EXISTS wallet (id integer PRIMARY KEY, user_id integer NOT NULL, symbol text NOT NULL, name text NOT NULL, shares integer NOT NULL, price DECIMAL, type integer DEFAULT 1, buy_date text NOT NULL, balance DECIMAL DEFAULT 10000, FOREIGN KEY (user_id) REFERENCES users (id))"
    db.execute(sql)
    return


def buyQuote(price, share, symbol, name):
    amount = 0
    id = session.get("user_id")
    row = db.execute("SELECT balance FROM wallet where user_id = ? ORDER BY id DESC LIMIT 1", id)

    # check last balance
    if len(row) > 0 :
        amount = row[0]["balance"]
    else:
        amount = 10000

    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    upBalance = amount - (price * share)
    db.execute("INSERT INTO wallet (user_id, symbol, name, shares, price, type, buy_date, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", id, symbol, name, share, price, 1, today, upBalance)
    return


def sellQuote(price, share, symbol, name):
    amount = 0
    id = session.get("user_id")
    row = db.execute("SELECT balance FROM wallet where user_id = ? ORDER BY id DESC LIMIT 1", id)

    # check last balance
    if len(row) > 0 :
        amount = row[0]["balance"]
    else:
        amount = 10000

    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    upBalance = amount + (price * share)

    db.execute("INSERT INTO wallet (user_id, symbol, name, shares, price, type, buy_date, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", id, symbol, name, share, price, 2, today, upBalance)
    return