import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

# NASDAQ 100 symbols from your codebase
all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO",
    "TSLA", "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN",
    "TMUS", "MU", "LIN", "PEP", "SHOP", "APP", "INTU", "AMAT",
    "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG", "AMGN", "TXN",
    "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
    "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS",
    "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
    "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY",
    "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA",
    "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
    "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP",
    "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
    "ON", "BIIB", "LULU", "CDW", "GFS"
]

# Database connection
def get_db_connection():
    """Create database connection"""
    try:
        database_url = os.getenv('DATABASE_URL', 'postgresql://aitrader:aitrader_password@postgres:5432/trading_db')
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Fetch stock data from Alpha Vantage
def fetch_stock_data_alpha_vantage(ticker, interval='5min'):
    """
    Fetch stock data from Alpha Vantage API
    
    Args:
        ticker: Stock symbol
        interval: Time interval - 1min, 5min, 15min, 30min, 60min, daily, weekly, monthly
    """
    api_key = os.getenv('ALPHAADVANTAGE_API_KEY')
    if not api_key:
        st.error("ALPHAADVANTAGE_API_KEY not found in .env file")
        return None
    
    try:
        if interval == 'daily':
            function = 'TIME_SERIES_DAILY'
            time_key = 'Time Series (Daily)'
        elif interval in ['1min', '5min', '15min', '30min', '60min']:
            function = 'TIME_SERIES_INTRADAY'
            time_key = f'Time Series ({interval})'
        else:
            function = 'TIME_SERIES_DAILY'
            time_key = 'Time Series (Daily)'
        
        url = f'https://www.alphavantage.co/query'
        params = {
            'function': function,
            'symbol': ticker,
            'apikey': api_key,
            'outputsize': 'full'
        }
        
        if function == 'TIME_SERIES_INTRADAY':
            params['interval'] = interval
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'Error Message' in data:
            st.error(f"Error fetching data for {ticker}: {data['Error Message']}")
            return None
        
        if 'Note' in data:
            st.warning(f"API rate limit reached. Please wait a moment.")
            return None
        
        if time_key not in data:
            st.error(f"No data found for {ticker}")
            return None
        
        # Convert to DataFrame
        time_series = data[time_key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Rename columns
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.astype(float)
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching data from Alpha Vantage: {e}")
        return None

# Save stock prices to database
def save_stock_prices_to_db(ticker, data, market='us'):
    """Save stock price data to PostgreSQL"""
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        for index, row in data.iterrows():
            cursor.execute("""
                INSERT INTO stock_prices (symbol, date, open_price, high_price, low_price, close_price, volume, market)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date, market) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            """, (ticker, index, row['Open'], row['High'], row['Low'], row['Close'], row['Volume'], market))
        conn.commit()
        cursor.close()
        st.success(f"Saved {len(data)} records for {ticker} to database")
    except Exception as e:
        st.warning(f"Error saving to database: {e}")
    finally:
        conn.close()

# Fetch AI agent positions from database
def fetch_agent_positions():
    """Fetch latest agent trading positions from database"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        query = """
            SELECT agent_signature, symbol, amount, price, cash_balance, date
            FROM latest_positions
            ORDER BY date DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.warning(f"Error fetching agent positions: {e}")
        conn.close()
        return pd.DataFrame()

# Fetch agent performance metrics
def fetch_agent_metrics():
    """Fetch AI agent performance metrics"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        query = """
            SELECT agent_signature, date, total_value, daily_return, cumulative_return, sharpe_ratio
            FROM agent_metrics
            ORDER BY date DESC
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.warning(f"Error fetching metrics: {e}")
        conn.close()
        return pd.DataFrame()

# Calculate basic metrics
def calculate_metrics(data):
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = data['High'].max()
    low = data['Low'].min()
    volume = data['Volume'].sum()
    return last_close, change, pct_change, high, low, volume

# Add technical indicators (simple moving averages)
def add_technical_indicators(data):
    if len(data) >= 20:
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
    if len(data) >= 14:
        # Simple RSI calculation
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI_14'] = 100 - (100 / (1 + rs))
    return data

# Main Dashboard
st.set_page_config(layout='wide', page_title='AI-Trader Stock Dashboard')
st.title('🤖 AI-Trader Real-Time Stock Dashboard')

# Create tabs
tab1, tab2, tab3 = st.tabs(["📈 Stock Analysis", "🤖 AI Agent Performance", "💼 Portfolio"])

# Tab 1: Stock Analysis
with tab1:
    st.header('Stock Price Analysis (Alpha Vantage)')
    
    # Sidebar for user input
    st.sidebar.header('Chart Parameters')
    ticker = st.sidebar.selectbox('Ticker', all_nasdaq_100_symbols, index=0)
    
    interval_options = {
        'Intraday (1min)': '1min',
        'Intraday (5min)': '5min',
        'Intraday (15min)': '15min',
        'Intraday (30min)': '30min',
        'Intraday (60min)': '60min',
        'Daily': 'daily'
    }
    interval_label = st.sidebar.selectbox('Time Interval', list(interval_options.keys()), index=1)
    interval = interval_options[interval_label]
    
    chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
    indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20', 'RSI 14'])

    # Update dashboard
    if st.sidebar.button('Update') or ticker:
        with st.spinner(f'Fetching data for {ticker}...'):
            data = fetch_stock_data_alpha_vantage(ticker, interval)
            
            if data is not None and not data.empty:
                # Save to database
                save_stock_prices_to_db(ticker, data)
                
                # Reset index for plotting
                data = data.reset_index()
                data.rename(columns={'index': 'Datetime'}, inplace=True)
                
                # Add technical indicators
                data = add_technical_indicators(data)

                last_close, change, pct_change, high, low, volume = calculate_metrics(data)

                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(f"{ticker} Last Price", f"${last_close:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
                col2.metric('High', f"${high:.2f}")
                col3.metric('Low', f"${low:.2f}")
                col4.metric('Volume', f"{int(volume):,}")

                # Plot chart
                fig = go.Figure()
                if chart_type == 'Candlestick':
                    fig.add_trace(go.Candlestick(
                        x=data['Datetime'], 
                        open=data['Open'],
                        high=data['High'], 
                        low=data['Low'], 
                        close=data['Close'],
                        name=ticker
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'], 
                        y=data['Close'], 
                        name=ticker,
                        mode='lines'
                    ))

                # Add indicators
                if 'SMA 20' in indicators and 'SMA_20' in data.columns:
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], name='SMA 20', line=dict(dash='dash')))
                if 'EMA 20' in indicators and 'EMA_20' in data.columns:
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], name='EMA 20', line=dict(dash='dot')))

                fig.update_layout(
                    title=f"{ticker} {interval_label} Chart",
                    xaxis_title='Time', 
                    yaxis_title='Price (USD)',
                    height=600,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # RSI chart if selected
                if 'RSI 14' in indicators and 'RSI_14' in data.columns:
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(x=data['Datetime'], y=data['RSI_14'], name='RSI 14'))
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
                    fig_rsi.update_layout(
                        title='RSI Indicator',
                        xaxis_title='Time',
                        yaxis_title='RSI',
                        height=300
                    )
                    st.plotly_chart(fig_rsi, use_container_width=True)

                # Historical data
                st.subheader('Historical Data')
                display_data = data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']].tail(100)
                st.dataframe(display_data, use_container_width=True)

# Tab 2: AI Agent Performance
with tab2:
    st.header('AI Trading Agent Performance')
    
    # Fetch agent positions
    positions_df = fetch_agent_positions()
    if not positions_df.empty:
        st.subheader('Current Agent Positions')
        st.dataframe(positions_df, use_container_width=True)
        
        # Agent portfolio visualization
        if 'amount' in positions_df.columns and 'price' in positions_df.columns:
            positions_df['value'] = positions_df['amount'] * positions_df['price']
            fig = px.bar(positions_df, x='symbol', y='value', color='agent_signature',
                        title='Agent Portfolio Values by Symbol')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No agent trading data available yet. Start the AI-Trader agent to see data.")
    
    # Fetch metrics
    metrics_df = fetch_agent_metrics()
    if not metrics_df.empty:
        st.subheader('Performance Metrics')
        
        # Plot total value over time
        fig = px.line(metrics_df, x='date', y='total_value', color='agent_signature',
                     title='Agent Portfolio Value Over Time')
        st.plotly_chart(fig, use_container_width=True)
        
        # Display metrics table
        st.dataframe(metrics_df, use_container_width=True)

# Tab 3: Portfolio Overview
with tab3:
    st.header('Portfolio Overview')
    
    positions_df = fetch_agent_positions()
    if not positions_df.empty:
        # Group by agent
        for agent in positions_df['agent_signature'].unique():
            st.subheader(f"Agent: {agent}")
            agent_data = positions_df[positions_df['agent_signature'] == agent]
            
            # Display positions
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Cash Balance", f"${agent_data['cash_balance'].iloc[0]:,.2f}")
            with col2:
                total_holdings = (agent_data['amount'] * agent_data['price']).sum()
                st.metric("Total Holdings", f"${total_holdings:,.2f}")
            
            # Position details
            st.dataframe(agent_data[['symbol', 'amount', 'price', 'date']], use_container_width=True)
    else:
        st.info("No portfolio data available yet.")

# Sidebar: Quick stock lookup for top NASDAQ symbols
st.sidebar.header('Quick Stock Lookup')
quick_symbols = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX']
for symbol in quick_symbols:
    if st.sidebar.button(f"📊 {symbol}", key=f"quick_{symbol}"):
        st.session_state['ticker'] = symbol
        st.rerun()

st.sidebar.subheader('About')
st.sidebar.info(
    'This dashboard integrates AI-Trader agent data with real-time stock analysis '
    'using Alpha Vantage API. Supports all NASDAQ 100 symbols.'
)