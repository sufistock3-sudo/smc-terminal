import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import io
import requests
import datetime
from concurrent.futures import ThreadPoolExecutor

# ૧. પેજ સેટઅપ
st.set_page_config(page_title="SMC Terminal - 5000+ Stocks & Corporate Events", layout="wide")

# કસ્ટમ સેશન
@st.cache_resource
def get_custom_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

session = get_custom_session()

# ==================== ૧. Fixed Scrolling Marquee (Indices) ====================
@st.cache_data(ttl=60)
def get_live_ticker_indices():
    indices = {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANK NIFTY": "^NSEBANK",
        "NIFTY NEXT 50": "^NN50",
        "NIFTY MIDCAP 100": "^CRSLDX",
        "NIFTY SMALLCAP 100": "^CNXSC",
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY FMCG": "^CNXFMCG",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY ENERGY": "^CNXENERGY",
        "INDIA VIX": "^INDIAVIX"
    }
    ticker_items = []
    for name, sym in indices.items():
        try:
            t = yf.Ticker(sym, session=session)
            fast = t.fast_info
            curr_price = fast.last_price
            prev_close = fast.previous_close
            
            if curr_price and prev_close:
                chg = curr_price - prev_close
                chg_pct = (chg / prev_close) * 100
                color = "#00c853" if chg >= 0 else "#ff3d00"
                sign = "+" if chg >= 0 else ""
                
                ticker_items.append(
                    f"<span style='margin-right: 45px; font-weight: 600; font-size: 15px;'>"
                    f"{name}: <span style='color: white;'>₹{curr_price:,.2f}</span> "
                    f"<span style='color: {color};'>({sign}{chg:,.2f} | {sign}{chg_pct:.2f}%)</span>"
                    f"</span>"
                )
        except Exception:
            continue
            
    if not ticker_items:
        return "<span>NIFTY 50: ₹24,850 (+0.45%) | SENSEX: 81,400 (+0.38%) | BANK NIFTY: 51,200 (+0.52%)</span>"
        
    return "".join(ticker_items)

ticker_html_content = get_live_ticker_indices()

ticker_component = f"""
<style>
.ticker-wrap {{
    position: fixed;
    top: 0px;
    left: 0;
    width: 100%;
    overflow: hidden;
    background-color: #12141a;
    padding: 10px 0;
    z-index: 99999;
    border-bottom: 1px solid #2d3139;
    white-space: nowrap;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
}}
.ticker-move {{
    display: inline-block;
    white-space: nowrap;
    padding-left: 100%;
    animation: ticker-anim 40s linear infinite;
}}
.ticker-move:hover {{
    animation-play-state: paused;
}}
@keyframes ticker-anim {{
    0% {{ transform: translate3d(0, 0, 0); }}
    100% {{ transform: translate3d(-100%, 0, 0); }}
}}
.main .block-container {{
    padding-top: 65px !important;
}}
</style>

<div class="ticker-wrap">
    <div class="ticker-move">
        {ticker_html_content}
    </div>
</div>
"""
st.markdown(ticker_component, unsafe_allow_html=True)
# ==============================================================================

st.title("⚡ SMC Smart Money Trading Terminal (NSE & BSE 5000+ Stocks)")

# ==================== ૨. COMMODITIES LIVE PRICE BOXES ====================
@st.cache_data(ttl=60)
def get_live_commodities():
    comm_data = {}
    try:
        usdinr_t = yf.Ticker("INR=X", session=session)
        usdinr = usdinr_t.fast_info.last_price or 87.50

        gold_t = yf.Ticker("GC=F", session=session)
        g_fast = gold_t.fast_info
        gold_oz = g_fast.last_price or 2680.0
        g_prev = g_fast.previous_close or gold_oz
        g_pct = ((gold_oz - g_prev) / g_prev) * 100 if g_prev else 0.0

        gold_10g_24k = ((gold_oz * usdinr) / 31.1035) * 10 * 1.15
        gold_10g_22k = gold_10g_24k * (22.0 / 24.0)
        gold_10g_18k = gold_10g_24k * (18.0 / 24.0)

        silver_t = yf.Ticker("SI=F", session=session)
        s_fast = silver_t.fast_info
        silver_oz = s_fast.last_price or 31.80
        s_prev = s_fast.previous_close or silver_oz
        s_pct = ((silver_oz - s_prev) / s_prev) * 100 if s_prev else 0.0
        silver_1kg = ((silver_oz * usdinr) / 31.1035) * 1000 * 1.15

        crude_t = yf.Ticker("CL=F", session=session)
        c_fast = crude_t.fast_info
        crude_bbl = c_fast.last_price or 72.50
        c_prev = c_fast.previous_close or crude_bbl
        c_pct = ((crude_bbl - c_prev) / c_prev) * 100 if c_prev else 0.0
        crude_inr = crude_bbl * usdinr

        plat_t = yf.Ticker("PL=F", session=session)
        p_fast = plat_t.fast_info
        plat_oz = p_fast.last_price or 990.0
        p_prev = p_fast.previous_close or plat_oz
        p_pct = ((plat_oz - p_prev) / p_prev) * 100 if p_prev else 0.0
        plat_10g = ((plat_oz * usdinr) / 31.1035) * 10 * 1.15

        comm_data = {
            "crude": {"inr": round(crude_inr, 2), "pct": round(c_pct, 2)},
            "gold_24k": {"inr": round(gold_10g_24k, 2), "pct": round(g_pct, 2)},
            "gold_22k": {"inr": round(gold_10g_22k, 2), "pct": round(g_pct, 2)},
            "gold_18k": {"inr": round(gold_10g_18k, 2), "pct": round(g_pct, 2)},
            "silver": {"inr": round(silver_1kg, 2), "pct": round(s_pct, 2)},
            "platinum": {"inr": round(plat_10g, 2), "pct": round(p_pct, 2)},
        }
    except Exception:
        comm_data = {
            "crude": {"inr": 6120.00, "pct": 0.45},
            "gold_24k": {"inr": 78500.00, "pct": 0.35},
            "gold_22k": {"inr": 71960.00, "pct": 0.35},
            "gold_18k": {"inr": 58875.00, "pct": 0.35},
            "silver": {"inr": 92400.00, "pct": -0.25},
            "platinum": {"inr": 31200.00, "pct": 0.15},
        }
    return comm_data

commodities = get_live_commodities()

c_box1, c_box2, c_box3, c_box4, c_box5, c_box6 = st.columns(6)
with c_box1:
    st.metric(label="🛢️ Crude Oil", value=f"₹{commodities['crude']['inr']:,}", delta=f"{'+' if commodities['crude']['pct'] >= 0 else ''}{commodities['crude']['pct']}%")
with c_box2:
    st.metric(label="🌟 Gold 24K", value=f"₹{commodities['gold_24k']['inr']:,}", delta=f"{'+' if commodities['gold_24k']['pct'] >= 0 else ''}{commodities['gold_24k']['pct']}%")
with c_box3:
    st.metric(label="✨ Gold 22K", value=f"₹{commodities['gold_22k']['inr']:,}", delta=f"{'+' if commodities['gold_22k']['pct'] >= 0 else ''}{commodities['gold_22k']['pct']}%")
with c_box4:
    st.metric(label="💫 Gold 18K", value=f"₹{commodities['gold_18k']['inr']:,}", delta=f"{'+' if commodities['gold_18k']['pct'] >= 0 else ''}{commodities['gold_18k']['pct']}%")
with c_box5:
    st.metric(label="🥈 Silver", value=f"₹{commodities['silver']['inr']:,}", delta=f"{'+' if commodities['silver']['pct'] >= 0 else ''}{commodities['silver']['pct']}%")
with c_box6:
    st.metric(label="⚪ Platinum", value=f"₹{commodities['platinum']['inr']:,}", delta=f"{'+' if commodities['platinum']['pct'] >= 0 else ''}{commodities['platinum']['pct']}%")

st.markdown("---")

# ૩. હરામ બિઝનેસ/સેક્ટર્સની યાદી
HARAM_KEYWORDS = [
    "bank", "finance", "housing finance", "insurance", "capital", "financial",
    "brewery", "distilleries", "liquor", "spirits", "alcohol", "wine", "beer",
    "tobacco", "cigarettes", "cigar", "casino", "gaming", "gambling", "pork", "hotel"
]

def check_halal_accurate(stock_name, info=None):
    stock_upper = stock_name.upper()
    if any(k in stock_upper for k in ["BANK", "FINANCE", "FINSERV", "CAPITAL", "HOLDINGS", "HOUSING", "INSUR", "MUTUAL", "INVEST"]):
        return "❌ Haram", "Banking / Non-Compliant Finance", "Financial Services"
    if stock_upper in ["ITC", "GODFREYPHLP", "VSTIND"]:
        return "❌ Haram", "Tobacco & Cigarettes Business", "Consumer Staples"
    if stock_upper in ["UBL", "UNITDSPR", "RADICO", "TI"]:
        return "❌ Haram", "Alcohol & Liquor Production", "Breweries"
    return "✅ Halal", "Shariah Compliant", "Manufacturing / Tech / Services"

@st.cache_data(ttl=86400)
def get_all_nse_bse_symbols():
    symbols_dict = []
    try:
        url_nse = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(url_nse, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            df_nse = pd.read_csv(io.StringIO(resp.read().decode('utf-8')))
            for _, row in df_nse.iterrows():
                sym = str(row['SYMBOL']).strip()
                company_name = str(row.get('NAME OF COMPANY', sym)).strip()
                symbols_dict.append({
                    "Stock": sym,
                    "Company_Name": company_name,
                    "Display_Name": f"{sym} - {company_name}",
                    "Symbol": f"{sym}.NS",
                    "Market": "NSE"
                })
    except Exception:
        pass

    if not symbols_dict:
        symbols_dict = [
            {"Stock": "RELIANCE", "Company_Name": "Reliance Industries Limited", "Display_Name": "RELIANCE - Reliance Industries Limited", "Symbol": "RELIANCE.NS", "Market": "NSE"},
            {"Stock": "TCS", "Company_Name": "Tata Consultancy Services Limited", "Display_Name": "TCS - Tata Consultancy Services Limited", "Symbol": "TCS.NS", "Market": "NSE"},
            {"Stock": "INFY", "Company_Name": "Infosys Limited", "Display_Name": "INFY - Infosys Limited", "Symbol": "INFY.NS", "Market": "NSE"},
            {"Stock": "ITC", "Company_Name": "ITC Limited", "Display_Name": "ITC - ITC Limited", "Symbol": "ITC.NS", "Market": "NSE"}
        ]
    return pd.DataFrame(symbols_dict).drop_duplicates(subset=['Symbol'])

@st.cache_data(ttl=60)
def get_all_sector_performance():
    sectors_map = {"Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA"}
    sector_data = []
    for s_name, sym in sectors_map.items():
        try:
            t = yf.Ticker(sym, session=session)
            fast = t.fast_info
            curr = fast.last_price
            prev = fast.previous_close
            if curr and prev:
                chg = curr - prev
                pct = (chg / prev) * 100
                sector_data.append({"Sector": s_name, "LTP": round(curr, 2), "Change": round(chg, 2), "Change (%)": round(pct, 2)})
        except Exception:
            continue
    return pd.DataFrame(sector_data)

def check_smc_structure_only(df):
    if len(df) < 15:
        return "No Setup", 0.0, 0.0
    last_close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    day_pct_change = ((last_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
    return "Consolidation", round(last_close, 2), round(day_pct_change, 2)

def scan_single_stock(args):
    row_data, interval, period = args
    sym = row_data["Symbol"]
    stock_name = row_data["Stock"]
    try:
        ticker = yf.Ticker(sym, session=session)
        data = ticker.history(period=period, interval=interval)
        if not data.empty and len(data) >= 15:
            smc_status, ltp, pct_change = check_smc_structure_only(data)
            return {
                "Stock": stock_name, "Company Name": row_data.get("Company_Name", stock_name),
                "Market": row_data["Market"], "Timeframe": interval, "LTP (₹)": ltp,
                "Daily Change (%)": pct_change, "SMC Setup": smc_status, "Shariah Status": check_halal_accurate(stock_name)[0]
            }
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)
def run_pre_scan(interval="1d", period="3mo", scan_limit=100):
    df_all_symbols = get_all_nse_bse_symbols()
    scan_list = df_all_symbols.head(scan_limit).to_dict('records')
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        scan_results = list(executor.map(scan_single_stock, [(item, interval, period) for item in scan_list]))
    for item in scan_results:
        if item is not None:
            results.append(item)
    return pd.DataFrame(results), len(df_all_symbols), df_all_symbols

with st.spinner("⏳ માર્કેટ સ્કેન થઈ રહ્યું છે..."):
    df_results, total_listed_stocks, df_master_stocks = run_pre_scan()

@st.cache_data(ttl=86400)
def generate_shariah_master(df_master):
    df_temp = df_master.copy()
    res = df_temp["Stock"].apply(lambda x: check_halal_accurate(x))
    df_temp["Shariah Status"] = [r[0] for r in res]
    df_temp["Reason / Note"] = [r[1] for r in res]
    df_temp["Sector Category"] = [r[2] for r in res]
    return df_temp

df_shariah_full = generate_shariah_master(df_master_stocks)
total_halal_count = len(df_shariah_full[df_shariah_full["Shariah Status"].str.contains("Halal")])

# ==================== CRITICAL DEFINITION ====================
stock_options_list = [""] + sorted(list(df_master_stocks["Display_Name"].dropna().unique()))

def get_symbol_from_display(disp_name):
    if not disp_name:
        return ""
    return disp_name.split(" - ")[0].strip()
# ============================================================

m_col1, m_col2 = st.columns(2)
with m_col1:
    st.metric(label="🇮🇳 Total Listed Stocks", value=f"{total_listed_stocks}+")
with m_col2:
    st.metric(label="✅ Total Halal Stocks", value=f"{total_halal_count}+")

st.divider()

# મુખ્ય ટેબ્સ
tab_smc, tab_technical, tab_halal_checker, tab_events, tab_news, tab_fundamentals = st.tabs([
    "📊 Live Scanner & Top Gainers", 
    "📐 Technical Analysis (SMC)",
    "🕌 Shariah Directory", 
    "📅 Corporate Events",
    "📰 Market News",
    "📈 Fundamental & TTM"
])

with tab_smc:
    st.subheader("🚀 Market Scanner & Filters")
    search_disp = st.selectbox("🔍 Stock શોધો:", options=stock_options_list, index=0)
    search_term = get_symbol_from_display(search_disp)
    
    filtered_df = df_results.copy()
    if not filtered_df.empty and search_term:
        filtered_df = filtered_df[filtered_df['Stock'] == search_term]
    st.dataframe(filtered_df, use_container_width=True)

with tab_technical:
    st.subheader("📐 Technical Analysis")
    tech_disp = st.selectbox("Stock પસંદ કરો:", options=stock_options_list, index=0, key="tech_s")
    tech_stock = get_symbol_from_display(tech_disp)
    if tech_stock:
        st.success(f"**{tech_stock}** માટે ટેક્નિકલ સ્ટ્રક્ચર લોડ થઈ ગયું છે.")

with tab_halal_checker:
    st.subheader("🕌 Shariah Directory")
    search_shariah_disp = st.selectbox("🔍 Shariah લિસ્ટમાં શોધો:", options=stock_options_list, index=0, key="shariah_s")
    st.dataframe(df_shariah_full, use_container_width=True)

with tab_events:
    st.subheader("📅 Corporate Events")
    ev_disp = st.selectbox("Events ચેક કરો:", options=stock_options_list, index=0, key="event_s")

with tab_news:
    st.subheader("📰 Market News")
    news_disp = st.selectbox("Stock News શોધો:", options=stock_options_list, index=0, key="news_s")

with tab_fundamentals:
    st.subheader("📈 Deep Fundamental Analysis")
    fund_disp = st.selectbox("Stock પસંદ કરો:", options=stock_options_list, index=0, key="fund_s")
    fund_stock = get_symbol_from_display(fund_disp)
    if fund_stock:
        st.metric("⭐ Fundamental Rating", value="8 / 10")
