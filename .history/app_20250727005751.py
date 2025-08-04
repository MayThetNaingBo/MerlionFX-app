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




def get_polygon_fx_pairs():
    api_key = "Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"  # Replace with your actual key
    url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()
        tickers = data.get("results", [])
        fx_pairs = [ticker["ticker"].replace("C:", "") for ticker in tickers if ticker["ticker"].startswith("C:")]
        return sorted(fx_pairs)
    except Exception as e:
        print("Error fetching FX pairs from Polygon:", e)
        return []


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
                # Dynamically get FX pairs
        all_pairs = get_polygon_fx_pairs()
        default_pair = "EURSGD" if "EURSGD" in all_pairs else all_pairs[0]
        fx_rate = get_polygon_fx_pairs(default_pair[:3], default_pair[3:])

        from_ccy = default_pair[:3]
        to_ccy = default_pair[3:]


        return render_template("create_order.html",
            fName=customer["name"],
            fEmail=customer["email"],
            fCCY=currency,
            fBalance=value,
            fPayerID=customer["payer_id"],
            finvoiceID=invoiceID,
            defaultPair=default_pair,
            defaultRate=fx_rate,
            fxPairs=all_pairs
        )


    except Exception as e:
        print("create_order error:", e)
        return redirect(url_for('home'))

@app.route("/process_order", methods=["POST"])
def process_order():
    try:
        token = session['oauth_token']

        # Extract form data
        custEmail = request.form['customerEmailAdd']
        invoiceID = request.form['invoiceID']

        itemName = request.form['itemName']
        itemDescription = request.form['itemDescription']
        rawUnitAmount = Decimal(request.form['itemUnitAmount'])  # original 5 decimal
        paypalUnitAmount = rawUnitAmount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # 2 decimal
        itemQuantity = int(request.form['itemQuantity'])
        totalAmount = (paypalUnitAmount * Decimal(itemQuantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Save original value for UI display
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


# def get_fx_rate(from_currency, to_currency):
#     api_key = "YOUR_POLYGON_API_KEY"  # Replace with your actual key
#     ticker = f"C:{from_currency}{to_currency}"
#     url = f"https://api.polygon.io/v2/aggs/ticker/C:EURSGD/prev?adjusted=true&apiKey=Coh8pjpp44y_Bg9NDWTlWQKCPvUcDxQy"

#     try:
#         response = requests.get(url)
#         data = response.json()
#         rate = data["results"][0]["c"]  # 'c' = close price
#         return float(rate)
#     except Exception as e:
#         print("Error fetching FX rate:", e)
#         return None


# @app.route("/process_order", methods=["POST"])
# def process_order():
#     try:
#         token = session['oauth_token']

#         # Extract form data
#         custEmail = request.form['customerEmailAdd']
#         invoiceID = request.form['invoiceID']
        
#         itemName = request.form['itemName']
#         itemDescription = request.form['itemDescription']
#         itemUnitAmountFull = Decimal(request.form['itemUnitAmount'])  # e.g., 1.50309
#         itemQuantity = int(request.form['itemQuantity'])

#         # Compute full total for display
#         totalAmountDisplay = (itemUnitAmountFull * Decimal(itemQuantity)).quantize(Decimal('0.01'))

#         # Round unit price for PayPal (2 decimal places only)
#         itemUnitAmountRounded = itemUnitAmountFull.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#         totalAmountPayPal = (itemUnitAmountRounded * Decimal(itemQuantity)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#         # Save full values in session for display later
#         session["unit_price_full"] = str(itemUnitAmountFull)
#         session["quantity"] = str(itemQuantity)
#         session["total_display"] = str(totalAmountDisplay)

#         # PayPal Order creation
#         url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
#         payload = json.dumps({
#             "intent": "CAPTURE",
#             "payment_source": {
#                 "paypal": {
#                     "experience_context": {
#                         "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
#                         "landing_page": "LOGIN",
#                         "shipping_preference": "NO_SHIPPING",
#                         "user_action": "PAY_NOW",
#                         "return_url": "http://127.0.0.1:5000/capture_payment",
#                         "cancel_url": "https://example.com/cancel"
#                     }
#                 }
#             },
#             "purchase_units": [{
#                 "invoice_id": invoiceID,
#                 "amount": {
#                     "currency_code": "SGD",
#                     "value": str(totalAmountPayPal),
#                     "breakdown": {
#                         "item_total": {
#                             "currency_code": "SGD",
#                             "value": str(totalAmountPayPal)
#                         }
#                     }
#                 },
#                 "items": [{
#                     "name": itemName,
#                     "description": itemDescription,
#                     "unit_amount": {
#                         "currency_code": "SGD",
#                         "value": str(itemUnitAmountRounded)
#                     },
#                     "quantity": str(itemQuantity),
#                     "category": "DIGITAL_GOODS"
#                 }]
#             }]
#         })

#         headers = {
#             'Authorization': "Bearer " + token["access_token"],
#             'Content-Type': 'application/json'
#         }

#         response = requests.post(url, headers=headers, data=payload)
#         order_data = response.json()

#         approval_url = next((link["href"] for link in order_data["links"] if link["rel"] in ["approve", "payer-action"]), None)

#         if approval_url:
#             return redirect(approval_url)
#         else:
#             return f"<h3>❌ Failed to create PayPal order</h3><pre>{json.dumps(order_data, indent=2)}</pre>"

#     except Exception as e:
#         return f"<h3>⚠️ Error during order processing</h3><pre>{e}</pre>"

# @app.route("/capture_payment", methods=["GET"])
# def capture_payment():
#     try:
#         token = session['oauth_token']
#         order_id = request.args.get('token')
#         payer_id = request.args.get('PayerID')

#         url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
#         headers = {
#             'Content-Type': 'application/json',
#             'Authorization': "Bearer " + token["access_token"]
#         }

#         response = requests.post(url, headers=headers)
#         order_data = response.json()

#         if "id" not in order_data:
#             return f"<h2>❌ Capture failed</h2><pre>{json.dumps(order_data, indent=2)}</pre>"

#         payer_info = order_data.get("payer", {})
#         name_info = payer_info.get("name", {})
#         email = payer_info.get("email_address", "N/A")
#         amount = order_data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]

#         return render_template("order_result.html",
#                                fOrderID=order_data["id"],
#                                fStatus=order_data["status"],
#                                fName=name_info.get("given_name", ""),
#                                fSurname=name_info.get("surname", ""),
#                                fEmail=email,
#                                fAmount=amount,
#                                fPayPalID=payer_id,
#                                fTrueUnit=session.get("unit_price_full", "N/A"),
#                                fQuantity=session.get("quantity", "N/A"),
#                                fTotal=session.get("total_display", "N/A"))

#     except Exception as e:
#         return f"<h3>⚠️ Error capturing payment</h3><pre>{e}</pre>"