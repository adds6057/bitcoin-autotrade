import time
import pyupbit
import datetime
import requests

access = ""
secret = ""
myToken = ""

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
        if df is None or len(df) < 2:
            return None
        target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
        return target_price
    except Exception as e:
        print(f"목표가 조회 중 오류 발생: {e}")
        return None

def get_start_time(ticker):
    """시작 시간 조회"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
        if df is None or len(df) == 0:
            return None
        start_time = df.index[0]
        return start_time
    except Exception as e:
        print(f"시작 시간 조회 중 오류 발생: {e}")
        return None

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
        if df is None or len(df) < 15:
            return None
        ma15 = df['close'].rolling(15).mean().iloc[-1]
        return ma15
    except Exception as e:
        print(f"이동평균선 조회 중 오류 발생: {e}")
        return None

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

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken,"#btcauto", "autotrade start")

# 매수 가격 저장 변수
buy_price = 0
last_notification_time = None

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        if start_time is None:
            print("시작 시간을 가져올 수 없습니다. 잠시 후 다시 시도합니다.")
            time.sleep(1)
            continue

        end_time = start_time + datetime.timedelta(days=1)

        # 매일 9시 1분에 목표가 알림
        if now.hour == 9 and now.minute == 1:
            if last_notification_time is None or last_notification_time.date() != now.date():
                target_price = get_target_price("KRW-BTC", 0.5)
                if target_price is not None:
                    post_message(myToken, "#btcauto", f"오늘의 목표 매수가: {target_price:,.0f}원")
                    last_notification_time = now

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", 0.5)
            ma15 = get_ma15("KRW-BTC")
            current_price = get_current_price("KRW-BTC")
            
            if target_price is None or ma15 is None or current_price is None:
                print("가격 정보를 가져올 수 없습니다. 잠시 후 다시 시도합니다.")
                time.sleep(1)
                continue
            
            # 손절/익절 체크
            if buy_price > 0:
                profit_rate = (current_price - buy_price) / buy_price * 100
                
                # 손절 (-2%)
                if profit_rate <= -2:
                    btc = get_balance("BTC")
                    if btc > 0.00008:
                        sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                        post_message(myToken,"#btcauto", f"손절매 실행: {profit_rate:.2f}%")
                        buy_price = 0
                
                # 익절 (10%)
                elif profit_rate >= 10:
                    btc = get_balance("BTC")
                    if btc > 0.00008:
                        sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                        post_message(myToken,"#btcauto", f"익절매 실행: {profit_rate:.2f}%")
                        buy_price = 0

            if target_price < current_price and ma15 < current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
                    if buy_result:
                        buy_price = current_price
                        post_message(myToken,"#btcauto", f"BTC 매수: {current_price:,.0f}원")
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                post_message(myToken,"#btcauto", "일일 매도 실행")
                buy_price = 0
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken,"#btcauto", str(e))
        time.sleep(1)