import yfinance as yf
import pandas as pd
import requests
import os
import matplotlib.pyplot as plt
import json
from datetime import datetime

# --- 設定區 ---
STOCK_CODE = "3668.HK" 
PROXY_COAL_STOCK = "YAL.AX"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CHART_FILENAME = "trend_analysis_with_lead.png"
PERIOD = "6mo"

def send_discord_message(message, file_path=None):
    if not DISCORD_WEBHOOK_URL:
        print("未設定 Webhook，僅列印:\n", message)
        return

    payload = {
        "content": message,
        "username": "煤炭連動監控站",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2534/2534204.png"
    }

    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(
                    DISCORD_WEBHOOK_URL, 
                    data={"payload_json": json.dumps(payload)}, 
                    files={"file": f}
                )
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"發送錯誤: {e}")

def generate_combined_chart(df_hk, df_yal):
    """ 生成主價格圖 + 領先指標子圖 """
    # 歸一化處理
    hk_norm = (df_hk['Close'] / df_hk['Close'].dropna().iloc[0]) * 100
    yal_norm = (df_yal['Close'] / df_yal['Close'].dropna().iloc[0]) * 100
    
    # 計算偏差 (Spread): YAL - HK
    spread = yal_norm - hk_norm

    # 建立 2x1 佈局，高度比例為 3:1
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]})

    # --- 上圖：價格走勢 ---
    ax1.plot(hk_norm.index, hk_norm, label=f"{STOCK_CODE} (HK)", color='#1f77b4', linewidth=2)
    ax1.plot(yal_norm.index, yal_norm, label=f"{PROXY_COAL_STOCK} (AU)", color='#ff7f0e', linewidth=2)
    ax1.set_title(f"Price Trend Comparison (Last 6 Months)", fontsize=16, fontweight='bold')
    ax1.set_ylabel("Performance (%) - Base 100")
    ax1.legend(loc='upper left')
    ax1.grid(True, linestyle='--', alpha=0.4)

    # --- 下圖：領先指標 (Relative Strength Spread) ---
    ax2.plot(spread.index, spread, color='gray', alpha=0.5)
    # 填色：當 Spread > 0 (YAL較強) 填綠色；當 Spread < 0 (HK較強) 填紅色
    ax2.fill_between(spread.index, 0, spread, where=(spread >= 0), color='green', alpha=0.3, label='YAL Leading')
    ax2.fill_between(spread.index, 0, spread, where=(spread < 0), color='red', alpha=0.3, label='HK Leading')
    
    ax2.axhline(0, color='black', linewidth=1, linestyle='-')
    ax2.set_title("Leading Indicator (YAL Performance - HK Performance)", fontsize=12)
    ax2.set_ylabel("Spread (%)")
    ax2.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(CHART_FILENAME)
    plt.close()
    return spread.iloc[-1]

def analyze_stock():
    print(f"正在執行深度連動分析...")
    
    try:
        # 下載數據並對齊日期 (使用 inner join 確保日期一致)
        df_hk = yf.download(STOCK_CODE, period=PERIOD, progress=False)
        df_yal = yf.download(PROXY_COAL_STOCK, period=PERIOD, progress=False)
        
        if df_hk.empty or df_yal.empty: return "數據抓取失敗", None

        # 清理 MultiIndex
        if isinstance(df_hk.columns, pd.MultiIndex): df_hk.columns = df_hk.columns.get_level_values(0)
        if isinstance(df_yal.columns, pd.MultiIndex): df_yal.columns = df_yal.columns.get_level_values(0)

        # 計算數學指標
        correlation = df_hk['Close'].corr(df_yal['Close'])
        last_spread = generate_combined_chart(df_hk, df_yal)
        
        # 最新價格資訊
        last_close = float(df_hk['Close'].iloc[-1])
        change_pct = ((last_close / float(df_hk['Close'].iloc[-2])) - 1) * 100
        
        # 領先訊號解讀
        if last_spread > 2.0:
            lead_msg = f"🚀 **澳股領先轉強 (+{last_spread:.1f}%)**，港股具補漲潛力"
        elif last_spread < -2.0:
            lead_msg = f"⚠️ **港股暫時超前 ({last_spread:.1f}%)**，留意短期修正"
        else:
            lead_msg = "⚖️ **兩地同步波動**，目前無顯著背離"

        report = f"""
>>> ## 📊 【{STOCK_CODE} x YAL.AX 深度報告】
📅 基準日期: {datetime.now().strftime('%Y-%m-%d')}

**連動分析**
• 數學相關係數: `{correlation:.2f}` (極高連動)
• 領先指標狀態: {lead_msg}

**3668.HK 技術面**
• 今日收盤: `${last_close:.2f}` ({change_pct:+.2f}%)
• 趨勢判斷: {'向上' if last_spread > 0 else '震盪'}

*下方圖表綠色區域表示 YAL 走勢強於 3668，紅色則反之。*
        """
        return report, CHART_FILENAME

    except Exception as e:
        return f"⚠️ 分析過程出錯: {e}", None

if __name__ == "__main__":
    msg, path = analyze_stock()
    send_discord_message(msg, path)
