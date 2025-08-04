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

