import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import io

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="SMC Scanner & Halal Screener", layout="wide")
st.title("⚡ SMC Trading Terminal & Shariah Screener")

# ૨. હરામ બિઝનેસ/સેક્ટર્સની યાદી
HARAM_KEYWORDS = [
    "bank", "finance", "housing finance", "insurance", "capital",
    "brewery", "distilleries", "liquor", "spirits", "alcohol", "wine",
    "tobacco", "cigarettes",
    "casino", "gaming", "entertainment",
    "pork", "hotel", "resort"
]

# ૩. સ્ટોક હલાલ છે કે હરામ તે ચકાસવું
def check_halal_compliance(info):
    try:
        sector = str(info.get('sector', '')).lower()
        industry = str(info.get('industry', '')).lower()

        # સેક્ટર આધારિત સ્ક્રીનિંગ
        for kw in HARAM_KEYWORDS:
            if kw in sector or kw in industry:
                return "❌ Haram", f"Excluded Sector: {kw.capitalize()}", sector.capitalize()

        # ડેટ રેશિયો સ્ક્રીનિંગ (Debt < 33% of Market Cap)
        total_debt = info.get('totalDebt', 0) or 0
        market_cap = info.get('marketCap', 0) or 0
        debt_ratio = (total_debt / market_cap) if market_cap > 0 else 0
        
        if market_cap > 0 and debt_ratio > 0.33:
            return "❌ Haram", f"High Debt Ratio: {round(debt_ratio * 100, 1)}% (Limit: 33%)", sector.capitalize()

        return "✅ Halal", "Shariah Compliant (Clean Business & Low Debt)", sector.capitalize()
    except Exception:
        return "⚠️ Unknown", "Data Incomplete", "N/A"

# ૪. NSE સિમ્બોલ્સ ડાઉનલોડ કરવા
@st.cache_data(ttl=86400)
def get_all_nse_symbols():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            csv_data = response.read()
        df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')))
        symbols = [s + ".NS" for s in df['SYMBOL'].dropna().unique()]
        return symbols
    except Exception:
        return [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", 
            "ICICIBANK.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", 
            "TATASTEEL.NS", "ASIANPAINT.NS", "HINDUNILVR.NS", "KOTAKBANK.NS", "TITAN.NS"
        ]

# ૫. SMC માર્કેટ સ્ટ્રક્ચર ચેક
def check_smc_structure(df):
    if len(df) < 15:
        return "No Setup", 0.0

    last_close = df['Close'].iloc[-1]
    highest_recent = df['High'].iloc[-10:-1].max()
    lowest_recent = df['Low'].iloc[-10:-1].min()

    status = "Consolidation"
    if last_close > highest_recent:
        status = "Bullish BoS / Breakout"
    elif last_close < lowest_recent:
        status = "Bearish BoS / Breakdown"
    elif df['Close'].iloc[-1] > df['High'].iloc[-2]:
        status = "Bullish Pullback"
    elif df['Close'].iloc[-1] < df['Low'].iloc[-2]:
        status = "Bearish Pullback"

    return status, round(last_close, 2)

# ૬. પેજ લોડ થતાં જ ઓટોમેટિક સ્કેન
@st.cache_data(ttl=300)
def run_pre_scan():
    symbols = get_all_nse_symbols()
    results = []
    
    scan_list = symbols[:40]

    for sym in scan_list:
        try:
            ticker = yf.Ticker(sym)
            data = ticker.history(period="1mo", interval="1d")
            
            if not data.empty:
                smc_status, ltp = check_smc_structure(data)
                info = ticker.info or {}
                status, reason, sector = check_halal_compliance(info)

                results.append({
                    "Stock": sym.replace(".NS", ""),
                    "LTP (₹)": ltp,
                    "SMC Structure": smc_status,
                    "Shariah Status": status,
                    "Sector": sector,
                    "Reason": reason
                })
        except Exception:
            continue

    return pd.DataFrame(results)

# ડેટા ફેચિંગ
with st.spinner("⏳ માર્કેટ સ્કેન અને શરિયા ડેટા પહેલેથી લોડ થઈ રહ્યો છે..."):
    df_results = run_pre_scan()

# ૭. બે અલગ ટેબ્સ (SMC સ્કેનર અને Halal ચેકર)
tab_smc, tab_halal_checker = st.tabs(["📊 SMC Market Scanner", "🕌 Halal / Haram Checker"])

# --- ટેબ ૧: SMC સ્કેનર ---
with tab_smc:
    st.subheader("📊 ઓટોમેટિક સ્કેન પરિણામો")
    if not df_results.empty:
        st.dataframe(df_results, use_container_width=True)
    else:
        st.info("કોઈ ડેટા મળ્યો નથી.")
    
    if st.button("🔄 ફરીથી ડેટા સ્કેન કરો (Refresh Scanner)"):
        st.cache_data.clear()
        st.rerun()

# --- ટેબ ૨: સ્પેશિયલ Halal / Haram ચેકર ટેબ ---
with tab_halal_checker:
    st.subheader("🔍 કોઈ પણ સ્ટોક Halal છે કે Haram તે સર્ચ કરો")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        stock_query = st.text_input("NSE શેરનું નામ નાખો (દા.ત. TATASTEEL, INFY, HDFCBANK, ITC):", value="TCS").strip().upper()
    with col2:
        st.write("")
        st.write("")
        check_btn = st.button("ચકાસો (Check)")

    if stock_query:
        sym_to_check = stock_query if stock_query.endswith(".NS") else f"{stock_query}.NS"
        try:
            t = yf.Ticker(sym_to_check)
            inf = t.info or {}
            
            if 'shortName' in inf or 'sector' in inf:
                stat, reas, sec = check_halal_compliance(inf)
                stock_title = inf.get('shortName', stock_query)
                curr_price = inf.get('currentPrice', inf.get('regularMarketPrice', 'N/A'))
                
                st.divider()
                st.write(f"### સ્ટોક: **{stock_title}** ({stock_query})")
                st.write(f"**LTP:** ₹{curr_price} | **Sector:** {sec}")

                if "Halal" in stat:
                    st.success(f"### સ્ટેટસ: {stat}\n**વિગત:** {reas}")
                else:
                    st.error(f"### સ્ટેટસ: {stat}\n**વિગત:** {reas}")
            else:
                st.warning("સ્ટોકની વિગતો મળી નથી, સાચો સિમ્બોલ નાખો.")
        except Exception as e:
            st.error(f"ચકાસણીમાં ભૂલ આવી: {e}")

    st.divider()
    st.markdown("#### 📋 સ્કેન થયેલા શેર્સનું શરિયા લિસ્ટ:")
    if not df_results.empty:
        halal_table = df_results[["Stock", "Shariah Status", "Sector", "Reason"]]
        st.dataframe(halal_table, use_container_width=True)
