from flask import Blueprint, redirect, session, request, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import os

auth_bp = Blueprint('auth', __name__)
client_id = os.getenv("PAYPAL_CLIENT_ID")
client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
authorization_base_url = 'https://www.sandbox.paypal.com/signin/authorize?flowEntry=static'
token_url = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'
redirect_uri = 'http://127.0.0.1:5000/callback'

@auth_bp.route("/login")
def login():
    paypal = OAuth2Session(client_id, redirect_uri=redirect_uri,
        scope='openid profile email address https://uri.paypal.com/services/paypalattributes')
    url, state = paypal.authorization_url(authorization_base_url)
    session['oauth_state'] = state
    return redirect(url)

@auth_bp.route("/callback")
def callback():
    paypal = OAuth2Session(client_id, state=session['oauth_state'])
    code = request.args.get('code')
    auth = HTTPBasicAuth(client_id, client_secret)
    body = f'grant_type=authorization_code&code={code}&redirect_uri={redirect_uri}&client_id={client_id}'
    token = paypal.fetch_token(token_url, auth=auth, code=code, body=body, method='POST')
    session['oauth_token'] = token
    return redirect(url_for('fx.services'))
