from flask import Flask, render_template, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os
import requests
from datetime import datetime
from random import randint

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

        return render_template('create_order.html',
                               fName=customer["name"],
                               fEmail=customer["email"],
                               fCCY=currency,
                               fBalance=value,
                               fPayerID=customer["payer_id"],
                               finvoiceID=invoiceID)
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
        itemUnitAmount = float(request.form['itemUnitAmount'])
        itemName = request.form['itemName']
        itemDescription = request.form['itemDescription']
        itemQuantity = int(request.form['itemQuantity'])
        totalAmount = itemQuantity * itemUnitAmount

        # PayPal Order creation URL
        url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

        # Payload in PayPal format
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
                        "value": f"{totalAmount:.2f}",
                        "breakdown": {
                            "item_total": {
                                "currency_code": "SGD",
                                "value": f"{totalAmount:.2f}"
                            }
                        }
                    },
                    "items": [
                        {
                            "name": itemName,
                            "description": itemDescription,
                            "unit_amount": {
                                "currency_code": "SGD",
                                "value": f"{itemUnitAmount:.2f}"
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

        # Extract PayPal approval URL
        approval_url = next((link["href"] for link in order_data["links"] if link["rel"] == "approve"), None)

        if approval_url:
            return redirect(approval_url)
        else:
            return f"<h3>❌ Failed to create PayPal order</h3><pre>{json.dumps(order_data, indent=2)}</pre>"

    except Exception as e:
        return f"<h3>⚠️ Error during order processing</h3><pre>{e}</pre>"
