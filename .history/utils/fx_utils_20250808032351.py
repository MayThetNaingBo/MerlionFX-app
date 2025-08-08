import requests, os

polygon_key = os.getenv("POLYGON_API_KEY")

def get_polygon_fx_pairs():
    base_url = f"https://api.polygon.io/v3/reference/tickers?market=fx&active=true&limit=1000&apiKey={polygon_key}"
    fx_pairs = []
    try:
        url = base_url
        while url:
            res = requests.get(url)
            data = res.json()
            if "results" not in data:
                break
            for t in data.get("results", []):
                if t["ticker"].startswith("C:"):
                    fx_pairs.append(t["ticker"].replace("C:", ""))
            url = data.get("next_url")
            if url:
                url += f"&apiKey={polygon_key}"
        return sorted(fx_pairs) or ["EURSGD", "USDSGD", "AUDSGD", "JPYSGD"]
    except Exception as e:
        print("❌ FX Pair Error:", e)
        return ["EURSGD", "USDSGD", "AUDSGD", "JPYSGD"]

def get_fx_rate(from_ccy, to_ccy):
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_ccy}{to_ccy}/prev?adjusted=true&apiKey={polygon_key}"
    try:
        res = requests.get(url).json()
        return res["results"][0]["c"]
    except Exception as e:
        print("FX rate error:", e)
        return None
