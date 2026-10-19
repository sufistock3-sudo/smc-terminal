import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import io

st.set_page_config(page_title="SMC Scanner - All 2000+ NSE Stocks", layout="wide")
st.title("🏹 SMC Smart Money Trading Terminal (NSE - Badha Shares)")

@st.cache_data
def get_all_nse_symbols():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
        )
        html = urllib.request.urlopen(req).read()
        df_nse = pd.read_csv(io.BytesIO(html))
        syms = df_nse['SYMBOL'].dropna().unique().tolist()
        return [s.strip() for s in syms if s.strip()]
    except Exception:
        # Fallback list jo network na chalse to Nifty 500
        url_alt = "https://raw.githubusercontent.com/anirbm/ind_nifty500list/master/ind_nifty500list.csv"
        try:
            df_alt = pd.read_csv(url_alt)
            return df_alt['Symbol'].tolist()
        except Exception:
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "TATAMOTORS", "SBIN"]

all_symbols = get_all_nse_symbols()

# Sidebar Controls
st.sidebar.header("⚙️ Terminal Settings")
st.sidebar.success(f"📊 **Total Available Stocks:** {len(all_symbols)}")

# Timeframe Options 1m thi 1mo
timeframe_options = {
    "1 Minute (1m)": ("1m", "1d"),
    "2 Minutes (2m)": ("2m", "1d"),
    "5 Minutes (5m)": ("5m", "5d"),
    "15 Minutes (15m)": ("15m", "5d"),
    "30 Minutes (30m)": ("30m", "1mo"),
    "60 Minutes / 1 Hour (60m)": ("60m", "1mo"),
    "1 Day / Daily (1d)": ("1d", "1y"),
    "1 Week / Weekly (1wk)": ("1wk", "2y"),
    "1 Month / Monthly (1mo)": ("1mo", "5y")
}

selected_tf_label = st.sidebar.selectbox("Timeframe (1m thi 1mo):", list(timeframe_options.keys()), index=3)
timeframe, period = timeframe_options[selected_tf_label]

scan_mode = st.sidebar.radio("Scan Mode:", ["Batch Scan (Slider)", "Badha j Shares (Full 2000+)"])

if scan_mode == "Batch Scan (Slider)":
    batch_size = st.sidebar.slider("Ketla shares scan karva chhe?", min_value=20, max_value=len(all_symbols), value=100, step=20)
    symbols_to_scan = all_symbols[:batch_size]
else:
    symbols_to_scan = all_symbols

def check_smc(df):
    if len(df) < 20:
        return "NEUTRAL", "-", df['Close'].iloc[-1]
    
    c_close = df['Close'].iloc[-1]
    swing_high = df['High'].iloc[-20:-2].max()
    swing_low = df['Low'].iloc[-20:-2].min()
    
    if c_close > swing_high:
        return "BUY", "BoS Breakout & Demand Zone", c_close
    elif c_close < swing_low:
        return "SELL", "BoS Breakdown & Supply Zone", c_close
    else:
        return "WAIT", "Pullback / Range", c_close

st.write(f"### Timeframe: **{selected_tf_label}** | Scanning **{len(symbols_to_scan)}** Stocks...")

results = []
progress_bar = st.progress(0)
status_text = st.empty()

for idx, sym in enumerate(symbols_to_scan):
    ticker = f"{sym}.NS"
    status_text.text(f"Scanning ({idx + 1}/{len(symbols_to_scan)}): {sym}")
    try:
        data = yf.download(ticker, period=period, interval=timeframe, progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [c[0] for c in data.columns]
            sig, mdl, price = check_smc(data)
            results.append({
                "Stock": sym,
                "Price (₹)": round(float(price), 2),
                "Signal": sig,
                "Setup": mdl
            })
    except Exception:
        pass
    progress_bar.progress((idx + 1) / len(symbols_to_scan))

status_text.text("✅ Scanning Complete!")

df_res = pd.DataFrame(results)

filter_option = st.selectbox("Filter:", ["Badha Shares", "Fakt BUY / SELL Signals"])

if filter_option == "Fakt BUY / SELL Signals":
    display_df = df_res[df_res['Signal'].isin(["BUY", "SELL"])]
else:
    display_df = df_res

def color_rows(val):
    if val == "BUY":
        return "background-color: #2e7d32; color: white; font-weight: bold;"
    elif val == "SELL":
        return "background-color: #c62828; color: white; font-weight: bold;"
    return "color: gray;"

if not display_df.empty:
    st.dataframe(display_df.style.map(color_rows, subset=['Signal']), use_container_width=True)
else:
    st.info("Koi signal malyu nathi.")