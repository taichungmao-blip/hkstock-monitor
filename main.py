import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# --- 設定區 ---
# 修正 1: 務必使用 4 位數代碼 "3668.HK" (Yahoo 不認 03668)
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
        # 修正 2: 移除手動 Session，完全交給 yfinance 處理
        coal_proxy = yf.Ticker(PROXY_COAL_STOCK)
        hist = coal_proxy.history(period="2d")
        
        if len(hist) < 2: return "數據不足", 0
        
        prev = hist['Close'].iloc[-2]
        curr = hist['Close'].iloc[-1]
        change_pct = ((curr - prev) / prev) * 100
        
        sentiment = "🔴 煤炭情緒轉弱" if change_pct < 0 else "🟢 煤炭情緒轉強"
        return f"{sentiment} (澳股 YAL: {change_pct:+.2f}%)", change_pct
    except Exception as e:
        print(f"煤價數據錯誤: {e}")
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
    
    try:
        # 修正 3: 移除 session 參數，這是解決報錯的關鍵
        # 只要代碼對 (3668.HK)，Yahoo 就能下載
        df = yf.download(STOCK_CODE, period="6mo", progress=False)
    except Exception as e:
        return f"⚠️ 下載失敗: {e}"
    
    if df.empty:
        return f"⚠️ 無法獲取 {STOCK_CODE} 數據 (請確認代碼是否正確)"

    # 處理 MultiIndex (Yahoo 新版格式)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 1. 計算均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    
    # 2. 手動計算 MACD
    df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
    
    # 取得最新數據
    last_close = float(df['Close'].iloc[-1])
    last_ma5 = float(df['MA5'].iloc[-1])
    last_ma20 = float(df['MA20'].iloc[-1])
    last_hist = float(df['Hist'].iloc[-1])

    # 策略判斷
    signal_text = "⚖️ **觀望 (Hold)**"
    
    if last_ma5 > last_ma20 and last_
