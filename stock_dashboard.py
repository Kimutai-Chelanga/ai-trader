import yfinance as yf
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import ta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

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

# Fetch stock data from Yahoo Finance
def fetch_stock_data(ticker, period, interval):
    try:
        end_date = datetime.now()
        if period == '1wk':
            start_date = end_date - timedelta(days=7)
        else:
            start_date = end_date - timedelta(days=int(period[:-1]))
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        if data.empty:
            st.error(f"No data found for {ticker}. Please check the ticker symbol and try again.")
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
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

# Process data for visualization
def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data

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

# Add technical indicators
def add_technical_indicators(data):
    data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
    data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    data['RSI_14'] = ta.momentum.rsi(data['Close'], window=14)
    return data

# Main Dashboard
st.set_page_config(layout='wide', page_title='AI-Trader Stock Dashboard')
st.title('🤖 AI-Trader Real-Time Stock Dashboard')

# Create tabs
tab1, tab2, tab3 = st.tabs(["📈 Stock Analysis", "🤖 AI Agent Performance", "💼 Portfolio"])

# Tab 1: Stock Analysis
with tab1:
    st.header('Stock Price Analysis')
    
    # Sidebar for user input
    st.sidebar.header('Chart Parameters')
    ticker = st.sidebar.text_input('Ticker', 'AAPL')
    time_period = st.sidebar.selectbox('Time Period', ['1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max'])
    chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
    indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20', 'RSI 14'])

    # Interval Mapping
    interval_mapping = {
        '1d': '1m', '5d': '5m', '1mo': '1h', '3mo': '1d',
        '6mo': '1d', '1y': '1wk', '5y': '1mo', 'max': '1mo',
    }

    # Update dashboard
    if st.sidebar.button('Update') or ticker:
        data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
        if data is not None:
            # Save to database
            save_stock_prices_to_db(ticker, data)
            
            data = process_data(data)
            data = add_technical_indicators(data)

            last_close, change, pct_change, high, low, volume = calculate_metrics(data)

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(f"{ticker} Last Price", f"${last_close:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            col2.metric('High', f"${high:.2f}")
            col3.metric('Low', f"${low:.2f}")
            col4.metric('Volume', f"{volume:,}")

            # Plot chart
            fig = go.Figure()
            if chart_type == 'Candlestick':
                fig.add_trace(go.Candlestick(
                    x=data['Datetime'], open=data['Open'],
                    high=data['High'], low=data['Low'], close=data['Close']
                ))
            else:
                fig = px.line(data, x='Datetime', y='Close')

            # Add indicators
            for indicator in indicators:
                if indicator == 'SMA 20':
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], name='SMA 20'))
                elif indicator == 'EMA 20':
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], name='EMA 20'))
                elif indicator == 'RSI 14':
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['RSI_14'], name='RSI 14', yaxis="y2"))

            fig.update_layout(
                title=f"{ticker} {time_period.upper()} Chart",
                xaxis_title='Time', yaxis_title='Price (USD)',
                yaxis2=dict(title='RSI', overlaying='y', side='right', showgrid=False),
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)

            # Historical data
            st.subheader('Historical Data')
            st.dataframe(data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])

# Tab 2: AI Agent Performance
with tab2:
    st.header('AI Trading Agent Performance')
    
    # Fetch agent positions
    positions_df = fetch_agent_positions()
    if not positions_df.empty:
        st.subheader('Current Agent Positions')
        st.dataframe(positions_df)
        
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
        st.dataframe(metrics_df)

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
            st.dataframe(agent_data[['symbol', 'amount', 'price', 'date']])

# Sidebar: Real-time prices
st.sidebar.header('Real-Time Stock Prices')
stock_symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT']
for symbol in stock_symbols:
    real_time_data = fetch_stock_data(symbol, '1d', '1m')
    if real_time_data is not None:
        real_time_data = process_data(real_time_data)
        last_price = real_time_data['Close'].iloc[-1]
        change = last_price - real_time_data['Open'].iloc[0]
        pct_change = (change / real_time_data['Open'].iloc[0]) * 100
        st.sidebar.metric(f"{symbol}", f"${last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")

st.sidebar.subheader('About')
st.sidebar.info('This dashboard integrates AI-Trader agent data with real-time stock analysis.')