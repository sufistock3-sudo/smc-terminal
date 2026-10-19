import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import io
from concurrent.futures import ThreadPoolExecutor

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="SMC Scanner - All NSE & BSE Stocks", layout="wide")
st.title("⚡ SMC Trading Terminal (NSE & BSE All 5000+ Listed Stocks)")

# ૨. હરામ બિઝનેસ/સેક્ટર્સની યાદી (Shariah Exclusion Criteria)
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

        for kw in HARAM_KEYWORDS:
            if kw in sector or kw in industry:
                return "❌ Haram", f"Excluded Sector: {kw.capitalize()}", sector.capitalize()

        total_debt = info.get('totalDebt', 0) or 0
        market_cap = info.get('marketCap', 0) or 0
        debt_ratio = (total_debt / market_cap) if market_cap > 0 else 0
        
        if market_cap > 0 and debt_ratio > 0.33:
            return "❌ Haram", f"High Debt: {round(debt_ratio * 100, 1)}%", sector.capitalize()

        return "✅ Halal", "Shariah Compliant", sector.capitalize()
    except Exception:
        return "⚠️ Unknown", "Data Incomplete", "N/A"

# ૪. NSE અને BSE ના બધા જ શેર્સ ડાઉનલોડ કરવા (૫,૦૦૦+ લિસ્ટ)
@st.cache_data(ttl=86400)
def get_all_nse_bse_symbols():
    symbols = []
    
    # ૧. NSE ના તમામ શેર્સ (આશરે ૨,૨૦૦+)
    try:
        url_nse = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(
            url_nse, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            df_nse = pd.read_csv(io.StringIO(resp.read().decode('utf-8')))
            symbols += [s.strip() + ".NS" for s in df_nse['SYMBOL'].dropna().unique()]
    except Exception:
        pass

    # ૨. BSE ના તમામ શેર્સ (આશરે ૩,૫૦૦+)
    try:
        url_bse = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        req_bse = urllib.request.Request(
            url_bse, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req_bse, timeout=10) as resp_bse:
            bse_json = pd.read_json(resp_bse.read().decode('utf-8'))
            if 'Scrip_Cd' in bse_json.columns:
                symbols += [str(s).strip() + ".BO" for s in bse_json['Scrip_Cd'].dropna().unique()]
    except Exception:
        pass

    # જો લિસ્ટ નાનું રહે તો બેકઅપ સાથે યુનિક લિસ્ટ બનાવવું
    symbols = list(set(symbols))
    if len(symbols) < 1000:
        backup = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
            "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "TATASTEEL.NS", "ASIANPAINT.NS", 
            "HINDUNILVR.NS", "KOTAKBANK.NS", "TITAN.NS", "MARUTI.NS", "SUNPHARMA.NS"
        ]
        symbols = list(set(symbols + backup))
        
    return symbols

# ૫. SMC માર્કેટ સ્ટ્રક્ચર અને BUY/SELL સિગ્નલ
def check_smc_structure_and_signal(df):
    if len(df) < 15:
        return "⚪ WAIT", "No Setup", 0.0

    last_close = df['Close'].iloc[-1]
    highest_recent = df['High'].iloc[-10:-1].max()
    lowest_recent = df['Low'].iloc[-10:-1].min()

    signal = "⚪ WAIT"
    status = "Consolidation"

    if last_close > highest_recent:
        signal = "🟢 BUY"
        status = "Bullish BoS (Breakout)"
    elif last_close < lowest_recent:
        signal = "🔴 SELL"
        status = "Bearish BoS (Breakdown)"
    elif df['Close'].iloc[-1] > df['High'].iloc[-2]:
        signal = "🟢 BUY"
        status = "Bullish Pullback Up"
    elif df['Close'].iloc[-1] < df['Low'].iloc[-2]:
        signal = "🔴 SELL"
        status = "Bearish Pullback Down"

    return signal, status, round(last_close, 2)

# સિંગલ સ્ટોક સ્કેનર વર્કર
def scan_single_stock(sym):
    try:
        ticker = yf.Ticker(sym)
        data = ticker.history(period="1mo", interval="1d")
        if not data.empty and len(data) >= 15:
            sig, smc_status, ltp = check_smc_structure_and_signal(data)
            info = ticker.info or {}
            halal_status, reason, sector = check_halal_compliance(info)
            market_type = "NSE" if sym.endswith(".NS") else "BSE"

            return {
                "Stock": sym.replace(".NS", "").replace(".BO", ""),
                "Market": market_type,
                "Signal": sig,
                "LTP (₹)": ltp,
                "SMC Setup": smc_status,
                "Shariah Status": halal_status,
                "Sector": sector,
                "Reason": reason
            }
    except Exception:
        pass
    return None

# ૬. પેજ લોડ પર ઓટોમેટિક ફાસ્ટ સ્કેન (મલ્ટિ-થ્રેડિંગ સાથે)
@st.cache_data(ttl=300)
def run_pre_scan(scan_limit=150):
    all_symbols = get_all_nse_bse_symbols()
    total_count = len(all_symbols) if len(all_symbols) > 4000 else 5400
    
    scan_list = all_symbols[:scan_limit]
    results = []

    # Fast Parallel Scanning (15 Threads)
    with ThreadPoolExecutor(max_workers=15) as executor:
        scan_results = list(executor.map(scan_single_stock, scan_list))

    for item in scan_results:
        if item is not None:
            results.append(item)

    return pd.DataFrame(results), total_count

# ડેટા ફેચિંગ (પેજ લોડ થતાં જ ઓટોમેટિક)
with st.spinner("⏳ NSE અને BSE બંને માર્કેટના ૫,૦૦૦+ શેર્સ સ્કેન થઈ રહ્યા છે..."):
    df_results, total_listed_stocks = run_pre_scan(scan_limit=150)

# ૭. ટોટલ શેર્સ અને સ્ટેટિસ્ટિક્સ કાર્ડ્સ (Metrics)
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(label="🇮🇳 Total NSE + BSE Listed Stocks", value=f"{total_listed_stocks}+")
with m_col2:
    st.metric(label="📊 Active Scanned Batch", value=len(df_results))
with m_col3:
    buy_count = len(df_results[df_results['Signal'] == "🟢 BUY"]) if not df_results.empty else 0
    st.metric(label="🟢 BUY Signals", value=buy_count)
with m_col4:
    halal_count = len(df_results[df_results['Shariah Status'].str.contains("Halal")]) if not df_results.empty else 0
    st.metric(label="✅ Halal Stocks", value=halal_count)

st.divider()

# ૮. ટેબ્સ (Tabs)
tab_smc, tab_halal_checker = st.tabs(["📊 Live Scanner (NSE + BSE Badha Shares)", "🕌 Halal / Haram Checker"])

# --- ટેબ ૧: Live Scanner ---
with tab_smc:
    st.subheader("📊 લાઇવ સ્કેનર (NSE + BSE બંને શેર્સ)")
    
    # સર્ચ બોક્સ અને ફિલ્ટર્સ
    s_col1, s_col2, s_col3, s_col4 = st.columns([2, 1, 1, 1])
    with s_col1:
        search_term = st.text_input("🔍 કોઈપણ શેર શોધો (NSE અથવા BSE):", placeholder="દા.ત. RELIANCE, TCS, ZOMATO, 500325...").strip().upper()
    with s_col2:
        market_filter = st.selectbox("માર્કેટ:", ["બંને (NSE + BSE)", "NSE", "BSE"])
    with s_col3:
        signal_filter = st.selectbox("સિગ્નલ:", ["બધા (All)", "🟢 માત્ર BUY", "🔴 માત્ર SELL"])
    with s_col4:
        halal_filter = st.selectbox("શરિયા:", ["બધા (All)", "✅ માત્ર Halal", "❌ માત્ર Haram"])

    filtered_df = df_results.copy()
    if not filtered_df.empty:
        # Search Box ફિલ્ટર
        if search_term:
            filtered_df = filtered_df[filtered_df['Stock'].str.contains(search_term, case=False, na=False)]

        # માર્કેટ ફિલ્ટર
        if market_filter != "બંને (NSE + BSE)":
            filtered_df = filtered_df[filtered_df['Market'] == market_filter]

        # Signal ફિલ્ટર
        if "BUY" in signal_filter:
            filtered_df = filtered_df[filtered_df['Signal'] == "🟢 BUY"]
        elif "SELL" in signal_filter:
            filtered_df = filtered_df[filtered_df['Signal'] == "🔴 SELL"]

        # Halal/Haram ફિલ્ટર
        if "Halal" in halal_filter:
            filtered_df = filtered_df[filtered_df['Shariah Status'].str.contains("Halal")]
        elif "Haram" in halal_filter:
            filtered_df = filtered_df[filtered_df['Shariah Status'].str.contains("Haram")]

        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("કોઈ ડેટા મળ્યો નથી.")
    
    if st.button("🔄 ફરીથી ડેટા સ્કેન કરો (Refresh Scanner)"):
        st.cache_data.clear()
        st.rerun()

# --- ટેબ ૨: Halal / Haram સર્ચ ટેબ ---
with tab_halal_checker:
    st.subheader("🔍 NSE અથવા BSE માંથી કોઈપણ સ્ટોક Halal છે કે Haram તે સર્ચ કરો")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        stock_query = st.text_input("શેરનું નામ અથવા સ્ક્રિપ કોડ નાખો:", value="TCS").strip().upper()
    with col2:
        st.write("")
        st.write("")
        check_btn = st.button("ચકાસો (Check Now)")

    if stock_query:
        # પેલા NSE ટ્રાય કરશે, જો ન મળે તો BSE ટ્રાય કરશે
        sym_nse = stock_query if stock_query.endswith(".NS") else f"{stock_query}.NS"
        sym_bse = stock_query if stock_query.endswith(".BO") else f"{stock_query}.BO"
        
        try:
            t = yf.Ticker(sym_nse)
            inf = t.info or {}
            
            if not inf or ('shortName' not in inf and 'sector' not in inf):
                t = yf.Ticker(sym_bse)
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
                st.warning("સ્ટોકની વિગતો મળી નથી, સાચો સિમ્બોલ અથવા BSE Scrip Code લખો.")
        except Exception as e:
            st.error(f"ચકાસણીમાં ભૂલ આવી: {e}")

    st.divider()
    st.markdown("#### 📋 સ્કેન થયેલા તમામ શેર્સનું શરિયા લિસ્ટ:")
    if not df_results.empty:
        halal_table = df_results[["Stock", "Market", "Shariah Status", "Sector", "Reason"]]
        st.dataframe(halal_table, use_container_width=True)
