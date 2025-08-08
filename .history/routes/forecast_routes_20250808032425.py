from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
import requests, os, numpy as np
from sklearn.linear_model import LinearRegression
from utils.fx_utils import get_polygon_fx_pairs

forecast_bp = Blueprint('forecast', __name__)
polygon_key = os.getenv("POLYGON_API_KEY")

@forecast_bp.route("/forecast")
def forecast_page():
    return render_template("forecast.html", fxPairs=get_polygon_fx_pairs())

@forecast_bp.route("/api/forecast")
def get_forecast():
    pair = request.args.get("pair", "USD/SGD").replace("/", "")
    days = 30
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/C:{pair}/range/1/day/"
        f"{start}/{end}?adjusted=true&sort=asc&limit={days}&apiKey={polygon_key}"
    )

    try:
        res = requests.get(url).json()
        results = res.get("results", [])
        if not results:
            return {"error": "No historical data available for this pair."}, 400

        close_prices = [p["c"] for p in results]
        X = np.arange(len(close_prices)).reshape(-1, 1)
        y = np.array(close_prices)
        model = LinearRegression().fit(X, y)
        tomorrow = len(close_prices)
        prediction = model.predict([[tomorrow]])

        return {
            "predicted_rate": round(prediction[0], 4),
            "last_known": round(close_prices[-1], 6)
        }

    except Exception as e:
        return {"error": str(e)}, 500
