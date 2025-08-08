from flask import Blueprint, render_template, session, request, redirect
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from random import randint
import requests, os, json

from utils.fx_utils import get_polygon_fx_pairs, get_fx_rate

fx_bp = Blueprint('fx', __name__)

@fx_bp.route("/services")
def services():
    token = session['oauth_token']
    headers = { 'Authorization': "Bearer " + token["access_token"] }
    user = requests.get("https://api-m.sandbox.paypal.com/v1/identity/openidconnect/userinfo?schema=openid", headers=headers).json()
    balance = requests.get("https://api-m.sandbox.paypal.com/v1/reporting/balances", headers=headers).json()

    session['paypal_customer'] = user
    session['paypal_customer_balance'] = balance
    currency = balance["balances"][0]["total_balance"]["currency_code"]
    value = balance["balances"][0]["total_balance"]["value"]

    return render_template("services.html", fName=user["name"], fEmail=user["email"],
                           fPayerID=user["payer_id"], fCCY=currency, fBalance=value,
                           fxPairs=get_polygon_fx_pairs())

@fx_bp.route("/create_order")
def create_order():
    customer = session['paypal_customer']
    balance = session['paypal_customer_balance']
    all_pairs = get_polygon_fx_pairs()
    default = "EURSGD" if "EURSGD" in all_pairs else all_pairs[0]
    fx_rate = get_fx_rate(default[:3], default[3:])
    invoice = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))

    return render_template("create_order.html", fName=customer["name"], fEmail=customer["email"],
                           fPayerID=customer["payer_id"],
                           fCCY=balance["balances"][0]["total_balance"]["currency_code"],
                           fBalance=balance["balances"][0]["total_balance"]["value"],
                           finvoiceID=invoice, fxPairs=all_pairs,
                           defaultPair=default, defaultRate=fx_rate)
