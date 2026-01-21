import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# --- 設定區 ---
# 修正 1: 去掉開頭的 0，改用 Yahoo 慣用的 3668.HK
STOCK_CODE = "3668.HK" 
PROXY_COAL_STOCK = "YAL.AX"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_message(message):
    if not DISCORD_WEBHOOK_URL:
        print("未設定 Webhook，僅列印:")
        print(message)
        return

    payload = {
        "content": message,
        "username": "港股監控機器人",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2534/2534204.png"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"發送錯誤: {e}")

def get_coal_price_sentiment():
    try:
        # 修正 2: 建立自定義 Session 以避免被擋 (404 錯誤常見原因)
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        
        coal_proxy = yf.Ticker(PROXY_COAL_STOCK, session=session)
        hist = coal_proxy.history(period="2d")
        if len(hist) < 2: return "數據不足", 0
        
        prev = hist['Close'].iloc[-2]
        curr = hist['Close'].iloc[-1]
        change_pct = ((curr - prev) / prev) * 100
        
        sentiment = "🔴 煤炭情緒轉弱" if change_pct < 0 else "🟢 煤炭情緒轉強"
        return f"{sentiment} (澳股 YAL: {change_pct:+.2f}%)", change_pct
    except Exception as e:
        print(f"煤價獲取失敗: {e}")
        return "無法獲取煤炭數據", 0

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def analyze_stock():
    print(f"正在分析 {STOCK_CODE}...")
    
    # 修正 3: 同樣為股票數據加入防擋 Session
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    try:
        # 加入 progress=False 讓 log 乾淨一點
        df = yf.download(STOCK_CODE, period="6mo", session=session, progress=False)
    except Exception as e:
        return f"⚠️ 下載失敗: {e}"
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if df.empty: 
        return f"⚠️ 無法獲取 {STOCK_CODE} 數據 (可能是 Yahoo API 暫時阻擋或代碼錯誤)"

    # 1. 計算均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # 2. 手動計算 MACD
    df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
    
    # 取得最新數據
    last_close = df['Close'].iloc[-1]
    last_ma5 = df['MA5'].iloc[-1]
    last_ma20 = df['MA20'].iloc[-1]
    last_hist = df['Hist'].iloc[-1]

    # 策略判斷
    signal_text = "⚖️ **觀望 (Hold)**"
    
    if last_ma5 > last_ma20 and last_hist > 0:
        signal_text = "🚀 **強勢買入訊號 (Buy)**"
    elif last_ma5 < last_ma20:
        signal_text = "🔻 **趨勢轉弱/賣出 (Sell)**"

    coal_sentiment_str, _ = get_coal_price_sentiment()
    
    return f"""
>>> ## 📊 【{STOCK_CODE} 監控報告】
📅 {datetime.now().strftime('%Y-%m-%d')}

**技術指標**
• 收盤: `${last_close:.2f}`
• 均線: `MA5 {last_ma5:.2f}` vs `MA20 {last_ma20:.2f}`
• 動能: {'🔼 增強' if last_hist > 0 else '🔽 減弱'}

**系統建議**
{signal_text}

**外部環境**
{coal_sentiment_str}
    """

if __name__ == "__main__":
    msg = analyze_stock()
    print(msg) # 在 Console 也印出來方便除錯
    send_discord_message(msg)
