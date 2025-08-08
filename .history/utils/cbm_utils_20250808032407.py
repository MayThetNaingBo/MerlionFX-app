import requests

def fetch_cbm_rate(currency):
    try:
        data = requests.get("https://forex.cbm.gov.mm/api/latest").json()
        return data["rates"].get(currency)
    except:
        return None
