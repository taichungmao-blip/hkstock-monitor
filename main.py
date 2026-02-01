import yfinance as yf
import pandas as pd
import requests
import os
import matplotlib.pyplot as plt
from datetime import datetime
import json  # 1. 確保在程式碼最上方加入了 import json

# --- 設定區 ---
STOCK_CODE = "3668.HK" 
PROXY_COAL_STOCK = "YAL.AX"  # 確認為 Yancoal 澳股
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CHART_FILENAME = "trend_6mo_comparison.png"
PERIOD = "6mo"  # 已改回 6 個月

def send_discord_message(message, file_path=None):
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
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                # 修改這裡：改用 json.dumps 而不是 pd.io.json.dumps
                requests.post(
                    DISCORD_WEBHOOK_URL, 
                    data={"payload_json": json.dumps(payload)}, 
                    files={"file": f}
                )
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"發送錯誤: {e}")

def generate_6mo_chart(df_hk, df_yal):
    """ 生成 6 個月走勢比較圖 """
    plt.figure(figsize=(12, 6))
    
    # 歸一化處理 (Normalization): 以 6 個月前為基點 100
    hk_norm = (df_hk['Close'] / df_hk['Close'].dropna().iloc[0]) * 100
    yal_norm = (df_yal['Close'] / df_yal['Close'].dropna().iloc[0]) * 100

    plt.plot(hk_norm.index, hk_norm, label=f"{STOCK_CODE} (HK)", color='#1f77b4', linewidth=2)
    plt.plot(yal_norm.index, yal_norm, label=f"{PROXY_COAL_STOCK} (AU)", color='#ff7f0e', linewidth=2)

    plt.title(f"Price Trend Comparison - Last 6 Months", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Performance (%) - Base 100")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(CHART_FILENAME)
    plt.close()

def analyze_and_report():
    print(f"正在分析 {STOCK_CODE} (6個月數據)...")
    
    try:
        df_hk = yf.download(STOCK_CODE, period=PERIOD, progress=False)
        df_yal = yf.download(PROXY_COAL_STOCK, period=PERIOD, progress=False)
    except Exception as e:
        return f"⚠️ 數據下載失敗: {e}", None
    
    if df_hk.empty or df_yal.empty:
        return "⚠️ 無法獲取數據", None

    # 清理資料欄位
    if isinstance(df_hk.columns, pd.MultiIndex):
        df_hk.columns = df_hk.columns.get_level_values(0)
    if isinstance(df_yal.columns, pd.MultiIndex):
        df_yal.columns = df_yal.columns.get_level_values(0)

    # 繪圖
    generate_6mo_chart(df_hk, df_yal)

    # 計算當前指標 (基於最新一天)
    last_close = float(df_hk['Close'].iloc[-1])
    prev_close = float(df_hk['Close'].iloc[-2])
    change_pct = ((last_close - prev_close) / prev_close) * 100
    
    # 計算均線
    ma5 = df_hk['Close'].rolling(5).mean().iloc[-1]
    ma20 = df_hk['Close'].rolling(20).mean().iloc[-1]
    
    signal = "🚀 **多頭**" if ma5 > ma20 else "⚠️ **空頭/整理**"

    report = f"""
>>> ## 📊 【{STOCK_CODE} 6個月監控報告】
📅 日期: {datetime.now().strftime('%Y-%m-%d')}

**行情摘要**
• 現價: `${last_close:.2f}` ({change_pct:+.2f}%)
• 趨勢: `MA5 {ma5:.2f}` {' > ' if ma5 > ma20 else ' < '} `MA20 {ma20:.2f}`
• 訊號: {signal}

**半年累計漲跌**
• {STOCK_CODE}: `{((last_close/df_hk['Close'].dropna().iloc[0])-1)*100:+.2f}%`
• {PROXY_COAL_STOCK}: `{((float(df_yal['Close'].iloc[-1])/df_yal['Close'].dropna().iloc[0])-1)*100:+.2f}%`
    """
    return report, CHART_FILENAME

if __name__ == "__main__":
    msg, path = analyze_and_report()
    send_discord_message(msg, path)
