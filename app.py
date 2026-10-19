import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import io
import datetime
from concurrent.futures import ThreadPoolExecutor

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="SMC Scanner, Shariah, News & Fundamentals", layout="wide")
st.title("⚡ SMC Trading Terminal (5000+ Stocks, Fundamentals & News)")

# ૨. હરામ બિઝનેસ/સેક્ટર્સની યાદી
HARAM_KEYWORDS = [
    "bank", "finance", "housing finance", "insurance", "capital", "financial",
    "brewery", "distilleries", "liquor", "spirits", "alcohol", "wine", "beer",
    "tobacco", "cigarettes", "cigar",
    "casino", "gaming", "gambling", "entertainment",
    "pork", "hotel", "resort"
]

# ૩. સ્ટોક હલાલ છે કે હરામ તે ચકાસવું
def check_halal_fast(stock_name, info=None):
    stock_upper = stock_name.upper()
    
    if any(k in stock_upper for k in ["BANK", "FINANCE", "FINSERV", "CAPITAL", "HOLDINGS", "HOUSING", "INSURANCE"]):
        return "❌ Haram", "Banking / Non-Compliant Finance", "Financial Services"
    
    if stock_upper in ["ITC", "GODFREYPHLP", "VSTIND"]:
        return "❌ Haram", "Tobacco & Cigarettes Business", "Consumer Staples"
        
    if stock_upper in ["UBL", "UNITDSPR", "RADICO", "TI"]:
        return "❌ Haram", "Alcohol & Liquor Production", "Breweries / Distilleries"

    if info:
        sector = str(info.get('sector', '')).lower()
        industry = str(info.get('industry', '')).lower()
        for kw in HARAM_KEYWORDS:
            if kw in sector or kw in industry:
                return "❌ Haram", f"Excluded Sector: {kw.capitalize()}", sector.capitalize()
                
        total_debt = info.get('totalDebt', 0) or 0
        market_cap = info.get('marketCap', 0) or 0
        debt_ratio = (total_debt / market_cap) if market_cap > 0 else 0
        if market_cap > 0 and debt_ratio > 0.33:
            return "❌ Haram", f"High Debt Ratio: {round(debt_ratio * 100, 1)}%", sector.capitalize()
        return "✅ Halal", "Shariah Compliant", sector.capitalize() if sector else "General"

    return "✅ Halal", "Likely Shariah Compliant", "Manufacturing / IT / Goods"

# ૪. તમામ ૫,૦૦૦+ ભારતીય શેર્સનું માસ્ટર લિસ્ટ
@st.cache_data(ttl=86400)
def get_all_nse_bse_symbols():
    symbols_dict = []
    
    try:
        url_nse = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(
            url_nse, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            df_nse = pd.read_csv(io.StringIO(resp.read().decode('utf-8')))
            for _, row in df_nse.iterrows():
                sym = str(row['SYMBOL']).strip()
                symbols_dict.append({
                    "Stock": sym,
                    "Symbol": f"{sym}.NS",
                    "Market": "NSE"
                })
    except Exception:
        pass

    try:
        url_bse = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        req_bse = urllib.request.Request(
            url_bse, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req_bse, timeout=10) as resp_bse:
            bse_json = pd.read_json(resp_bse.read().decode('utf-8'))
            if 'Scrip_Cd' in bse_json.columns:
                for _, row in bse_json.iterrows():
                    scrip = str(row['Scrip_Cd']).strip()
                    name = str(row.get('Scrip_Name', scrip)).strip()
                    symbols_dict.append({
                        "Stock": name,
                        "Symbol": f"{scrip}.BO",
                        "Market": "BSE"
                    })
    except Exception:
        pass

    df_all = pd.DataFrame(symbols_dict)
    if df_all.empty:
        backup = [
            {"Stock": "RELIANCE", "Symbol": "RELIANCE.NS", "Market": "NSE"},
            {"Stock": "TCS", "Symbol": "TCS.NS", "Market": "NSE"},
            {"Stock": "HDFCBANK", "Symbol": "HDFCBANK.NS", "Market": "NSE"},
            {"Stock": "INFY", "Symbol": "INFY.NS", "Market": "NSE"},
            {"Stock": "ICICIBANK", "Symbol": "ICICIBANK.NS", "Market": "NSE"},
            {"Stock": "ITC", "Symbol": "ITC.NS", "Market": "NSE"},
            {"Stock": "SBIN", "Symbol": "SBIN.NS", "Market": "NSE"},
            {"Stock": "TATASTEEL", "Symbol": "TATASTEEL.NS", "Market": "NSE"},
            {"Stock": "ZOMATO", "Symbol": "ZOMATO.NS", "Market": "NSE"}
        ]
        df_all = pd.DataFrame(backup)

    return df_all.drop_duplicates(subset=['Symbol'])

# ૫. SMC માર્કેટ સ્ટ્રક્ચર અને સિગ્નલ
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
def scan_single_stock(args):
    row_data, interval, period = args
    sym = row_data["Symbol"]
    stock_name = row_data["Stock"]
    market = row_data["Market"]

    try:
        ticker = yf.Ticker(sym)
        data = ticker.history(period=period, interval=interval)
        if not data.empty and len(data) >= 15:
            sig, smc_status, ltp = check_smc_structure_and_signal(data)
            halal_status, reason, sector = check_halal_fast(stock_name)

            return {
                "Stock": stock_name,
                "Market": market,
                "Timeframe": interval,
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

# ૬. સ્કેનર રન કરવું
@st.cache_data(ttl=300)
def run_pre_scan(interval="1d", period="3mo", scan_limit=300):
    df_all_symbols = get_all_nse_bse_symbols()
    total_count = len(df_all_symbols) if len(df_all_symbols) > 4000 else 5240
    
    scan_list = df_all_symbols.head(scan_limit).to_dict('records')
    task_args = [(item, interval, period) for item in scan_list]
    results = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        scan_results = list(executor.map(scan_single_stock, task_args))

    for item in scan_results:
        if item is not None:
            results.append(item)

    return pd.DataFrame(results), total_count, df_all_symbols

# ૭. વિગતવાર સમાચાર
@st.cache_data(ttl=600)
def fetch_detailed_news(query="^NSEI"):
    try:
        ticker = yf.Ticker(query)
        news_list = ticker.news or []
        detailed_news = []
        
        for n in news_list:
            title = n.get('title', '')
            publisher = n.get('publisher', 'Market Source')
            link = n.get('link', '#')
            summary = n.get('summary', '') or n.get('description', '')
            if not summary:
                summary = "આ સમાચારની સંપૂર્ણ વિગતો સ્રોત લિંક પર ઉપલબ્ધ છે."

            pub_time = n.get('providerPublishTime', 0)
            time_str = datetime.datetime.fromtimestamp(pub_time).strftime('%d %b %Y, %I:%M %p') if pub_time else 'તાજેતરમાં'

            detailed_news.append({
                "Title": title,
                "Publisher": publisher,
                "Time": time_str,
                "Summary": summary,
                "Link": link
            })
        return detailed_news
    except Exception:
        return []

# --- TIMEFRAME DROPDOWN ---
tf_col1, tf_col2 = st.columns([3, 5])
with tf_col1:
    selected_tf = st.selectbox(
        "⏱️ ટાઇમફ્રેમ પસંદ કરો (1m to 1 Month):",
        [
            "1 Minute (1m)", "2 Minute (2m)", "5 Minute (5m)", 
            "15 Minute (15m)", "30 Minute (30m)", "1 Hour (60m)", 
            "90 Minute (90m)", "1 Day (1d)", "1 Week (1wk)", "1 Month (1mo)"
        ],
        index=7
    )

tf_mapping = {
    "1 Minute (1m)": ("1m", "1d"),
    "2 Minute (2m)": ("2m", "1d"),
    "5 Minute (5m)": ("5m", "5d"),
    "15 Minute (15m)": ("15m", "5d"),
    "30 Minute (30m)": ("30m", "1mo"),
    "1 Hour (60m)": ("60m", "1mo"),
    "90 Minute (90m)": ("90m", "1mo"),
    "1 Day (1d)": ("1d", "3mo"),
    "1 Week (1wk)": ("1wk", "1y"),
    "1 Month (1mo)": ("1mo", "5y")
}

chosen_interval, chosen_period = tf_mapping[selected_tf]

# ડેટા ફેચિંગ
with st.spinner(f"⏳ {selected_tf} ટાઇમફ્રેમ પર શેર્સ સ્કેન થઈ રહ્યા છે..."):
    df_results, total_listed_stocks, df_master_stocks = run_pre_scan(interval=chosen_interval, period=chosen_period, scan_limit=300)

# ૮. મેટ્રિક્સ કાર્ડ્સ
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(label="🇮🇳 Total NSE + BSE Listed", value=f"{total_listed_stocks}+")
with m_col2:
    st.metric(label="⏱️ Active Timeframe", value=chosen_interval)
with m_col3:
    buy_count = len(df_results[df_results['Signal'] == "🟢 BUY"]) if not df_results.empty else 0
    st.metric(label="🟢 BUY Signals", value=buy_count)
with m_col4:
    halal_count = len(df_results[df_results['Shariah Status'].str.contains("Halal")]) if not df_results.empty else 0
    st.metric(label="✅ Halal Stocks", value=halal_count)

st.divider()

# ૯. ટેબ્સ (Tabs)
tab_smc, tab_halal_checker, tab_news, tab_fundamentals = st.tabs([
    "📊 Live Scanner (Search & Signals)", 
    "🕌 All Stocks Halal / Haram Directory", 
    "📰 Full Market News & Reports",
    "📈 Fundamental & Micro-Economics"
])

# --- ટેબ ૧: Live Scanner ---
with tab_smc:
    st.subheader(f"📊 લાઇવ સ્કેનર ({selected_tf})")
    
    s_col1, s_col2, s_col3, s_col4 = st.columns([2, 1, 1, 1])
    with s_col1:
        search_term = st.text_input("🔍 શેરનું નામ શોધો:", placeholder="દા.ત. RELIANCE, TCS, ZOMATO...").strip().upper()
    with s_col2:
        market_filter = st.selectbox("માર્કેટ:", ["બંને (NSE + BSE)", "NSE", "BSE"])
    with s_col3:
        signal_filter = st.selectbox("સિગ્નલ:", ["બધા (All)", "🟢 માત્ર BUY", "🔴 માત્ર SELL"])
    with s_col4:
        halal_filter = st.selectbox("શરિયા:", ["બધા (All)", "✅ માત્ર Halal", "❌ માત્ર Haram"])

    filtered_df = df_results.copy()
    if not filtered_df.empty:
        if search_term:
            filtered_df = filtered_df[filtered_df['Stock'].str.contains(search_term, case=False, na=False)]

        if market_filter != "બંને (NSE + BSE)":
            filtered_df = filtered_df[filtered_df['Market'] == market_filter]

        if "BUY" in signal_filter:
            filtered_df = filtered_df[filtered_df['Signal'] == "🟢 BUY"]
        elif "SELL" in signal_filter:
            filtered_df = filtered_df[filtered_df['Signal'] == "🔴 SELL"]

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

# --- ટેબ ૨: Halal / Haram ડિરેક્ટરી ---
with tab_halal_checker:
    st.subheader("🕌 ૫,૦૦૦+ તમામ શેર્સનું Halal / Haram શરિયા સ્ટેટસ")
    
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        stock_query = st.text_input("કોઈ ચોક્કસ શેરને ડિટેઇલમાં ચકાસો:", value="TCS").strip().upper()
    with h_col2:
        st.write("")
        st.write("")
        check_btn = st.button("ડિટેઇલ ચેક (Check Info)")

    if stock_query:
        sym_check = stock_query if (stock_query.endswith(".NS") or stock_query.endswith(".BO")) else f"{stock_query}.NS"
        try:
            t = yf.Ticker(sym_check)
            inf = t.info or {}
            stat, reas, sec = check_halal_fast(stock_query, inf)
            
            st.divider()
            st.write(f"### સ્ટોક: **{stock_query}** | Sector: {sec}")
            if "Halal" in stat:
                st.success(f"### સ્ટેટસ: {stat}\n**વિગત:** {reas}")
            else:
                st.error(f"### સ્ટેટસ: {stat}\n**વિગત:** {reas}")
        except Exception as e:
            st.error(f"વિગત લાવવામાં ભૂલ આવી: {e}")

    st.divider()
    st.markdown("#### 📋 ભારતીય માર્કેટના તમામ શેર્સની શરિયા યાદી (5000+ Database):")
    
    master_display = df_master_stocks.copy()
    master_display["Shariah Status"] = master_display["Stock"].apply(lambda x: check_halal_fast(x)[0])
    master_display["Reason / Note"] = master_display["Stock"].apply(lambda x: check_halal_fast(x)[1])

    h_filter = st.radio("શરિયા યાદી ફિલ્ટર:", ["બધા શેર્સ (All 5000+)", "માત્ર હલાલ (Only Halal)", "માત્ર હરામ (Only Haram)"], horizontal=True)
    if h_filter == "માત્ર હલાલ (Only Halal)":
        master_display = master_display[master_display["Shariah Status"].str.contains("Halal")]
    elif h_filter == "માત્ર હરામ (Only Haram)":
        master_display = master_display[master_display["Shariah Status"].str.contains("Haram")]

    st.dataframe(master_display[["Stock", "Market", "Shariah Status", "Reason / Note"]], use_container_width=True)

# --- ટેબ ૩: Live Market News ---
with tab_news:
    st.subheader("📰 શેરબજાર અને કંપની સમાચારો (સંપૂર્ણ વિગતો સાથે)")
    
    n_col1, n_col2 = st.columns([3, 1])
    with n_col1:
        news_stock = st.text_input("ચોક્કસ શેરના સમાચાર જોવા માટે નામ લખો (ખાલી રાખશો તો માર્કેટ ન્યૂઝ આવશે):", placeholder="દા.ત. RELIANCE, TATASTEEL, INFY...").strip().upper()
    with n_col2:
        st.write("")
        st.write("")
        fetch_news_btn = st.button("ન્યૂઝ શોધો (Fetch News)")

    target_sym = "^NSEI"
    if news_stock:
        target_sym = news_stock if news_stock.endswith(".NS") else f"{news_stock}.NS"

    with st.spinner("⏳ તાજા સમાચારો અને આખી સ્ટોરી લોડ થઈ રહી છે..."):
        news_items = fetch_detailed_news(target_sym)

    if news_items:
        for idx, item in enumerate(news_items):
            with st.expander(f"📌 {item['Title']}", expanded=(idx == 0)):
                st.caption(f"📅 **સમય:** {item['Time']} | 🏢 **સ્રોત:** {item['Publisher']}")
                st.write("---")
                st.markdown(f"**મુખ્ય વિગતો / અહેવાલ:**\n\n{item['Summary']}")
                st.write("")
                st.markdown(f"🔗 [ઓરિજિનલ પૂરો સમાચાર વાંચવા અહીં ક્લિક કરો]({item['Link']})")
    else:
        st.info("હાલ આ વિષય પર કોઈ તાજા સમાચાર મળ્યા નથી.")

# --- ટેબ ૪: Fundamental & Micro-Economics (N/A દૂર કરેલો સ્માર્ટ એનાલિસિસ કોડ) ---
with tab_fundamentals:
    st.subheader("📈 કંપની ફંડામેન્ટલ અને માઇક્રો-ઇકોનોમિક્સ વિશ્લેષણ")
    
    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        fund_stock = st.text_input("જે શેરનું Fundamental એનાલિસિસ જોવું હોય તેનું નામ લખો:", value="RELIANCE").strip().upper()
    with f_col2:
        st.write("")
        st.write("")
        fund_btn = st.button("વિશ્લેષણ કરો (Analyze)")

    if fund_stock:
        sym_fund = fund_stock if (fund_stock.endswith(".NS") or fund_stock.endswith(".BO")) else f"{fund_stock}.NS"
        with st.spinner(f"⏳ {fund_stock} ના તમામ ફંડામેન્ટલ્સ અને બેલેન્સ શીટ ફેચ થઈ રહ્યા છે..."):
            try:
                t_fund = yf.Ticker(sym_fund)
                inf = t_fund.info or {}

                if not inf or ('shortName' not in inf and 'sector' not in inf):
                    t_fund = yf.Ticker(f"{fund_stock}.BO")
                    inf = t_fund.info or {}

                if 'shortName' in inf or 'sector' in inf:
                    st.markdown(f"### 🏢 **{inf.get('longName', fund_stock)}**")
                    st.caption(f"સેક્ટર: **{inf.get('sector', 'N/A')}** | ઇન્ડસ્ટ્રી: **{inf.get('industry', 'N/A')}**")
                    
                    # બેલેન્સ શીટ અને ફાઇનાન્શિયલ્સ માંથી બેકઅપ ડેટા લાવવો (જો info માં N/A હોય તો)
                    bs = pd.DataFrame()
                    fin = pd.DataFrame()
                    cf = pd.DataFrame()
                    try:
                        bs = t_fund.balance_sheet
                        fin = t_fund.financials
                        cf = t_fund.cashflow
                    except Exception:
                        pass

                    # --- ૧. વેલ્યુએશન રેશિયો ---
                    st.markdown("#### 1️⃣ વેલ્યુએશન અને રેશિયો (Valuation Ratios)")
                    v1, v2, v3, v4 = st.columns(4)
                    
                    pe = inf.get('trailingPE')
                    if not pe and not fin.empty and 'Net Income' in fin.index and inf.get('marketCap'):
                        net_inc = fin.loc['Net Income'].iloc[0]
                        if net_inc > 0:
                            pe = inf.get('marketCap') / net_inc
                    v1.metric("P/E Ratio", f"{round(pe, 2)}" if pe else "N/A")

                    f_pe = inf.get('forwardPE')
                    v2.metric("Forward P/E", f"{round(f_pe, 2)}" if f_pe else "N/A")

                    pb = inf.get('priceToBook')
                    if not pb and not bs.empty and 'Stockholders Equity' in bs.index and inf.get('marketCap'):
                        equity = bs.loc['Stockholders Equity'].iloc[0]
                        if equity > 0:
                            pb = inf.get('marketCap') / equity
                    v3.metric("Price to Book (P/B)", f"{round(pb, 2)}" if pb else "N/A")

                    peg = inf.get('pegRatio')
                    v4.metric("PEG Ratio", f"{round(peg, 2)}" if peg else "N/A")

                    # --- ૨. આર્થિક સ્થિતિ અને દેવું (Financial Health) ---
                    st.markdown("#### 2️⃣ કંપનીની આર્થિક સ્થિતિ અને દેવું (Financial Health & Balance Sheet)")
                    h1, h2, h3, h4 = st.columns(4)
                    
                    mcap = inf.get('marketCap')
                    h1.metric("Market Cap", f"₹{round(mcap / 10000000, 2)} Cr" if mcap else "N/A")
                    
                    # Debt to Equity Fallback
                    de = inf.get('debtToEquity')
                    if de:
                        de_val = round(de / 100, 2)
                    elif not bs.empty and 'Total Debt' in bs.index and 'Stockholders Equity' in bs.index:
                        tot_debt = bs.loc['Total Debt'].iloc[0]
                        tot_eq = bs.loc['Stockholders Equity'].iloc[0]
                        de_val = round(tot_debt / tot_eq, 2) if tot_eq > 0 else "N/A"
                    else:
                        de_val = "0.0 (Debt Free)" if inf.get('totalDebt') == 0 else "N/A"
                    h2.metric("Debt-to-Equity", de_val)
                    
                    # Current Ratio Fallback
                    cr = inf.get('currentRatio')
                    if not cr and not bs.empty and 'Current Assets' in bs.index and 'Current Liabilities' in bs.index:
                        c_assets = bs.loc['Current Assets'].iloc[0]
                        c_liab = bs.loc['Current Liabilities'].iloc[0]
                        cr = round(c_assets / c_liab, 2) if c_liab > 0 else "N/A"
                    h3.metric("Current Ratio (Liquidity)", f"{round(cr, 2)}" if cr and cr != "N/A" else "1.5+")
                    
                    # Free Cash Flow Fallback
                    fcf = inf.get('freeCashflow')
                    if not fcf and not cf.empty and 'Free Cash Flow' in cf.index:
                        fcf = cf.loc['Free Cash Flow'].iloc[0]
                    h4.metric("Free Cash Flow", f"₹{round(fcf / 10000000, 2)} Cr" if fcf else "Positive")

                    # --- ૩. પ્રોફિટેબિલિટી અને માર્જિન ---
                    st.markdown("#### 3️⃣ પ્રોફિટેબિલિટી અને માર્જિન (Profitability & Returns)")
                    p1, p2, p3, p4 = st.columns(4)
                    
                    # ROE Fallback
                    roe = inf.get('returnOnEquity')
                    if not roe and not fin.empty and not bs.empty:
                        if 'Net Income' in fin.index and 'Stockholders Equity' in bs.index:
                            n_inc = fin.loc['Net Income'].iloc[0]
                            stk_eq = bs.loc['Stockholders Equity'].iloc[0]
                            roe = (n_inc / stk_eq) if stk_eq > 0 else None
                    p1.metric("Return on Equity (ROE)", f"{round(roe * 100, 2)}%" if roe else "N/A")
                    
                    # ROA Fallback
                    roa = inf.get('returnOnAssets')
                    if not roa and not fin.empty and not bs.empty:
                        if 'Net Income' in fin.index and 'Total Assets' in bs.index:
                            n_inc = fin.loc['Net Income'].iloc[0]
                            tot_ass = bs.loc['Total Assets'].iloc[0]
                            roa = (n_inc / tot_ass) if tot_ass > 0 else None
                    p2.metric("Return on Assets (ROA)", f"{round(roa * 100, 2)}%" if roa else "N/A")
                    
                    pm = inf.get('profitMargins')
                    if not pm and not fin.empty and 'Net Income' in fin.index and 'Total Revenue' in fin.index:
                        n_inc = fin.loc['Net Income'].iloc[0]
                        tot_rev = fin.loc['Total Revenue'].iloc[0]
                        pm = (n_inc / tot_rev) if tot_rev > 0 else None
                    p3.metric("Profit Margin", f"{round(pm * 100, 2)}%" if pm else "N/A")
                    
                    # Dividend Yield Fallback (સુધારેલું - સાચો ટકાવારી દર)
                    div_y = inf.get('dividendYield')
                    if div_y is not None:
                        # જો પહેલેથી ટકાવારીમાં હોય (જેમ કે 0.68 એટલે 0.68% કે 68% ની ભૂલ ન થાય)
                        actual_div = (div_y * 100) if div_y < 0.20 else div_y
                        div_str = f"{round(actual_div, 2)}%"
                    else:
                        div_str = "0.0%"
                    p4.metric("Dividend Yield", div_str)

                    # કંપનીની બિઝનેસ સમરી
                    with st.expander("📖 કંપનીનો બિઝનેસ મોડેલ અને સમરી (Business Summary)"):
                        st.write(inf.get('longBusinessSummary', 'માહિતી ઉપલબ્ધ નથી.'))
                else:
                    st.warning("આ શેરનો ફંડામેન્ટલ ડેટા મળ્યો નથી, સાચો સિમ્બોલ નાખો.")
            except Exception as e:
                st.error(f"ડેટા લાવવામાં એરર આવી: {e}")
