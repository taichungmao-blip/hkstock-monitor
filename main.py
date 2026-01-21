import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
from datetime import datetime

# --- 設定區 ---
STOCK_CODE = "03668.HK"
PROXY_COAL_STOCK = "YAL.AX" # 澳洲母公司作為煤價情緒指標

# 從 GitHub Secrets 獲取 Discord Webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_message(message):
    """發送訊息到 Discord"""
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL，僅列印內容:")
        print(message)
        return

    # Discord 訊息格式 Payload
    payload = {
        "content": message,
        "username": "港股監控機器人",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2534/2534204.png" # 隨意放個股票圖示
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print("✅ Discord 通知發送成功")
        else:
            print(f"⚠️ 發送失敗: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"❌ 發送錯誤: {e}")

def get_coal_price_sentiment():
    """抓取澳洲母公司(YAL.AX)漲跌幅"""
    try:
        coal_proxy = yf.Ticker(PROXY_COAL_STOCK)
        hist = coal_proxy.history(period="2d")
        
        if len(hist) < 2:
            return "數據不足", 0
            
        prev_close = hist['Close'].iloc[-2]
        curr_price = hist['Close'].iloc[-1]
        change_pct = ((curr_price - prev_close) / prev_close) * 100
        
        sentiment = "🔴 煤炭情緒轉弱" if change_pct < 0 else "🟢 煤炭情緒轉強"
        return f"{sentiment} (澳股 YAL: {change_pct:+.2f}%)", change_pct
    except Exception as e:
        return f"無法獲取煤炭數據: {str(e)}", 0

def analyze_stock():
    # 下載數據
    print(f"正在分析 {STOCK_CODE}...")
    df = yf.download(STOCK_CODE, period="6mo")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if df.empty:
        return "⚠️ 無法獲取股價數據"

    # 計算技術指標
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)
    
    # 取得最新數據
    last_close = df['Close'].iloc[-1]
    last_ma5 = df['MA5'].iloc[-1]
    last_ma20 = df['MA20'].iloc[-1]
    last_hist = df.iloc[-1][df.columns.str.contains('MACDh')].values[0]

    # 策略判斷
    signal = "⚖️ **觀望 (Hold)**"
    color_emoji = "⚪"
    
    if last_ma5 > last_ma20 and last_hist > 0:
        signal = "🚀 **強勢買入訊號 (Buy)**"
        color_emoji = "🟢"
    elif last_ma5 < last_ma20:
        signal = "🔻 **趨勢轉弱/賣出 (Sell)**"
        color_emoji = "🔴"

    # 獲取煤炭情緒
    coal_sentiment_str, _ = get_coal_price_sentiment()
    
    # 組合 Discord 訊息 (Markdown 格式)
    report = f"""
>>> ## {color_emoji} 【03668.HK 兗煤監控報告】
📅 日期: {datetime.now().strftime('%Y-%m-%d')}

**📊 技術面分析**
• 收盤價: `${last_close:.2f}`
• MA趨勢: `MA5({last_ma5:.2f})` vs `MA20({last_ma20:.2f})`
• MACD動能: {'🔼 增強' if last_hist > 0 else '🔽 減弱'}

**🎯 系統建議**
{signal}

**⛏️ 外部環境 (煤價)**
{coal_sentiment_str}
*(註: 使用澳洲母公司 YAL.AX 作為今日開盤前導指標)*
    """
    return report

if __name__ == "__main__":
    result = analyze_stock()
    send_discord_message(result)
