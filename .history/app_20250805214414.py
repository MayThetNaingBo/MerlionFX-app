# from flask import Flask, render_template, request, redirect, session, url_for, jsonify
# from requests_oauthlib import OAuth2Session
# from requests.auth import HTTPBasicAuth
# from datetime import datetime, timedelta
# from random import randint
# from decimal import Decimal, ROUND_HALF_UP
# import json
# import requests
# from sklearn.linear_model import LinearRegression
# import pandas as pd
# import numpy as np

# app = Flask(__name__)
# app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # Replace with strong secret key

# client_id = "AfnOhVQ6me9M3_WHdka-qdWtHle8BKBnjNGAEgXQRKqxkCDsfgT6JLqJQMhvxFMp6zMCuCYVXDkx3JuS"
# client_secret = "EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW"
# authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
# token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
# redirect_uri = 'http://127.0.0.1:5000/callback'

# # ---------------- Polygon FX -----------------
# def get_polygon_fx_pairs():
#     api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Your Polygon.io API key
#     base_url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={api_key}"
#     fx_pairs = []
#     try:
#         url = base_url
#         while url:
#             response = requests.get(url)
#             data = response.json()
#             for ticker in data.get("results", []):
#                 if ticker["ticker"].startswith("C:"):
#                     fx_pairs.append(ticker["ticker"].replace("C:", ""))
#             url = data.get("next_url")
#             if url:
#                 url += f"&apiKey={api_key}"
#         return sorted(fx_pairs)
#     except:
#         return []

# def get_fx_rate(from_ccy, to_ccy):
#     api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"
#     ticker = f"C:{from_ccy}{to_ccy}"
#     url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={api_key}"
#     try:
#         response = requests.get(url)
#         return response.json()["results"][0]["c"]
#     except:
#         return None

# # ---------------- CBM MMK -----------------
# def get_cbm_supported_currencies():
#     try:
#         url = "https://forex.cbm.gov.mm/api/latest"
#         response = requests.get(url)
#         data = response.json()
#         return sorted(data["rates"].keys())
#     except:
#         return []

# @app.route("/get_cbm_rate")
# def get_cbm_rate():
#     target = request.args.get("currency", "USD")
#     try:
#         url = "https://forex.cbm.gov.mm/api/latest"
#         response = requests.get(url)
#         data = response.json()
#         rate = data["rates"].get(target)
#         return {"currency": target, "rate": rate}
#     except Exception as e:
#         return {"error": str(e)}, 500

# @app.route("/cbm")
# def cbm_page():
#     currencies = get_cbm_supported_currencies()
#     return render_template("cbm.html", currencies=currencies)

# # ---------------- Auth -----------------
# @app.route('/')
# def home():
#     return render_template("index.html")

# @app.route('/login')
# def login():
#     paypal = OAuth2Session(client_id, redirect_uri=redirect_uri,
#         scope='openid profile email address https://uri.paypal.com/services/paypalattributes')
#     authorization_url, state = paypal.authorization_url(authorization_base_url)
#     session['oauth_state'] = state
#     return redirect(authorization_url)

# @app.route("/callback")
# def callback():
#     paypal = OAuth2Session(client_id, state=session['oauth_state'])
#     code = request.args.get('code')
#     auth = HTTPBasicAuth(client_id, client_secret)
#     body = f'grant_type=authorization_code&code={code}&redirect_uri={redirect_uri}&client_id={client_id}'
#     token = paypal.fetch_token(token_url, auth=auth, code=code, body=body, method='POST')
#     session['oauth_token'] = token
#     return redirect(url_for('services'))

# # ---------------- Services Page -----------------
# @app.route("/services")
# def services():
#     token = session['oauth_token']
#     headers = {
#         'Content-Type': "application/x-www-form-urlencoded",
#         'Authorization': "Bearer " + token["access_token"]
#     }

#     user_response = requests.get(
#         "https://api-m.sandbox.paypal.com/v1/identity/openidconnect/userinfo?schema=openid",
#         headers=headers)
#     user_data = user_response.json()

#     balance_response = requests.get(
#         "https://api-m.sandbox.paypal.com/v1/reporting/balances",
#         headers=headers)
#     balance_data = balance_response.json()

#     session['paypal_customer'] = user_data
#     session['paypal_customer_balance'] = balance_data

#     currency = balance_data["balances"][0]["total_balance"]["currency_code"]
#     value = balance_data["balances"][0]["total_balance"]["value"]

#     return render_template('services.html',
#         fName=user_data["name"],
#         fEmail=user_data["email"],
#         fPayerID=user_data["payer_id"],
#         fCCY=currency,
#         fBalance=value)

# # ---------------- Buy FX -----------------
# @app.route("/create_order", methods=["GET"])
# def create_order():
#     customer = session['paypal_customer']
#     balance = session['paypal_customer_balance']
#     invoiceID = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))

#     all_pairs = get_polygon_fx_pairs()
#     default_pair = "EURSGD" if "EURSGD" in all_pairs else all_pairs[0]
#     fx_rate = get_fx_rate(default_pair[:3], default_pair[3:])

#     return render_template("create_order.html",
#         fName=customer["name"],
#         fEmail=customer["email"],
#         fCCY=balance["balances"][0]["total_balance"]["currency_code"],
#         fBalance=balance["balances"][0]["total_balance"]["value"],
#         fPayerID=customer["payer_id"],
#         finvoiceID=invoiceID,
#         defaultPair=default_pair,
#         defaultRate=fx_rate,
#         fxPairs=all_pairs)

# @app.route("/process_order", methods=["POST"])
# def process_order():
#     token = session['oauth_token']
#     custEmail = request.form['customerEmailAdd']
#     invoiceID = request.form['invoiceID']
#     itemName = request.form['itemName']
#     itemDescription = request.form['itemDescription']
#     rawUnitAmount = Decimal(request.form['itemUnitAmount'])
#     itemQuantity = int(request.form['itemQuantity'])
#     totalAmount = (rawUnitAmount * Decimal(itemQuantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#     session["fx_total"] = str(totalAmount)
#     session["fx_quantity"] = itemQuantity
#     session["fx_unit_price"] = str(rawUnitAmount)

#     url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
#     payload = {
#         "intent": "CAPTURE",
#         "purchase_units": [{
#             "invoice_id": invoiceID,
#             "amount": {
#                 "currency_code": "SGD",
#                 "value": str(totalAmount)
#             },
#             "items": [{
#                 "name": itemName,
#                 "description": itemDescription,
#                 "unit_amount": {
#                     "currency_code": "SGD",
#                     "value": str(rawUnitAmount)
#                 },
#                 "quantity": str(itemQuantity),
#                 "category": "DIGITAL_GOODS"
#             }]
#         }],
#         "payment_source": {
#             "paypal": {
#                 "experience_context": {
#                     "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
#                     "return_url": "http://127.0.0.1:5000/capture_payment",
#                     "cancel_url": "https://example.com/cancel"
#                 }
#             }
#         }
#     }

#     headers = {
#         'Authorization': "Bearer " + token["access_token"],
#         'Content-Type': 'application/json'
#     }

#     response = requests.post(url, headers=headers, data=json.dumps(payload))
#     order_data = response.json()
#     approval_url = next((link["href"] for link in order_data["links"] if link["rel"] in ["approve", "payer-action"]), None)
#     return redirect(approval_url) if approval_url else "❌ Order creation failed"

# @app.route("/capture_payment")
# def capture_payment():
#     token = session['oauth_token']
#     order_id = request.args.get('token')
#     payer_id = request.args.get('PayerID')

#     url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
#     headers = {
#         'Content-Type': 'application/json',
#         'Authorization': "Bearer " + token["access_token"]
#     }

#     response = requests.post(url, headers=headers)
#     data = response.json()
#     payer_info = data.get("payer", {}).get("name", {})
#     return render_template("order_result.html",
#         fOrderID=data["id"],
#         fStatus=data["status"],
#         fName=payer_info.get("given_name", ""),
#         fSurname=payer_info.get("surname", ""),
#         fEmail=data.get("payer", {}).get("email_address", ""),
#         fAmount=session.get("fx_total"),
#         fUnitPrice=session.get("fx_unit_price"),
#         fQuantity=session.get("fx_quantity"),
#         fPayPalID=payer_id)

# # ---------------- Chart -----------------
# @app.route("/chart")
# def chart():
#     return render_template("chart.html", fxPairs=get_polygon_fx_pairs())

# @app.route("/api/chart_data")
# def chart_data():
#     pair = request.args.get("pair", "EURSGD")
#     days = int(request.args.get("range", 30))
#     api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"

#     end_date = datetime.today().strftime("%Y-%m-%d")
#     start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
#     url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit={days}&apiKey={api_key}"

#     try:
#         response = requests.get(url)
#         results = response.json().get("results", [])
#         dates = [datetime.fromtimestamp(d["t"]/1000).strftime('%Y-%m-%d') for d in results]
#         prices = [d["c"] for d in results]
#         return {"dates": dates, "prices": prices}
#     except:
#         return {"dates": [], "prices": []}

# # ---------------- News Placeholder -----------------
# @app.route("/news")
# def news_page():
#     return render_template("news.html")

# @app.route('/api/news')
# def get_fx_news():
#     api_key = "44efb3199f64d940271c870c1ac62f72"
#     url = f"https://gnews.io/api/v4/search?q=forex OR currency OR exchange&lang=en&token={api_key}"

#     try:
#         response = requests.get(url)
#         data = response.json()
#         articles = data.get("articles", [])
#         return jsonify({"articles": articles})
#     except Exception as e:
#         return jsonify({"error": str(e)})
    
# @app.route("/forecast")
# def forecast_page():
#     pairs = get_polygon_fx_pairs()  # Reuse your existing function
#     return render_template("forecast.html", fxPairs=pairs)

# @app.route('/api/forecast')
# def forecast_fx():
#     pair = request.args.get("pair", "USDSGD")
#     days = 30
#     api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Replace with your actual key

#     end_date = datetime.today().strftime("%Y-%m-%d")
#     start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

#     url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit={days}&apiKey={api_key}"

#     try:
#         response = requests.get(url)
#         data = response.json()
#         results = data.get("results", [])

#         if not results:
#             return {"error": "No data available for this pair."}, 400

#         # Prepare data for ML
#         df = pd.DataFrame(results)
#         df["day"] = np.arange(len(df))  # day 0 to day 29
#         X = df[["day"]]  # features
#         y = df["c"]      # close prices

#         model = LinearRegression()
#         model.fit(X, y)

#         tomorrow = [[len(df)]]  # day 30
#         predicted = model.predict(tomorrow)[0]

#         return {
#             "pair": pair,
#             "predicted_rate": round(predicted, 5),
#             "last_known": round(df['c'].iloc[-1], 5)
#         }

#     except Exception as e:
#         print("Forecast error:", e)
#         return {"error": str(e)}, 500

# if __name__ == '__main__':
#     app.run(debug=True)

# api_key = "44efb3199f64d940271c870c1ac62f72"

from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import requests
from datetime import datetime, timedelta
from random import randint
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # 🔒 Replace with a secure secret

# 🔑 PayPal OAuth Config
client_id = "AfnOhVQ6me9M3_WHdka-qdWtHle8BKBnjNGAEgXQRKqxkCDsfgT6JLqJQMhvxFMp6zMCuCYVXDkx3JuS"
client_secret = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'

# 🔑 Polygon.io API Key
polygon_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Replace with your actual key

# 🔑 GNews API Key
gnews_api_key = "44efb3199f64d940271c870c1ac62f72"


# 🔍 Utilities
def get_polygon_fx_pairs():
    base_url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={polygon_key}"
    fx_pairs = []
    try:
        url = base_url
        while url:
            res = requests.get(url)
            data = res.json()
            for t in data.get("results", []):
                if t["ticker"].startswith("C:"):
                    fx_pairs.append(t["ticker"].replace("C:", ""))
            url = data.get("next_url", None)
            if url:
                url += f"&apiKey={polygon_key}"
        return sorted(fx_pairs)
    except Exception as e:
        print("Polygon pair error:", e)
        return []


def get_fx_rate(from_ccy, to_ccy):
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_ccy}{to_ccy}/prev?adjusted=true&apiKey={polygon_key}"
    try:
        res = requests.get(url).json()
        return res["results"][0]["c"]
    except Exception as e:
        print("FX rate error:", e)
        return None


def get_cbm_supported_currencies():
    try:
        data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
        return sorted(data["rates"].keys())
    except:
        return []


# 📍 ROUTES
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login')
def login():
    try:
        paypal = OAuth2Session(client_id, redirect_uri=redirect_uri,
            scope='openid profile email address https://uri.paypal.com/services/paypalattributes')
        url, state = paypal.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        return redirect(url)
    except Exception as e:
        return str(e)


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
        return str(e)
    
    

@app.route("/services")
def services():
    try:
        token = session['oauth_token']
        headers = {
            'Authorization': "Bearer " + token["access_token"]
        }

        user = requests.get("https://api-m.sandbox.paypal.com/v1/identity/openidconnect/userinfo?schema=openid", headers=headers).json()
        balance = requests.get("https://api-m.sandbox.paypal.com/v1/reporting/balances", headers=headers).json()

        session['paypal_customer'] = user
        session['paypal_customer_balance'] = balance
        currency = balance["balances"][0]["total_balance"]["currency_code"]
        value = balance["balances"][0]["total_balance"]["value"]

        return render_template("services.html", fName=user["name"], fEmail=user["email"],
                               fPayerID=user["payer_id"], fCCY=currency, fBalance=value)
    except Exception as e:
        return str(e)


@app.route("/create_order")
def create_order():
    try:
        customer = session['paypal_customer']
        balance = session['paypal_customer_balance']
        all_pairs = get_polygon_fx_pairs()
        default = "EURSGD" if "EURSGD" in all_pairs else all_pairs[0]
        fx_rate = get_fx_rate(default[:3], default[3:])
        invoice = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))

        return render_template("create_order.html", fName=customer["name"], fEmail=customer["email"],
                               fPayerID=customer["payer_id"], fCCY=balance["balances"][0]["total_balance"]["currency_code"],
                               fBalance=balance["balances"][0]["total_balance"]["value"], finvoiceID=invoice,
                               fxPairs=all_pairs, defaultPair=default, defaultRate=fx_rate)
    except Exception as e:
        return str(e)


@app.route("/get_fx_rate")
def get_fx_rate_route():
    pair = request.args.get("pair", "")
    try:
        rate = get_fx_rate(pair[:3], pair[3:])
        return {"rate": rate}
    except:
        return {"error": "Invalid pair"}, 400


@app.route("/process_order", methods=["POST"])
def process_order():
    try:
        token = session['oauth_token']
        email = request.form['customerEmailAdd']
        itemName = request.form['itemName']
        invoiceID = request.form['invoiceID']
        unit = Decimal(request.form['itemUnitAmount']).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        qty = int(request.form['itemQuantity'])
        desc = request.form['itemDescription']
        total = (unit * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        session["fx_unit_price"] = str(unit)
        session["fx_quantity"] = qty
        session["fx_total"] = str(total)

        payload = {
            "intent": "CAPTURE",
            "payment_source": {
                "paypal": {
                    "experience_context": {
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
                    "description": desc,
                    "unit_amount": {
                        "currency_code": "SGD",
                        "value": str(unit)
                    },
                    "quantity": str(qty),
                    "category": "DIGITAL_GOODS"
                }]
            }]
        }

        headers = {'Authorization': "Bearer " + token["access_token"], 'Content-Type': 'application/json'}
        response = requests.post("https://api-m.sandbox.paypal.com/v2/checkout/orders", headers=headers, json=payload).json()
        for link in response["links"]:
            if link["rel"] in ["approve", "payer-action"]:
                return redirect(link["href"])
        return str(response)
    except Exception as e:
        return str(e)

@app.route("/capture_payment")
def capture_payment():
    try:
        token = session['oauth_token']
        orderID = request.args.get("token")
        payerID = request.args.get("PayerID")
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer " + token["access_token"]
        }
        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{orderID}/capture"
        response = requests.post(url, headers=headers)
        order = response.json()

        # ✅ Add debug: print full PayPal response
        print("🔍 PayPal capture response:", json.dumps(order, indent=2))

        # ✅ Check for success before accessing keys
        if "id" not in order or "status" not in order:
            return f"<h3>❌ Capture failed</h3><pre>{json.dumps(order, indent=2)}</pre>"

        info = order.get("payer", {}).get("name", {})
        return render_template("order_result.html",
                               fOrderID=order["id"],
                               fStatus=order["status"],
                               fName=info.get("given_name", ""),
                               fSurname=info.get("surname", ""),
                               fEmail=order.get("payer", {}).get("email_address", ""),
                               fAmount=session.get("fx_total"),
                               fPayPalID=payerID,
                               fUnitPrice=session.get("fx_unit_price"),
                               fQuantity=session.get("fx_quantity"))
    except Exception as e:
        return f"<h3>⚠️ Error during capture</h3><pre>{str(e)}</pre>"


@app.route("/chart")
def chart():
    return render_template("chart.html", fxPairs=get_polygon_fx_pairs())


@app.route("/api/chart_data")
def chart_data():
    pair = request.args.get("pair", "EURSGD")
    days = int(request.args.get("range", 30))
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit={days}&apiKey={polygon_key}"
    try:
        res = requests.get(url).json()
        dates = [datetime.fromtimestamp(d["t"] / 1000).strftime('%Y-%m-%d') for d in res["results"]]
        prices = [d["c"] for d in res["results"]]
        return {"dates": dates, "prices": prices}
    except:
        return {"dates": [], "prices": []}


# ✅ Helper function to fetch CBM rate
def fetch_cbm_rate(currency):
    try:
        data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
        return data["rates"].get(currency)
    except Exception:
        return None

# ✅ Show MMK purchase form with current CBM rate

@app.route("/cbm", methods=["GET", "POST"])
def cbm():
    cbm_data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
    rates = cbm_data["rates"]
    default_currency = "SGD"
    default_rate = rates.get(default_currency)
    return render_template("cbm.html", all_rates=rates, default_currency=default_currency, default_rate=default_rate)

# ✅ API endpoint to get live CBM rate
@app.route("/get_cbm_rate")
def get_cbm_rate_api():
    currency = request.args.get("currency", "SGD")
    allowed = ["SGD", "USD"]

    if currency not in allowed:
        return {"error": "Only SGD and USD are allowed to convert to MMK."}, 400

    try:
        data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
        rate = data["rates"].get(currency)
        return {"currency": currency, "rate": rate}
    except Exception as e:
        return {"error": str(e)}, 500

# ✅ Process CBM Purchase + PayPal Order
@app.route("/process_cbm_order", methods=["POST"])
def process_cbm_order():
    try:
        token = session['oauth_token']
        currency = request.form["currency"]  # Must be "SGD"
        mmk_amount = request.form["mmkAmount"]
        rate_str = request.form["rate"]  # From CBM (e.g., "1500.55")

        # Convert MMK → SGD
        cbm_rate = Decimal(rate_str.replace(",", ""))
        mmk_value = Decimal(mmk_amount)
        sgd_total = (mmk_value / cbm_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        invoiceID = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))

        # Save details for result page
        session["fx_unit_price"] = str(sgd_total)
        session["fx_quantity"] = 1
        session["fx_total"] = str(sgd_total)

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "invoice_id": invoiceID,
                "amount": {
                    "currency_code": "SGD",
                    "value": str(sgd_total),
                    "breakdown": {
                        "item_total": {
                            "currency_code": "SGD",
                            "value": str(sgd_total)
                        }
                    }
                },
                "items": [{
                    "name": f"CBM MMK Buy {currency}",
                    "description": f"{mmk_amount} MMK → {sgd_total} SGD",
                    "unit_amount": {
                        "currency_code": "SGD",
                        "value": str(sgd_total)
                    },
                    "quantity": "1",
                    "category": "DIGITAL_GOODS"
                }]
            }],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": "http://127.0.0.1:5000/capture_payment",
                        "cancel_url": "https://example.com/cancel"
                    }
                }
            }
        }

        headers = {
            'Authorization': "Bearer " + token["access_token"],
            'Content-Type': 'application/json'
        }

        res = requests.post("https://api-m.sandbox.paypal.com/v2/checkout/orders",
                            headers=headers, data=json.dumps(payload))
        data = res.json()

        approval_url = next((link["href"] for link in data["links"] if link["rel"] in ["approve", "payer-action"]), None)
        if approval_url:
            return redirect(approval_url)
        else:
            return f"<h3>❌ Failed to create PayPal order</h3><pre>{json.dumps(data, indent=2)}</pre>"

    except Exception as e:
        return f"<h3>⚠️ Error processing CBM order</h3><pre>{e}</pre>"
@app.route("/news")
def news_page():
    return render_template("news.html")


@app.route("/api/news")
def get_news():
    url = f"https://gnews.io/api/v4/search?q=forex&lang=en&token={gnews_api_key}"
    try:
        return requests.get(url).json()
    except Exception as e:
        return {"error": str(e)}


@app.route("/forecast")
def forecast_page():
    return render_template("forecast.html", fxPairs=get_polygon_fx_pairs())


@app.route("/api/forecast")
def predict_forecast():
    pair = request.args.get("pair", "USD/SGD").replace("/", "")
    days = 30
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit={days}&apiKey={polygon_key}"

    try:
        res = requests.get(url).json()
        close_prices = [p["c"] for p in res["results"]]
        X = np.arange(len(close_prices)).reshape(-1, 1)
        y = np.array(close_prices)
        model = LinearRegression().fit(X, y)
        tomorrow = len(close_prices)
        prediction = model.predict([[tomorrow]])
        return {"forecast": round(prediction[0], 4), "today": close_prices[-1]}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    app.run(debug=True)
