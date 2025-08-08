from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import requests
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from dotenv import load_dotenv
import os
from sklearn.linear_model import LinearRegression
import uuid  # ✅ For unique invoice IDs

app = Flask(__name__)
load_dotenv()

app.secret_key = os.getenv("FLASK_SECRET_KEY")
client_id = os.getenv("PAYPAL_CLIENT_ID")
client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
polygon_key = os.getenv("POLYGON_API_KEY")
gnews_api_key = os.getenv("GNEWS_API_KEY")

authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'


def get_polygon_fx_pairs():
    base_url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={polygon_key}"
    fx_pairs = []
    try:
        url = base_url
        while url:
            res = requests.get(url)
            data = res.json()
            if "results" not in data:
                print("Polygon API error or no results:", data)
                break
            for t in data.get("results", []):
                if t["ticker"].startswith("C:"):
                    fx_pairs.append(t["ticker"].replace("C:", ""))
            url = data.get("next_url")
            if url:
                url += f"&apiKey={polygon_key}"
        if not fx_pairs:
            fx_pairs = ["EURSGD", "USDSGD", "AUDSGD", "JPYSGD"]
            print("Using fallback FX pairs:", fx_pairs)
        return sorted(fx_pairs)
    except Exception as e:
        print("Polygon pair error:", e)
        return ["EURSGD", "USDSGD", "AUDSGD", "JPYSGD"]


def get_fx_rate(from_ccy, to_ccy):
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_ccy}{to_ccy}/prev?adjusted=true&apiKey={polygon_key}"
    try:
        res = requests.get(url).json()
        return res["results"][0]["c"]
    except Exception as e:
        print("FX rate error:", e)
        return None


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

        return render_template("services.html", fName=user["name"], fEmail=user["email"],
                               fPayerID=user["payer_id"],
                               fCCY=balance["balances"][0]["total_balance"]["currency_code"],
                               fBalance=balance["balances"][0]["total_balance"]["value"],
                               fxPairs=get_polygon_fx_pairs())
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
        invoice = str(uuid.uuid4())  # ✅ Unique

        return render_template("create_order.html", fName=customer["name"], fEmail=customer["email"],
                               fPayerID=customer["payer_id"],
                               fCCY=balance["balances"][0]["total_balance"]["currency_code"],
                               fBalance=balance["balances"][0]["total_balance"]["value"],
                               finvoiceID=invoice,
                               fxPairs=all_pairs, defaultPair=default, defaultRate=fx_rate)
    except Exception as e:
        return str(e)


@app.route("/process_order", methods=["POST"])
def process_order():
    try:
        token = session['oauth_token']
        session["cbm_purchase"] = False

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

        print("PayPal capture response:", json.dumps(order, indent=2))

        if "id" not in order or "status" not in order:
            return f"<h3>Capture failed</h3><pre>{json.dumps(order, indent=2)}</pre>"

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
        return f"<h3>Error during capture</h3><pre>{str(e)}</pre>"


@app.route("/process_cbm_order", methods=["POST"])
def process_cbm_order():
    try:
        token = session['oauth_token']
        currency = request.form["currency"]
        mmk_amount = request.form["mmkAmount"]  # ✅ Now defined early
        rate_str = request.form["rate"]

        session["cbm_purchase"] = True
        session["fx_original_mmk"] = str(mmk_amount)

        cbm_rate = Decimal(rate_str.replace(",", ""))
        mmk_value = Decimal(mmk_amount)
        sgd_total = (mmk_value / cbm_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        invoiceID = str(uuid.uuid4())  # ✅ Use UUID

        session["fx_unit_price"] = str(sgd_total)
        session["fx_quantity"] = mmk_amount
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
            return f"<h3>Failed to create PayPal order</h3><pre>{json.dumps(data, indent=2)}</pre>"

    except Exception as e:
        return f"<h3>Error processing CBM order</h3><pre>{e}</pre>"
