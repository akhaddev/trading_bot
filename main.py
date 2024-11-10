import requests
import time
import hashlib
import hmac
import json

BYBIT_API_KEY = 'your_bybit_api_key'
BYBIT_SECRET = 'your_bybit_secret'

TELEGRAM_BOT_TOKEN = '7861409185:AAGEP7GDLZ2tNB0QNbRj8UyGy7Tr6ShiSKY'
TELEGRAM_CHAT_ID = '399785783'

SYMBOL = "BTCUSDT"
ORDER_SIDE = "Buy"
PROFIT_PERCENTAGE = 0.001  

def get_signature(params, secret):
    """
    Generate the HMAC signature for the API request
    """
    return hmac.new(
        secret.encode(),
        '&'.join(f"{key}={value}" for key, value in sorted(params.items())).encode(),
        hashlib.sha256,
    ).hexdigest()

def place_order(symbol, side, qty, price=None):
    """
    Place an order on Bybit
    """
    endpoint = "https://api.bybit.com/v2/private/order/create"
    params = {
        'api_key': BYBIT_API_KEY,
        'symbol': symbol,
        'side': side,
        'order_type': 'Market',
        'qty': qty,
        'time_in_force': 'GoodTillCancel',
        'timestamp': int(time.time() * 1000),
    }
    params['sign'] = get_signature(params, BYBIT_SECRET)
    response = requests.post(endpoint, data=params, verify=True)
    return response.json()

def get_latest_price(symbol):
    """
    Fetch the latest price of the symbol from Bybit
    """
    try:
        response = requests.get(f"https://api.bybit.com/v2/public/tickers?symbol={symbol}", verify=True)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return None

        print(f"Response Content: {response.text}")

        data = response.json()
        if 'result' in data and data['result']:
            return float(data['result'][0]['last_price'])
        else:
            print("Error: Unexpected response format")
            return None
    except requests.exceptions.JSONDecodeError:
        print("Error decoding JSON response")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def get_open_position(symbol):
    """
    Fetch the open position for the given symbol from Bybit
    """
    endpoint = "https://api.bybit.com/v2/private/position/list"
    params = {
        'api_key': BYBIT_API_KEY,
        'symbol': symbol,
        'timestamp': int(time.time() * 1000),
    }
    params['sign'] = get_signature(params, BYBIT_SECRET)
    response = requests.get(endpoint, params=params, verify=True)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return None

    data = response.json()
    if 'result' in data:
        return data['result']
    return None

def close_position(symbol, side, qty):
    """
    Close the position by placing a market order in the opposite direction
    """
    opposite_side = 'Sell' if side == 'Buy' else 'Buy'
    return place_order(symbol, opposite_side, qty)

def send_telegram_message(message):
    """
    Send a message to the Telegram bot
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        response = requests.get(url, params=params, verify=True)
        print(f"Telegram Message Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

def main():
    """
    Main function to place the order and monitor the position
    """
    latest_price = get_latest_price(SYMBOL)
    if latest_price is None:
        print("Failed to fetch latest price.")
        return

    quantity = 0.001  

    print("Placing order...")
    order_response = place_order(SYMBOL, ORDER_SIDE, quantity)
    if order_response['ret_code'] != 0:
        print("Failed to place order:", order_response)
        return
    print("Order placed:", order_response)

    entry_price = latest_price
    target_price = entry_price * (1 + PROFIT_PERCENTAGE if ORDER_SIDE == 'Buy' else 1 - PROFIT_PERCENTAGE)
    print(f"Target price for profit: {target_price}")

    while True:
        time.sleep(5)  
        latest_price = get_latest_price(SYMBOL)
        if latest_price is None:
            continue

        position = get_open_position(SYMBOL)
        if not position or float(position[0]['size']) == 0:
            print("No open position found, exiting.")
            break

        current_price = float(position[0]['entry_price'])
        if (ORDER_SIDE == 'Buy' and latest_price >= target_price) or \
           (ORDER_SIDE == 'Sell' and latest_price <= target_price):
            print("Target reached, closing position.")
            close_response = close_position(SYMBOL, ORDER_SIDE, quantity)
            print("Close response:", close_response)
            send_telegram_message("Position closed with target profit.")
            break

if __name__ == "__main__":
    main()
