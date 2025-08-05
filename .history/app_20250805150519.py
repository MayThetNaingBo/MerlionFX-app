from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os
import requests
from datetime import datetime, timedelta
from random import randint
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW' # Replace with your strong secret key

# PayPal settings
client_id = ""
client_secret = "EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'"
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'

# Polygon API
polygon_api_key = ""  # Replace with your real key

# GNews API
news_api_key = ""  # Replace with your GNews.io API key

# ----------- Utilities ------------

def get_polygon_fx_pairs():
    url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={polygon_api_key}"
    fx_pairs = []
    try:
        while url:
            response = requests.get(url)
            data = response.json()
            results = data.get("results", [])
            for ticker in results:
                if ticker["ticker"].startswith("C:"):
                    fx_pairs.append(ticker["ticker"].replace("C:", ""))
            url = data.get("next_url")
            if url:
                url += f"&apiKey={polygon_api_key}"
        return sorted(fx_pairs)
    except Exception as e:
        print("Error fetching FX pairs:", e)
        return []

def get_fx_rate(from_ccy, to_ccy):
    ticker = f"C:{from_ccy}{to_ccy}"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={polygon_api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        return data["results"][0]["c"]
    except Exception as e:
        print("FX rate error:", e)
        return None

def get_cbm_supported_currencies():
    try:
        response = requests.get("https://forex.cbm.gov.mm/api/latest")
        data = response.json()
        return sorted(data["rates"].keys())
    except Exception as e:
        print("CBM fetch error:", e)
        return []

# ----------- Auth Routes ------------

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login')
def login():
    try:
        paypal = OAuth2Session(client_id, redirect_uri=redirect_uri,
                               scope='openid profile email address https://uri.paypal.com/services/paypalattributes')
        auth_url, state = paypal.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        return redirect(auth_url)
    except Exception as e:
        print("Login error:", e)
        return redirect(url_for('home'))

@app.route("/callback")
def callback():
    try:
        paypal = OAuth2Session(client_id, state=session['oauth_state'])
        code = request.args.get('code')
        auth = HTTPBasicAuth(client_id, client_secret)
        token = paypal.fetch_token(token_url, auth=auth, code=code,
                                   body=f'grant_type=authorization_code&code={code}&redirect_uri={redirect_uri}&client_id={client_id}')
        session['oauth_token'] = token
        return redirect(url_for('services'))
    except Exception as e:
        print("Callback error:", e)
        return redirect(url_for('home'))

# ----------- Dashboard ------------

@app.route("/services")
def services():
    try:
        token = session['oauth_token']
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': "Bearer " + token["access_token"]
        }

        user_info_url = "https://api-m.sandbox.paypal.com/v1/identity/openidconnect/userinfo?schema=openid"
        user_response = requests.get(user_info_url, headers=headers)
        user_data = user_response.json()
        session['paypal_customer'] = user_data

        balance_url = "https://api-m.sandbox.paypal.com/v1/reporting/balances"
        balance_response = requests.get(balance_url, headers=headers)
        balance_data = balance_response.json()
        session['paypal_customer_balance'] = balance_data

        currency = balance_data["balances"][0]["total_balance"]["currency_code"]
        value = balance_data["balances"][0]["total_balance"]["value"]

        fx_pairs = get_polygon_fx_pairs()
        cbm_ccys = get_cbm_supported_currencies()

        return render_template("dashboard.html",
                               fEmail=user_data["email"],
                               fPayerID=user_data["payer_id"],
                               fCCY=currency,
                               fBalance=value,
                               fxPairs=fx_pairs,
                               cbmCurrencies=cbm_ccys)
    except Exception as e:
        print("Dashboard error:", e)
        return redirect(url_for('home'))

# ----------- FX Buy ------------

@app.route("/get_fx_rate")
def get_fx_rate_api():
    from_to = request.args.get("pair", "")
    if len(from_to) != 6:
        return {"error": "Invalid pair"}, 400
    from_ccy, to_ccy = from_to[:3], from_to[3:]
    rate = get_fx_rate(from_ccy, to_ccy)
    return {"rate": rate}

@app.route("/process_order", methods=["POST"])
def process_order():
    try:
        token = session['oauth_token']
        itemName = request.form['itemName']
        itemDescription = request.form['itemDescription']
        unitAmount = Decimal(request.form['itemUnitAmount'])
        quantity = int(request.form['itemQuantity'])
        total = (unitAmount * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        session.update({
            "fx_total": str(total),
            "fx_quantity": quantity,
            "fx_unit_price": str(unitAmount)
        })

        url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
        invoiceID = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))
        payload = json.dumps({
            "intent": "CAPTURE",
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": "http://127.0.0.1:5000/capture_payment",
                        "cancel_url": "https://example.com/cancel"
                    }
                }
            },
            "purchase_units": [{
                "invoice_id": invoiceID,
                "amount": {
                    "currency_code": "SGD",
                    "value": str(total),
                    "breakdown": {
                        "item_total": {
                            "currency_code": "SGD",
                            "value": str(total)
                        }
                    }
                },
                "items": [{
                    "name": itemName,
                    "description": itemDescription,
                    "unit_amount": {
                        "currency_code": "SGD",
                        "value": str(unitAmount)
                    },
                    "quantity": str(quantity),
                    "category": "DIGITAL_GOODS"
                }]
            }]
        })

        headers = {
            'Authorization': "Bearer " + token["access_token"],
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers, data=payload).json()
        approval_url = next((link["href"] for link in response["links"] if link["rel"] in ["approve", "payer-action"]), None)

        if approval_url:
            return redirect(approval_url)
        return f"<h3>❌ Failed to create order</h3><pre>{json.dumps(response, indent=2)}</pre>"
    except Exception as e:
        return f"<h3>⚠️ Error</h3><pre>{e}</pre>"

@app.route("/capture_payment")
def capture_payment():
    try:
        token = session['oauth_token']
        order_id = request.args.get("token")
        payer_id = request.args.get("PayerID")

        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer " + token["access_token"]
        }

        response = requests.post(url, headers=headers).json()

        return render_template("order_result.html",
                               fOrderID=response["id"],
                               fStatus=response["status"],
                               fName=response["payer"]["name"]["given_name"],
                               fSurname=response["payer"]["name"]["surname"],
                               fEmail=response["payer"]["email_address"],
                               fAmount=session.get("fx_total"),
                               fUnitPrice=session.get("fx_unit_price"),
                               fQuantity=session.get("fx_quantity"),
                               fPayPalID=payer_id)
    except Exception as e:
        return f"<h3>❌ Capture error</h3><pre>{e}</pre>"

# ----------- FX Chart ------------

@app.route("/api/chart_data")
def chart_data():
    pair = request.args.get("pair", "EURSGD")
    days = int(request.args.get("range", 30))
    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.today().strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit={days}&apiKey={polygon_api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        results = data.get("results", [])
        dates = [datetime.fromtimestamp(d["t"]/1000).strftime('%Y-%m-%d') for d in results]
        prices = [d["c"] for d in results]
        return {"dates": dates, "prices": prices}
    except:
        return {"dates": [], "prices": []}

# ----------- CBM MMK Converter ------------

@app.route("/get_cbm_rate")
def get_cbm_rate():
    currency = request.args.get("currency", "USD")
    try:
        data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
        return {"currency": currency, "rate": data["rates"].get(currency)}
    except Exception as e:
        return {"error": str(e)}, 500

# ----------- FX News ------------

@app.route("/api/news")
def get_fx_news():
    url = f"https://gnews.io/api/v4/search?q=forex+currency+exchange&lang=en&token={news_api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        return {"articles": data.get("articles", [])}
    except Exception as e:
        return {"error": str(e)}

# ----------- Currency Forecast ------------

@app.route("/api/forecast")
def forecast():
    pair = request.args.get("pair", "USD/SGD")
    from_ccy, to_ccy = pair.split("/")
    days = 30
    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.today().strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_ccy}{to_ccy}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit={days}&apiKey={polygon_api_key}"
    try:
        response = requests.get(url).json()
        prices = [x["c"] for x in response.get("results", [])]
        if len(prices) < 2:
            return {"error": "Not enough data to forecast."}
        X = np.array(range(len(prices))).reshape(-1, 1)
        y = np.array(prices)
        model = LinearRegression()
        model.fit(X, y)
        tomorrow_index = len(prices)
        predicted = model.predict(np.array([[tomorrow_index]]))[0]
        today_rate = prices[-1]
        return {"today": round(today_rate, 5), "predicted_rate": round(predicted, 5)}
    except Exception as e:
        return {"error": str(e)}

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
