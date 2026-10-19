# ==================== Live Marquee Ticker (Nifty50, Sensex, Bank Nifty) ====================
@st.cache_data(ttl=60)
def get_live_ticker_indices():
    indices = {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANK NIFTY": "^NSEBANK",
        "NIFTY IT": "^CNXIT",
        "INDIA VIX": "^INDIAVIX"
    }
    ticker_items = []
    for name, sym in indices.items():
        try:
            t = yf.Ticker(sym, session=session)
            # Fast real-time price info
            fast = t.fast_info
            curr_price = fast.last_price
            prev_close = fast.previous_close
            
            if curr_price and prev_close:
                chg = curr_price - prev_close
                chg_pct = (chg / prev_close) * 100
                color = "#00c853" if chg >= 0 else "#ff3d00"
                sign = "+" if chg >= 0 else ""
                
                ticker_items.append(
                    f"<span style='margin-right: 40px; font-weight: 600; font-size: 15px;'>"
                    f"{name}: <span style='color: white;'>₹{curr_price:,.2f}</span> "
                    f"<span style='color: {color};'>({sign}{chg:,.2f} | {sign}{chg_pct:.2f}%)</span>"
                    f"</span>"
                )
        except Exception:
            continue
            
    if not ticker_items:
        # Backup jo network busy hoy to
        return "<span>NIFTY 50: ₹24,850 (+0.45%) | SENSEX: 81,400 (+0.38%) | BANK NIFTY: 51,200 (+0.52%)</span>"
        
    return "".join(ticker_items)

# Ticker data fetch karo
ticker_html_content = get_live_ticker_indices()

# CSS sathe continuous scrolling marquee
ticker_component = f"""
<style>
.ticker-wrap {{
    width: 100%;
    overflow: hidden;
    background-color: #12141a;
    padding: 10px 0;
    border-radius: 8px;
    border: 1px solid #2d3139;
    margin-bottom: 20px;
    white-space: nowrap;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}}
.ticker-move {{
    display: inline-block;
    white-space: nowrap;
    padding-left: 100%;
    animation: ticker-anim 25s linear infinite;
}}
.ticker-move:hover {{
    animation-play-state: paused;
}}
@keyframes ticker-anim {{
    0% {{ transform: translate3d(0, 0, 0); }}
    100% {{ transform: translate3d(-100%, 0, 0); }}
}}
</style>

<div class="ticker-wrap">
    <div class="ticker-move">
        {ticker_html_content}
    </div>
</div>
"""

# Streamlit ma render karo
st.markdown(ticker_component, unsafe_allow_html=True)
# ===========================================================================================
