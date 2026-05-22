# Merlion FX App

Merlion FX App is a Flask-based foreign exchange web application that allows users to view currency exchange rates, check forex trends, read latest FX news, convert MMK using Central Bank of Myanmar exchange rates, forecast currency movement, and make sandbox payments through PayPal.

This project was developed as a web application project to demonstrate API integration, payment processing, currency conversion, chart visualization, and simple machine learning prediction.

---

## Features

### 1. PayPal Sandbox Login

Users can log in using PayPal Sandbox OAuth authentication.

After login, the dashboard displays:

- User name
- Email address
- PayPal payer ID
- PayPal balance

## PayPal Sandbox Testing

This project uses PayPal Sandbox for login and payment testing.

To test the PayPal features, please use your own PayPal Sandbox personal account from the PayPal Developer Dashboard.

For demo access, please contact the project owner.

---

### 2. FX Trend Chart

The dashboard includes an FX trend chart where users can:

- Select an FX currency pair
- View exchange rate trends
- Choose different time ranges such as 1 day, 7 days, or 30 days

The chart is displayed using Chart.js.

---

### 3. Latest FX News

The dashboard displays the latest foreign exchange news.

Each news item includes:

- News image
- News title
- Short description
- Read more button

---

### 4. Buy FX Currency

Users can simulate buying FX currency through PayPal Sandbox checkout.

The app allows users to:

- Select a currency pair
- View the current exchange rate
- Enter quantity
- Create a PayPal Sandbox order
- Complete sandbox payment
- View payment result

---

### 5. MMK Converter

The MMK Converter uses the Central Bank of Myanmar exchange rate API.

Users can:

- Enter MMK amount
- Convert MMK to SGD
- Proceed with PayPal Sandbox payment

---

### 6. Currency Forecast

The Currency Forecast feature predicts the next exchange rate using simple Linear Regression.

It uses historical FX data and displays:

- Last known exchange rate
- Predicted next exchange rate

---

## Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- Bootstrap
- jQuery
- Select2
- Chart.js
- PayPal Sandbox API
- Polygon.io API
- GNews API
- Central Bank of Myanmar API
- NumPy
- scikit-learn

---

## Project Structure

```bash
merlion_fx_app/
├── app.py
├── templates/
│   ├── index.html
│   ├── services.html
│   ├── create_order.html
│   ├── cbm.html
│   ├── forecast.html
│   └── order_result.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── README.md

How to Run the Project
======================

1. Open the project folder in VS Code.

2. Run these commands:

python -m venv venv
venv\Scripts\activate
pip install flask requests requests-oauthlib numpy scikit-learn python-dotenv
python app.py

3. Open this URL in your browser:

http://127.0.0.1:5000