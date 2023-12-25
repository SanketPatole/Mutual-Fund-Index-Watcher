from flask import Flask, jsonify, render_template, request
import yfinance as yf
import os.path
import os
import signal
from datetime import datetime, timedelta
import pytz
import json

ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)
yesterday_ist = now_ist - timedelta(days=1)

tickers = {"^NSEI": "Nifty 50 Total Return Index",
   "^BSESN": "S&P BSE Sensex Total Return Index",
   "NIFTYMIDCAP150.NS": "Nifty Midcap 150 Total Return Index",
   "NIFTYSMLCAP250.NS": "Nifty Smallcap 250 Total Return Index",
   "GC=F": "Domestic Price of Gold",
   "^CNXCMDT": "Nifty Commodities Total Return Index"}

periods = {2:"1 Day", 6: "1 Week", 21: "1 Month", 61: "3 Months", 121: "6 Months"}
app = Flask(__name__)

def get_ranges():
  ranges = []
  pct = 0
  inc = 0.5
  i = 0
  while pct < 100:
      l = pct
      u = pct + inc
      pct = u
      if pct >= 100:
          ranges.append([l, 100])
          break
      ranges.append([l, u])
      i += 1
      if i == 5:
          i = 0
          inc *= 2
  return ranges

def is_market_open():
  latest_data = yf.Ticker("^NSEI").history(period='1d')
  last_date = latest_data.index.to_list()[-1].date()
  if now_ist.date() > last_date:
      return "Closed"
  else:
      return "Open"

def get_invest_amt(changes, ticker_symbol):
  min_period = None
  min_change = 999
  invest_amt = 0.0
  base_amt = 2000
  period_divisors = {"1 Day": 1, "1 Week": 2, "1 Month": 4, "3 Months": 8, "6 Months": 16}
  ticker_divisors = {"^NSEI": 1, "^BSESN": 1, "NIFTYMIDCAP150.NS": 2, "NIFTYSMLCAP250.NS": 2, "GC=F": 4, "^CNXCMDT": 4}
  for period in changes.keys():
    if float(changes[period][:-1]) < min_change:
      min_change = float(changes[period][:-1])
      min_period = period
  if min_change >= 0:
    return "₹" + str(invest_amt)
  else:
    ranges = get_ranges()
    window = 1
    for range in ranges:
      if range[0] <= abs(min_change) <= range[1]:
        invest_amt = (window*base_amt/period_divisors[min_period])/ticker_divisors[ticker_symbol]
        break
      window += 1
    return "₹" + str(invest_amt)

def get_data(tickers, periods):
  data_table = dict()
  for ticker_symbol in tickers.keys():
    ticker_object = yf.Ticker(ticker_symbol)
    ticker_name = tickers[ticker_symbol]
    data = ticker_object.history(period='1y')
    data = data['Close']
    if data.shape[0] < 121:
      continue
    else:
      data_table[ticker_name] = dict()
    for days in periods:
      period_name = periods[days]
      latest_close = data.iloc[-1]
      prev_close = data.iloc[-days]
      change = str(round((latest_close - prev_close) * 100 / prev_close, 3))+'%'
      data_table[ticker_name][period_name] = change
    invest_amt = get_invest_amt(data_table[ticker_name], ticker_symbol)
    data_table[ticker_name]["Investment Amount"] = str(invest_amt)
  return data_table


@app.route('/')
def index():

  def stopServer():
      os.kill(os.getpid(), signal.SIGINT)
      return jsonify({ "success": True, "message": "Server is shutting down..." })

  try:
    file_path = ""
    if now_ist.hour < 17:
      file_path = yesterday_ist.strftime('%Y_%m_%d.dat')
    else:
      file_path = now_ist.strftime('%Y_%m_%d.dat')
  
    json_data = {}
    if os.path.exists(file_path):
      with open(file_path, 'r') as file:
        json_data = json.load(file)
    else:
      json_data = get_data(tickers, periods)
      with open(file_path, 'w') as file:
        json.dump(json_data, file)
    return render_template('index.html', data=json_data, market_status=is_market_open())

  finally:
    stopServer()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
