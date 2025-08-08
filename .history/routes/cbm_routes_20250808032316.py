from flask import Blueprint, render_template, request, session, redirect
from utils.cbm_utils import fetch_cbm_rate
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from random import randint
import requests, json

cbm_bp = Blueprint('cbm', __name__)

@cbm_bp.route("/cbm", methods=["GET", "POST"])
def cbm():
    cbm_data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
    rates = cbm_data["rates"]
    default_currency = "SGD"
    default_rate = rates.get(default_currency)
    return render_template("cbm.html", all_rates=rates, default_currency=default_currency, default_rate=default_rate)

@cbm_bp.route("/get_cbm_rate")
def get_cbm_rate_api():
    currency = request.args.get("currency", "SGD")
    rate = fetch_cbm_rate(currency)
    if rate:
        return {"currency": currency, "rate": rate}
    return {"error": "Invalid currency code."}, 400

@cbm_bp.route("/process_cbm_order", methods=["POST"])
def process_cbm_order():
    try:
        token = session['oauth_token']
        currency = request.form["currency"]
        mmk_amount = request.form["mmkAmount"]
        rate_str = request.form["rate"]
        cbm_rate = Decimal(rate_str.replace(",", ""))
        mmk_value = Decimal(mmk_amount)
        sgd_total = (mmk_value / cbm_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        invoiceID = datetime.now().strftime("%Y%m%d%H%M%S") + str(randint(100, 999))

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
        return f"<h3>❌ Failed to create PayPal order</h3><pre>{json.dumps(data, indent=2)}</pre>"

    except Exception as e:
        return f"<h3>⚠️ Error processing CBM order</h3><pre>{e}</pre>"
