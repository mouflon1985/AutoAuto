import time
import pyupbit
import datetime
import requests
import schedule
from fbprophet import Prophet


# 3% 이상 오르면 매도 추가

access = "J"
secret = "n"
myToken = "xoxp-1936335540372-1942786429489-2686645119552-1933cd874b79b2ecae9cc95f569f43b4"

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma5(ticker):
    """5일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    return ma5

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

predicted_close_price = 0
def predict_price(ticker):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute60", count=700)
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
predict_price("KRW-ENJ")
schedule.every().hour.do(lambda: predict_price("KRW-ENJ"))

target_price = get_target_price("KRW-ENJ", 0.3)

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken,"#stock", "autotrade start")
post_message(myToken,"#stock", "예상종가 :" + str(predicted_close_price)) 
post_message(myToken,"#stock", "목표가 :" + str(target_price))

schedule.every(6).hour.do(lambda: post_message(myToken,"#stock", "예상종가 :" + str(predicted_close_price)))
schedule.every(6).hour.do(lambda: post_message(myToken,"#stock", "목표가 :" + str(target_price)))

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-ENJ")
        end_time = start_time + datetime.timedelta(days=1)
        schedule.run_pending()

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-ENJ", 0.3)
            ma5 = get_ma5("KRW-ENJ")
            current_price = get_current_price("KRW-ENJ")
            if target_price < current_price and ma5 < current_price and current_price < predicted_close_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-ENJ", "900000", krw*0.9995)
                    post_message(myToken,"#stock", "Coin buy : " +str(buy_result))
        else:
            btc = get_balance("BTC")
            avg_price = btc[0]
            balance = btc[1]
            buy_profit = ((current_price - avg_price) / avg_price) *100
            profit = round(buy_profit, 2)
            #현재 보유 코인 수익률 계산

            if btc > 0.00008 or profit >= 10.0:
                sell_result = upbit.sell_market_order("KRW-ENJ")
                post_message(myToken,"#stock", "Coin sell : " +str(sell_result))
        time.sleep(1)

    except Exception as e:
        print(e)
        time.sleep(1)