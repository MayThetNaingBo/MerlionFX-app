from flask import Blueprint, render_template, jsonify
import os, requests

news_bp = Blueprint('news', __name__)
gnews_api_key = os.getenv("GNEWS_API_KEY")

@news_bp.route("/news")
def news_page():
    return render_template("news.html")

@news_bp.route("/api/news")
def get_news():
    url = f"https://gnews.io/api/v4/search?q=forex&lang=en&token={gnews_api_key}"
    try:
        res = requests.get(url).json()
        return jsonify(res)
    except Exception as e:
        return {"error": str(e)}, 500
