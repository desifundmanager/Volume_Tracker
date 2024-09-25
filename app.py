import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import pytz
import traceback

# Initialize session state for storing symbols
if 'symbols' not in st.session_state:
    st.session_state.symbols = []

# Analyze stock data
@st.cache_data(ttl=3600)
def analyze_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y")
        
        if hist.empty:
            st.warning(f"No data available for symbol: {symbol}")
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
    except Exception as e:
        st.error(f"Error analyzing stock {symbol}: {str(e)}")
        st.error(traceback.format_exc())
        return None

def run_volume_tracker():
    st.markdown('<p style="font-size: 30px;">Stock Volume Tracker</p>', unsafe_allow_html=True)

    # Debug output
    st.write("Debug: Application started")

    # Sidebar for adding and removing symbols
    with st.sidebar:
        st.header("Manage Symbols")
        new_symbol = st.text_input("Add new symbol").upper()
        if st.button("Add Symbol") and new_symbol:
            if new_symbol not in st.session_state.symbols:
                st.session_state.symbols.append(new_symbol)
                st.success(f"Added {new_symbol}")
            else:
                st.warning(f"{new_symbol} already exists")
        
        if st.session_state.symbols:
            symbol_to_remove = st.selectbox("Select symbol to remove", st.session_state.symbols)
            if st.button("Remove Symbol"):
                st.session_state.symbols.remove(symbol_to_remove)
                st.success(f"Removed {symbol_to_remove}")

    # Debug output
    st.write(f"Debug: Current symbols: {st.session_state.symbols}")

    # Update button
    if st.button('🔄 Update Data'):
        st.cache_data.clear()
        st.rerun()

    # Main app logic
    if st.session_state.symbols:
        st.write("Debug: Analyzing stocks...")
        with st.spinner('Analyzing stocks...'):
            results = []
            for symbol in st.session_state.symbols:
                data = analyze_stock(symbol)
                if data is not None:
                    results.append(data)

        st.write(f"Debug: Analysis complete. Results: {len(results)} stocks")

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
        st.info("No symbols added yet. Use the sidebar to add symbols to track.")

    # Final debug output
    st.write("Debug: Application completed")

if __name__ == "__main__":
    try:
        run_volume_tracker()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error(traceback.format_exc())