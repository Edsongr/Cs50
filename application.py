import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, getBalance, buyQuote, sellQuote

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    ## GET CONTENT TABLE
    baln = getBalance()
    baln = round(float(baln), 2)
    cost = 0

    id = session.get("user_id")
    rows = db.execute("SELECT symbol, name, price, (SELECT SUM(shares) FROM wallet WHERE user_id = :id AND type = 1) AS qtdBuy, (SELECT SUM(shares) FROM wallet WHERE user_id = :id AND type = 2) AS qtdSell FROM wallet where user_id = :id AND symbol <> 0 GROUP BY symbol", id=id)

    for row in rows:
        if not row['qtdSell'] :
            row['qtd'] = int(row['qtdBuy'])
        else:
            row['qtd'] = int(row['qtdBuy']) - int(row['qtdSell'])

        row['total'] = round(row['qtd'] * float(row['price']), 2)
        row['price'] = round(float(row['price']), 2)
        cost += float(row['total'])

    totalGer = round(baln + cost, 2)

    return render_template("index.html", rows=rows, baln=baln, totalGer=totalGer)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        if not request.form.get("shares"):
            return apology("must provide shares", 403)

        if int(request.form.get("shares")) < 1:
            return apology("shares need positive", 403)

        # Get price quot.price
        quot = lookup(request.form.get("symbol"))
        share= request.form.get("shares")
        symbol=request.form.get("symbol")
        baln = getBalance()
        want = quot['price'] * float(share)

        if baln < want:
            return apology("Sorry your balance is less", 403)

        buyQuote(quot['price'], float(share), symbol, quot['name'])
        # Redirect user
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    # User rHistory
    id = session.get("user_id")
    rows = db.execute("SELECT * FROM wallet where user_id = :id AND symbol <> 0", id=id)

    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        quot = lookup(request.form.get("symbol"))

        # Redirect user
        return render_template("quoted.html", quot=quot)
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        #Check if exist
        if len(rows) > 0 and check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("This user is already registered", 403)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"),  generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = :username",  username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    id = session.get("user_id")

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        if not request.form.get("shares"):
            return apology("must provide shares", 403)

        if int(request.form.get("shares")) < 1:
            return apology("shares need positive", 403)

        # Get price quot.price
        symbol = request.form.get("symbol")
        share  = request.form.get("shares")
        share   = float(share)
        hasShare = 0

        rows = db.execute("SELECT (SELECT SUM(shares) FROM wallet WHERE user_id = :id AND type = 1) AS qtdBuy, (SELECT SUM(shares) FROM wallet WHERE user_id = :id AND type = 2) AS qtdSell FROM wallet where user_id = :id AND symbol <> 0 and symbol = :symbol GROUP BY symbol", id=id, symbol=symbol)

        for row in rows:
            if not row['qtdSell'] :
                hasShare += int(row['qtdBuy'])
            else:
                hasShare += int(row['qtdBuy']) - int(row['qtdSell'])

        if share > hasShare:
            return apology("Sorry your share is less", 403)

        quot = lookup(symbol)
        want = quot['price'] * share

        sellQuote(quot['price'], share, symbol, quot['name'])

        # Redirect user
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        baln = getBalance()
        rows = db.execute("SELECT symbol FROM wallet where user_id = :id AND symbol <> 0 GROUP BY symbol", id=id)

        symbols = {}

        for row in rows:
            symbols[row['symbol']] = row['symbol']

        return render_template("sell.html", symbols=symbols)


@app.route("/configuration", methods=["GET", "POST"])
@login_required
def configuration():
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("newPassword"):
            return apology("must provide New Password", 403)

        if not request.form.get("confNewPassword"):
            return apology("must provide Confirmation new Password", 403)

        if request.form.get("newPassword") != request.form.get("confNewPassword"):
            return apology("Password is diferent to the confirmation", 403)

        id = session.get("user_id")
        db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash=generate_password_hash(request.form.get("newPassword")), id=id)

        # Redirect user
        alter = 1
        return render_template("configuration.html", alter=alter)
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("configuration.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
