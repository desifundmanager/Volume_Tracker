import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz
import hashlib
import sqlite3

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None

# Database setup
def init_db():
    conn = sqlite3.connect('stock_tracker.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('DROP TABLE IF EXISTS user_symbols')
    c.execute('''CREATE TABLE users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE user_symbols
                 (user_id INTEGER, symbol TEXT,
                 FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Add the single user
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              ('pranav', hash_password('learn to code')))
    
    # Add the predefined symbols
    user_id = c.lastrowid
    symbols = [
        'DCW.NS', 'SPICEJET.BO', 'STYRENIX.NS', 'PANACEABIO.NS', 'NPOWER.NS',
        'TIRUMALCHM.NS', 'INDOSTAR.NS', 'INDIGOPNTS.NS', 'BEPL.NS', 'VINATIORGA.NS',
        'NELCO.NS', 'DREAMFOLKS.NS', 'RAMCOCEM.NS', 'VEDL.NS', 'RKSWAMY.NS',
        'PPLPHARMA.NS', 'SAIL.NS', 'DEEDEV.NS', 'INDA', 'SMIN',
        'SHYAMMETL.NS', 'CORALFINAC.NS', 'TREJHARA.NS', 'RBA.NS', 'STEELCAS.BO',
        'QUICKHEAL.NS', 'EICHERMOT.NS', 'PNBHOUSING.NS', 'JYOTISTRUC.NS', 'SHK.NS',
        'BCONPRDTS.NS', 'IDEA.NS', 'ARVIND.NS', 'SEQUENT.NS', 'MANINDS.NS',
        'WELCORP.NS', 'LINC.NS'
    ]
    for symbol in symbols:
        c.execute("INSERT INTO user_symbols (user_id, symbol) VALUES (?, ?)", (user_id, symbol))
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    conn = sqlite3.connect('stock_tracker.db')
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and user[1] == hash_password(password):
        return user[0]
    return None

def get_user_symbols(user_id):
    conn = sqlite3.connect('stock_tracker.db')
    c = conn.cursor()
    c.execute("SELECT symbol FROM user_symbols WHERE user_id = ?", (user_id,))
    symbols = [row[0] for row in c.fetchall()]
    conn.close()
    return symbols

def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user_id = verify_user(username, password)
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

@st.cache_data(ttl=3600)
def analyze_stock(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1y")
    
    if hist.empty:
        return None
    
    hist['Avg_Volume'] = hist['Volume'].rolling(window=10).mean()
    hist['Volume_Change'] = (hist['Volume'] - hist['Avg_Volume']) / hist['Avg_Volume'] * 100
    hist['Daily_Change'] = hist['Close'].pct_change() * 100
    
    current_year = datetime.datetime.now(pytz.timezone('UTC')).year
    ytd_start = datetime.datetime(current_year, 1, 1, tzinfo=pytz.timezone('UTC'))
    ytd_start_price = hist.loc[hist.index >= ytd_start, 'Close'].iloc[0]
    ytd_return = (hist['Close'].iloc[-1] - ytd_start_price) / ytd_start_price * 100
    
    latest = hist.iloc[-1]
    
    return {
        'Symbol': symbol,
        'Close': latest['Close'],
        'Daily_Change': latest['Daily_Change'],
        'YTD_Return': ytd_return,
        'Volume': latest['Volume'],
        'Avg_Volume': hist['Avg_Volume'].iloc[-1],
        'Volume_Change': hist['Volume_Change'].iloc[-1],
        'Date': latest.name.date(),
    }

def run_volume_tracker():
    st.markdown('<p style="font-size: 30px;">Stock Volume Tracker</p>', unsafe_allow_html=True)

    # Update button
    if st.button('🔄 Update Data'):
        st.cache_data.clear()
        st.rerun()

    # Main app logic
    user_symbols = get_user_symbols(st.session_state.user_id)
    if user_symbols:
        with st.spinner('Analyzing stocks...'):
            results = []
            for symbol in user_symbols:
                data = analyze_stock(symbol)
                if data is not None:
                    results.append(data)

        if results:
            df = pd.DataFrame(results)
            df['Avg_Volume'] = df['Avg_Volume'].fillna(0).round(0).astype(int)
            df = df.sort_values(by='Volume_Change', ascending=False)

            df['Close'] = df['Close'].round(2)
            df['Daily_Change'] = df['Daily_Change'].round(2)
            df['YTD_Return'] = df['YTD_Return'].round(2)
            df['Volume'] = df['Volume'].astype(int)
            df['Volume_Change'] = df['Volume_Change'].round(2)

            df['Price'] = df.apply(lambda row: f"{row['Close']:.2f} ({row['Daily_Change']:+.2f}%)", axis=1)

            column_order = ['Symbol', 'Price', 'Daily_Change', 'Volume_Change', 'Volume', 'Avg_Volume', 'YTD_Return', 'Date']
            df = df[column_order]

            # Display statistics at the top
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stocks", len(df))
            with col2:
                st.metric("Stocks with Positive Daily Change", len(df[df['Daily_Change'] > 0]))
            with col3:
                st.metric("Stocks with Positive Volume Change", len(df[df['Volume_Change'] > 0]))

            # Display the dataframe
            st.dataframe(df.style.format({
                'Daily_Change': '{:+.2f}%',
                'YTD_Return': '{:.2f}%',
                'Volume': '{:,}',
                'Avg_Volume': '{:,}',
                'Volume_Change': '{:.2f}%'
            }).applymap(lambda x: f"background-color: {'#c6efce' if x > 0 else '#ffc7ce'}; color: {'#006100' if x > 0 else '#9c0006'}" if isinstance(x, (int, float)) else '', subset=['Daily_Change', 'YTD_Return', 'Volume_Change']),
            use_container_width=True)

            st.write(f"Data generated on: {datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            st.warning("No valid data found for the given symbols.")
    else:
        st.info("No symbols found in the database.")

    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.rerun()

def main():
    init_db()
    if st.session_state.logged_in:
        run_volume_tracker()
    else:
        login()

if __name__ == "__main__":
    main()