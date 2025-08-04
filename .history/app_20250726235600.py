from flask import Flask, render_template, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os
import requests
from datetime import datetime
from random import randint
from decimal import Decimal, ROUND_HALF_UP

app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # Replace with a strong key

client_id = "AfnOhVQ6me9M3_WHdka-qdWtHle8BKBnjNGAEgXQRKqxkCDsfgT6JLqJQMhvxFMp6zMCuCYVXDkx3JuS"
client_secret = "EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW"
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'

@app.route('/')
def home():
    return render_template("index.html")


def get_fx_rate(from_currency, to_currency):
    api_key = "YOUR_POLYGON_API_KEY"  # Replace with your actual key
    ticker = f"C:{from_currency}{to_currency}"
    url = f"https://api.polygon.io/v2/aggs/ticker/C:EURSGD/prev?adjusted=true&apiKey=Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"

    try:
        response = requests.get(url)
        data = response.json()
        rate = data["results"][0]["c"]  # 'c' = close price
        return float(rate)
    except Exception as e:
        print("Error fetching FX rate:", e)
        return None


@app.route('/login')
def login():
    try:
        paypal = OAuth2Session(
            client_id,
            redirect_uri=redirect_uri,
            scope='openid profile email address https://uri.paypal.com/services/paypalattributes'
        )
        authorization_url, state = paypal.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        print("Login error:", e)
        return redirect(url_for('home'))

@app.route("/callback")
def callback():
    try:
        paypal = OAuth2Session(client_id, state=session['oauth_state'])
        code = request.args.get('code')

        auth = HTTPBasicAuth(client_id, client_secret)
        body = f'grant_type=authorization_code&code={code}&redirect_uri={redirect_uri}&client_id={client_id}'

        token = paypal.fetch_token(token_url, auth=auth, code=code, body=body, method='POST')
        session['oauth_token'] = token
        return redirect(url_for('services'))
    except Exception as e:
        print("Callback error:", e)
        return redirect(url_for('home'))

@app.route("/services")
def services():
    try:
        token = session['oauth_token']
        
        # Get user profile
        user_info_url = "https://api-m.sandbox.paypal.com/v1/identity/openidconnect/userinfo?schema=openid"
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': "Bearer " + token["access_token"]
        }
        user_response = requests.get(user_info_url, headers=headers)
        user_data = user_response.json()
        session['paypal_customer'] = user_data

        # Get wallet balance
        balance_url = "https://api-m.sandbox.paypal.com/v1/reporting/balances"
        balance_response = requests.get(balance_url, headers=headers)
        balance_data = balance_response.json()
        session['paypal_customer_balance'] = balance_data

        currency = balance_data["balances"][0]["total_balance"]["currency_code"]
        value = balance_data["balances"][0]["total_balance"]["value"]

        return render_template('services.html',
                               fName=user_data["name"],
                               fEmail=user_data["email"],
                               fPayerID=user_data["payer_id"],
                               fCCY=currency,
                               fBalance=value)
    except Exception as e:
        print("Services error:", e)
        return redirect(url_for('home'))

@app.route("/create_order", methods=["GET"])
def create_order():
    try:
        customer = session['paypal_customer']
        balance = session['paypal_customer_balance']
        
        invoiceID = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))
        currency = balance["balances"][0]["total_balance"]["currency_code"]
        value = balance["balances"][0]["total_balance"]["value"]

        # 🪙 Default FX pair to show first
        from_ccy = "EUR"
        to_ccy = "SGD"
        fx_pair = f"{from_ccy}{to_ccy}"

        # 🔁 Call your get_fx_rate() function
        fx_rate = get_fx_rate(from_ccy, to_ccy)

        return render_template("create_order.html",
            fName=customer["name"],
            fEmail=customer["email"],
            fCCY=currency,
            fBalance=value,
            fPayerID=customer["payer_id"],
            finvoiceID=invoiceID,
            defaultPair=fx_pair,
            defaultRate=fx_rate
        )

    except Exception as e:
        print("create_order error:", e)
        return redirect(url_for('home'))


