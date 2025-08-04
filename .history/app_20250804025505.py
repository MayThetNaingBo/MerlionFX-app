from flask import Flask, render_template, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os
import requests
from datetime import datetime, timedelta
from random import randint
from decimal import Decimal, ROUND_HALF_UP
from flask import jsonify, request

app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # Replace with a strong secret key

client_id = "AfnOhVQ6me9M3_WHdka-qdWtHle8BKBnjNGAEgXQRKqxkCDsfgT6JLqJQMhvxFMp6zMCuCYVXDkx3JuS"
client_secret = "EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW"
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'


def get_polygon_fx_pairs():
    api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Replace with your actual API key
    base_url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={api_key}"
    fx_pairs = []

    try:
        url = base_url
        while url:
            response = requests.get(url)
            data = response.json()
            results = data.get("results", [])
            for ticker in results:
                if ticker["ticker"].startswith("C:"):
                    fx_pairs.append(ticker["ticker"].replace("C:", ""))
            url = data.get("next_url", None)
            if url:
                url += f"&apiKey={api_key}"  # Append the key to the next_url

        return sorted(fx_pairs)
    except Exception as e:
        print("Error fetching full FX pairs list:", e)
        return []


def get_fx_rate(from_ccy, to_ccy):
    api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Replace with your actual Polygon API key
    ticker = f"C:{from_ccy}{to_ccy}"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        return data["results"][0]["c"]
    except Exception as e:
        print("Error fetching FX rate:", e)
        return None
    
@app.route("/get_fx_rate")
def get_fx_rate_api():
    from_to = request.args.get("pair", "")
    if len(from_to) != 6:
        return {"error": "Invalid pair"}, 400

    from_ccy = from_to[:3]
    to_ccy = from_to[3:]

    try:
        # Use your actual Polygon key
        api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"
        url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_ccy}{to_ccy}/prev?adjusted=true&apiKey={api_key}"
        response = requests.get(url)
        data = response.json()
        rate = data["results"][0]["c"]
        return {"rate": rate}
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/')
def home():
    return render_template("index.html")


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

        all_pairs = get_polygon_fx_pairs()
        default_pair = "EURSGD" if "EURSGD" in all_pairs else all_pairs[0]
        from_ccy = default_pair[:3]
        to_ccy = default_pair[3:]
        fx_rate = get_fx_rate(from_ccy, to_ccy)

        return render_template("create_order.html",
                               fName=customer["name"],
                               fEmail=customer["email"],
                               fCCY=currency,
                               fBalance=value,
                               fPayerID=customer["payer_id"],
                               finvoiceID=invoiceID,
                               defaultPair=default_pair,
                               defaultRate=fx_rate,
                               fxPairs=all_pairs)
    except Exception as e:
        print("create_order error:", e)
        return redirect(url_for('home'))


@app.route("/process_order", methods=["POST"])
def process_order():
    try:
        token = session['oauth_token']
        custEmail = request.form['customerEmailAdd']
        invoiceID = request.form['invoiceID']

        itemName = request.form['itemName']
        itemDescription = request.form['itemDescription']
        rawUnitAmount = Decimal(request.form['itemUnitAmount'])
        paypalUnitAmount = rawUnitAmount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        itemQuantity = int(request.form['itemQuantity'])
        totalAmount = (paypalUnitAmount * Decimal(itemQuantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        session["fx_unit_price"] = str(rawUnitAmount)
        session["fx_quantity"] = itemQuantity
        session["fx_total"] = str(totalAmount)

        url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

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
            "purchase_units": [
                {
                    "invoice_id": invoiceID,
                    "amount": {
                        "currency_code": "SGD",
                        "value": str(totalAmount),
                        "breakdown": {
                            "item_total": {
                                "currency_code": "SGD",
                                "value": str(totalAmount)
                            }
                        }
                    },
                    "items": [
                        {
                            "name": itemName,
                            "description": itemDescription,
                            "unit_amount": {
                                "currency_code": "SGD",
                                "value": str(paypalUnitAmount)
                            },
                            "quantity": str(itemQuantity),
                            "category": "DIGITAL_GOODS"
                        }
                    ]
                }
            ]
        })

        headers = {
            'Authorization': "Bearer " + token["access_token"],
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers, data=payload)
        order_data = response.json()

        approval_url = next((link["href"] for link in order_data["links"] if link["rel"] in ["approve", "payer-action"]), None)

        if approval_url:
            return redirect(approval_url)
        else:
            return f"<h3>❌ Failed to create PayPal order</h3><pre>{json.dumps(order_data, indent=2)}</pre>"

    except Exception as e:
        return f"<h3>⚠️ Error during order processing</h3><pre>{e}</pre>"


@app.route("/capture_payment", methods=["GET"])
def capture_payment():
    try:
        token = session['oauth_token']
        order_id = request.args.get('token')
        payer_id = request.args.get('PayerID')

        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer " + token["access_token"]
        }

        response = requests.post(url, headers=headers)
        order_data = response.json()

        if "id" not in order_data:
            return f"<h2>❌ Capture failed</h2><pre>{json.dumps(order_data, indent=2)}</pre>"

        payer_info = order_data.get("payer", {})
        name_info = payer_info.get("name", {})
        email = payer_info.get("email_address", "N/A")

        return render_template("order_result.html",
                               fOrderID=order_data["id"],
                               fStatus=order_data["status"],
                               fName=name_info.get("given_name", ""),
                               fSurname=name_info.get("surname", ""),
                               fEmail=email,
                               fAmount=session.get("fx_total"),
                               fUnitPrice=session.get("fx_unit_price"),
                               fQuantity=session.get("fx_quantity"),
                               fPayPalID=payer_id)
    except Exception as e:
        return f"<h3>⚠️ Error capturing payment</h3><pre>{e}</pre>"

@app.route("/chart")
def chart():
    pairs = get_polygon_fx_pairs()
    return render_template("chart.html", fxPairs=pairs)

@app.route("/api/chart_data")
def chart_data():
    pair = request.args.get("pair", "EURSGD")
    days = int(request.args.get("range", 30))
    api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"

    # Generate correct start and end dates
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Correct URL format using start_date and end_date
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit={days}&apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()
        results = data.get("results", [])

        dates = [datetime.fromtimestamp(d["t"] / 1000).strftime('%Y-%m-%d') for d in results]
        prices = [d["c"] for d in results]

        return {"dates": dates, "prices": prices}
    except Exception as e:
        print("Chart data error:", e)
        return {"dates": [], "prices": []}

@app.route("/fluctuation")
def fluctuation():
    return render_template("fluctuation.html")\


@app.route("/api/fluctuation_data")
def get_fluctuation_data():
    base = request.args.get("base")
    symbols = request.args.get("symbols")

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=7)

    access_key = "your_actual_api_key_here"  # Replace with your actual key

url = (
    f"https://api.exchangerate.host/timeseries"
    f"?start_date={start_date}&end_date={end_date}"
    f"&base={base}&symbols={symbols}"
    f"&access_key={access_key}"
)


    print("🔗 Requesting:", url)

    try:
        response = requests.get(url)
        data = response.json()

        print("📦 Raw response:", data)  # 👈 log response

        if not data.get("success", False) or "rates" not in data:
            return jsonify({"error": "No fluctuation data", "info": data})

        return jsonify(data)

    except Exception as e:
        print("🔥 Error:", str(e))
        return jsonify({"error": str(e)})

    
if __name__ == '__main__':
   app.run(debug=True)
