from flask import Flask, render_template, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import json
import os


app = Flask(__name__)
app.secret_key = 'EG6vZLYReYRtUJ1tDWmNNhz2OFq5VXYnDquk9nekWjsEJxLBB8_O9CWjqwz69s_T5T5PnSs7_bPLMvGW'  # Replace with a strong key

@app.route('/')
def home():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
