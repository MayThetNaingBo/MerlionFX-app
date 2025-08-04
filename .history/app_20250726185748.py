from flask import Flask, render_template, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os


app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # Replace with a strong key

client_id = "YOUR_PAYPAL_CLIENT_ID"
client_secret = "YOUR_PAYPAL_SECRET"
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'


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

