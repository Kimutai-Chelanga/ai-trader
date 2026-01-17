import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
from sqlalchemy import text

# SET PAGE CONFIG FIRST - BEFORE ANY OTHER STREAMLIT COMMAND
st.set_page_config(layout='wide', page_title='🤖 AI-Trader Dashboard', page_icon='📈')

# Import our database helper
try:
    from db_helpers import DatabaseHelper
except ImportError:
    st.error("db_helpers.py not found. Please ensure it's in the same directory.")
    st.stop()

load_dotenv()


# Initialize database helper
@st.cache_resource
def get_db_helper():
    """Get cached database helper instance"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/trading_db')
    return DatabaseHelper(database_url)

db = get_db_helper()

# NASDAQ 100 symbols
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

# ============================================================
# Data Fetching Functions
# ============================================================

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_data_alpha_vantage(ticker, interval='5min'):
    """Fetch stock data from Alpha Vantage API"""
    api_key = os.getenv('ALPHAADVANTAGE_API_KEY')
    if not api_key:
        st.error("ALPHAADVANTAGE_API_KEY not found in environment")
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
        
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': function,
            'symbol': ticker,
            'apikey': api_key,
            'outputsize': 'full'
        }
        
        if function == 'TIME_SERIES_INTRADAY':
            params['interval'] = interval
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Error Message' in data:
            st.error(f"Error: {data['Error Message']}")
            return None
        
        if 'Note' in data:
            st.warning("API rate limit reached. Please wait a moment.")
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
        st.error(f"Error fetching data: {e}")
        return None

def save_stock_prices_to_db(ticker, data, market='us'):
    """Save stock price data to database"""
    session = db.get_session()
    try:
        from models import StockPrice
        for index, row in data.iterrows():
            stock_price = StockPrice(
                symbol=ticker,
                date=index,
                open_price=row['Open'],
                high_price=row['High'],
                low_price=row['Low'],
                close_price=row['Close'],
                volume=int(row['Volume']),
                market=market
            )
            # Merge (upsert)
            session.merge(stock_price)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.warning(f"Database save error: {e}")
        return False
    finally:
        session.close()

@st.cache_data(ttl=60)
def fetch_agent_positions():
    """Fetch latest agent positions from database view"""
    session = db.get_session()
    try:
        query = text("""
            SELECT 
                agent_signature,
                agent_name,
                symbol,
                amount,
                price,
                average_price,
                cash_balance,
                total_value,
                date
            FROM latest_positions
            ORDER BY agent_signature, date DESC
        """)
        result = session.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df
    except Exception as e:
        st.warning(f"Error fetching positions: {e}")
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=60)
def fetch_agent_performance_summary():
    """Fetch agent performance summary from database view"""
    session = db.get_session()
    try:
        query = text("""
            SELECT 
                signature,
                name,
                status,
                total_trades,
                winning_trades,
                win_rate_percentage,
                total_profit_loss,
                peak_value,
                worst_drawdown,
                avg_sharpe_ratio,
                prompts_used
            FROM agent_performance_summary
            ORDER BY total_profit_loss DESC NULLS LAST
        """)
        result = session.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df
    except Exception as e:
        st.warning(f"Error fetching performance: {e}")
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=60)
def fetch_agent_metrics_history(agent_signature=None, days=30):
    """Fetch agent metrics history"""
    session = db.get_session()
    try:
        if agent_signature:
            # FIXED: Corrected interval syntax
            query = text("""
                SELECT 
                    a.signature as agent_signature,
                    a.name as agent_name,
                    m.date,
                    m.total_value,
                    m.cash_balance,
                    m.portfolio_value,
                    m.daily_return,
                    m.cumulative_return,
                    m.sharpe_ratio,
                    m.trades_count
                FROM agent_metrics m
                JOIN agents a ON m.agent_id = a.id
                WHERE a.signature = :signature
                    AND m.date >= CURRENT_DATE - :days * INTERVAL '1 day'
                ORDER BY m.date DESC
            """)
            result = session.execute(query, {"signature": agent_signature, "days": days})
        else:
            # FIXED: Corrected interval syntax
            query = text("""
                SELECT 
                    a.signature as agent_signature,
                    a.name as agent_name,
                    m.date,
                    m.total_value,
                    m.cash_balance,
                    m.portfolio_value,
                    m.daily_return,
                    m.cumulative_return,
                    m.sharpe_ratio,
                    m.trades_count
                FROM agent_metrics m
                JOIN agents a ON m.agent_id = a.id
                WHERE m.date >= CURRENT_DATE - :days * INTERVAL '1 day'
                ORDER BY a.signature, m.date DESC
            """)
            result = session.execute(query, {"days": days})
        
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df
    except Exception as e:
        st.warning(f"Error fetching metrics: {e}")
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=60)
def fetch_recent_trades(agent_signature=None, limit=50):
    """Fetch recent trades"""
    session = db.get_session()
    try:
        if agent_signature:
            query = text("""
                SELECT 
                    a.signature as agent_signature,
                    a.name as agent_name,
                    t.symbol,
                    t.action,
                    t.quantity,
                    t.price,
                    t.total_value,
                    t.executed_at,
                    t.profit_loss,
                    t.is_profitable,
                    t.confidence_score,
                    t.reasoning
                FROM trades t
                JOIN agents a ON t.agent_id = a.id
                WHERE a.signature = :signature
                ORDER BY t.executed_at DESC
                LIMIT :limit
            """)
            result = session.execute(query, {"signature": agent_signature, "limit": limit})
        else:
            query = text("""
                SELECT 
                    a.signature as agent_signature,
                    a.name as agent_name,
                    t.symbol,
                    t.action,
                    t.quantity,
                    t.price,
                    t.total_value,
                    t.executed_at,
                    t.profit_loss,
                    t.is_profitable,
                    t.confidence_score,
                    t.reasoning
                FROM trades t
                JOIN agents a ON t.agent_id = a.id
                ORDER BY t.executed_at DESC
                LIMIT :limit
            """)
            result = session.execute(query, {"limit": limit})
        
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df
    except Exception as e:
        st.warning(f"Error fetching trades: {e}")
        return pd.DataFrame()
    finally:
        session.close()

@st.cache_data(ttl=60)
def fetch_prompt_performance():
    """Fetch prompt performance from database view"""
    session = db.get_session()
    try:
        query = text("""
            SELECT 
                prompt_name,
                version,
                agents_using,
                total_trades,
                successful_trades,
                success_rate_percentage,
                total_profit_loss,
                avg_profit_loss_per_agent
            FROM prompt_performance
            ORDER BY total_profit_loss DESC NULLS LAST
        """)
        result = session.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df
    except Exception as e:
        st.warning(f"Error fetching prompt performance: {e}")
        return pd.DataFrame()
    finally:
        session.close()

# ============================================================
# Technical Indicators
# ============================================================

def add_technical_indicators(data):
    """Add technical indicators to price data"""
    if len(data) >= 20:
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
    if len(data) >= 50:
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
    if len(data) >= 14:
        # RSI calculation
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI_14'] = 100 - (100 / (1 + rs))
    return data

def calculate_metrics(data):
    """Calculate basic price metrics"""
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = data['High'].max()
    low = data['Low'].min()
    volume = data['Volume'].sum()
    return last_close, change, pct_change, high, low, volume

# ============================================================
# Streamlit Dashboard
# ============================================================


# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .positive {
        color: #00cc00;
    }
    .negative {
        color: #ff0000;
    }
</style>
""", unsafe_allow_html=True)

st.title('🤖 AI-Trader Real-Time Dashboard')
st.markdown('*Multi-Agent Trading System with AI-Powered Strategies*')

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Stock Analysis", 
    "🤖 Agent Performance", 
    "💼 Portfolio", 
    "📊 Trading History",
    "🎯 Strategy Performance"
])

# ============================================================
# TAB 1: Stock Analysis
# ============================================================
with tab1:
    st.header('📈 Real-Time Stock Analysis')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ticker = st.selectbox('Select Stock Symbol', all_nasdaq_100_symbols, index=0)
    
    with col2:
        interval_options = {
            '1 Minute': '1min',
            '5 Minutes': '5min',
            '15 Minutes': '15min',
            '30 Minutes': '30min',
            '1 Hour': '60min',
            'Daily': 'daily'
        }
        interval_label = st.selectbox('Time Interval', list(interval_options.keys()), index=1)
        interval = interval_options[interval_label]
    
    col3, col4 = st.columns(2)
    with col3:
        chart_type = st.selectbox('Chart Type', ['Candlestick', 'Line', 'Area'])
    with col4:
        indicators = st.multiselect(
            'Technical Indicators', 
            ['SMA 20', 'SMA 50', 'EMA 20', 'RSI 14'],
            default=['SMA 20']
        )
    
    if st.button('🔄 Fetch & Update Data', type='primary'):
        with st.spinner(f'Fetching {ticker} data...'):
            data = fetch_stock_data_alpha_vantage(ticker, interval)
            
            if data is not None and not data.empty:
                # Save to database
                if save_stock_prices_to_db(ticker, data):
                    st.success(f'✅ Saved {len(data)} records to database')
                
                # Add technical indicators
                data = add_technical_indicators(data)
                
                # Calculate metrics
                last_close, change, pct_change, high, low, volume = calculate_metrics(data)
                
                # Display metrics
                metric_cols = st.columns(5)
                with metric_cols[0]:
                    st.metric(
                        f"{ticker} Price", 
                        f"${last_close:.2f}", 
                        f"{change:+.2f} ({pct_change:+.2f}%)"
                    )
                with metric_cols[1]:
                    st.metric('High', f"${high:.2f}")
                with metric_cols[2]:
                    st.metric('Low', f"${low:.2f}")
                with metric_cols[3]:
                    st.metric('Volume', f"{int(volume):,}")
                with metric_cols[4]:
                    avg_volume = data['Volume'].mean()
                    st.metric('Avg Volume', f"{int(avg_volume):,}")
                
                # Reset index for plotting
                data_plot = data.reset_index()
                data_plot.rename(columns={'index': 'Datetime'}, inplace=True)
                
                # Main price chart
                fig = go.Figure()
                
                if chart_type == 'Candlestick':
                    fig.add_trace(go.Candlestick(
                        x=data_plot['Datetime'],
                        open=data_plot['Open'],
                        high=data_plot['High'],
                        low=data_plot['Low'],
                        close=data_plot['Close'],
                        name=ticker
                    ))
                elif chart_type == 'Line':
                    fig.add_trace(go.Scatter(
                        x=data_plot['Datetime'],
                        y=data_plot['Close'],
                        name=ticker,
                        mode='lines',
                        line=dict(width=2)
                    ))
                else:  # Area
                    fig.add_trace(go.Scatter(
                        x=data_plot['Datetime'],
                        y=data_plot['Close'],
                        name=ticker,
                        mode='lines',
                        fill='tozeroy',
                        line=dict(width=2)
                    ))
                
                # Add technical indicators
                if 'SMA 20' in indicators and 'SMA_20' in data_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=data_plot['Datetime'], 
                        y=data_plot['SMA_20'], 
                        name='SMA 20',
                        line=dict(dash='dash', width=1.5)
                    ))
                if 'SMA 50' in indicators and 'SMA_50' in data_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=data_plot['Datetime'], 
                        y=data_plot['SMA_50'], 
                        name='SMA 50',
                        line=dict(dash='dot', width=1.5)
                    ))
                if 'EMA 20' in indicators and 'EMA_20' in data_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=data_plot['Datetime'], 
                        y=data_plot['EMA_20'], 
                        name='EMA 20',
                        line=dict(dash='dashdot', width=1.5)
                    ))
                
                fig.update_layout(
                    title=f"{ticker} {interval_label} Chart",
                    xaxis_title='Time',
                    yaxis_title='Price (USD)',
                    height=600,
                    hovermode='x unified',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # RSI chart
                if 'RSI 14' in indicators and 'RSI_14' in data_plot.columns:
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(
                        x=data_plot['Datetime'], 
                        y=data_plot['RSI_14'], 
                        name='RSI 14',
                        line=dict(width=2, color='purple')
                    ))
                    fig_rsi.add_hline(
                        y=70, line_dash="dash", line_color="red", 
                        annotation_text="Overbought (70)"
                    )
                    fig_rsi.add_hline(
                        y=30, line_dash="dash", line_color="green", 
                        annotation_text="Oversold (30)"
                    )
                    fig_rsi.update_layout(
                        title='RSI Indicator',
                        xaxis_title='Time',
                        yaxis_title='RSI',
                        height=300,
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_rsi, use_container_width=True)
                
                # Data table
                with st.expander('📊 View Historical Data'):
                    display_data = data_plot[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']].tail(100)
                    st.dataframe(display_data, use_container_width=True, height=400)

# ============================================================
# TAB 2: Agent Performance
# ============================================================
with tab2:
    st.header('🤖 AI Agent Performance Overview')
    
    # Fetch agent performance
    perf_df = fetch_agent_performance_summary()
    
    if not perf_df.empty:
        # Summary metrics
        st.subheader('📊 Overall Performance')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_agents = len(perf_df)
            active_agents = len(perf_df[perf_df['status'] == 'active'])
            st.metric('Total Agents', total_agents, f"{active_agents} active")
        with col2:
            total_trades = perf_df['total_trades'].sum()
            st.metric('Total Trades', f"{int(total_trades):,}")
        with col3:
            total_pnl = perf_df['total_profit_loss'].sum()
            pnl_color = '🟢' if total_pnl >= 0 else '🔴'
            st.metric('Total P&L', f"{pnl_color} ${total_pnl:,.2f}")
        with col4:
            avg_win_rate = perf_df['win_rate_percentage'].mean()
            st.metric('Avg Win Rate', f"{avg_win_rate:.1f}%")
        
        # Agent performance table
        st.subheader('🏆 Agent Leaderboard')
        
        # Format the dataframe for display
        display_df = perf_df.copy()
        display_df['total_profit_loss'] = display_df['total_profit_loss'].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
        )
        display_df['win_rate_percentage'] = display_df['win_rate_percentage'].apply(
            lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"
        )
        display_df['avg_sharpe_ratio'] = display_df['avg_sharpe_ratio'].apply(
            lambda x: f"{x:.4f}" if pd.notnull(x) else "N/A"
        )
        
        st.dataframe(
            display_df[['name', 'status', 'total_trades', 'winning_trades', 
                       'win_rate_percentage', 'total_profit_loss', 'avg_sharpe_ratio', 'prompts_used']],
            use_container_width=True,
            height=400
        )
        
        # Performance charts
        col1, col2 = st.columns(2)
        
        with col1:
            # P&L by agent
            fig_pnl = px.bar(
                perf_df,
                x='name',
                y='total_profit_loss',
                title='Profit/Loss by Agent',
                color='total_profit_loss',
                color_continuous_scale=['red', 'yellow', 'green']
            )
            fig_pnl.update_layout(template='plotly_white')
            st.plotly_chart(fig_pnl, use_container_width=True)
        
        with col2:
            # Win rate comparison
            fig_wr = px.bar(
                perf_df,
                x='name',
                y='win_rate_percentage',
                title='Win Rate by Agent',
                color='win_rate_percentage',
                color_continuous_scale='Blues'
            )
            fig_wr.update_layout(template='plotly_white')
            st.plotly_chart(fig_wr, use_container_width=True)
        
        # Agent metrics history
        st.subheader('📈 Performance Over Time')
        
        selected_agent = st.selectbox(
            'Select Agent',
            perf_df['signature'].tolist(),
            format_func=lambda x: perf_df[perf_df['signature'] == x]['name'].iloc[0]
        )
        
        metrics_df = fetch_agent_metrics_history(selected_agent, days=30)
        
        if not metrics_df.empty:
            # Portfolio value over time
            fig_value = px.line(
                metrics_df,
                x='date',
                y='total_value',
                title=f'Portfolio Value Over Time - {metrics_df["agent_name"].iloc[0]}',
                markers=True
            )
            fig_value.update_layout(template='plotly_white')
            st.plotly_chart(fig_value, use_container_width=True)
            
            # Returns chart
            col1, col2 = st.columns(2)
            with col1:
                fig_daily = px.bar(
                    metrics_df,
                    x='date',
                    y='daily_return',
                    title='Daily Returns',
                    color='daily_return',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                fig_daily.update_layout(template='plotly_white')
                st.plotly_chart(fig_daily, use_container_width=True)
            
            with col2:
                fig_cum = px.line(
                    metrics_df,
                    x='date',
                    y='cumulative_return',
                    title='Cumulative Return',
                    markers=True
                )
                fig_cum.update_layout(template='plotly_white')
                st.plotly_chart(fig_cum, use_container_width=True)
    else:
        st.info('📭 No agent performance data available. Start trading agents to see metrics.')

# ============================================================
# TAB 3: Portfolio
# ============================================================
with tab3:
    st.header('💼 Current Portfolio Positions')
    
    positions_df = fetch_agent_positions()
    
    if not positions_df.empty:
        # Group by agent
        agents = positions_df['agent_signature'].unique()
        
        for agent_sig in agents:
            agent_data = positions_df[positions_df['agent_signature'] == agent_sig]
            agent_name = agent_data['agent_name'].iloc[0]
            
            with st.expander(f"🤖 {agent_name} ({agent_sig})", expanded=True):
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    cash = agent_data['cash_balance'].iloc[0]
                    st.metric('Cash Balance', f"${cash:,.2f}")
                
                with col2:
                    holdings_value = (agent_data['amount'] * agent_data['price']).sum()
                    st.metric('Holdings Value', f"${holdings_value:,.2f}")
                
                with col3:
                    total_value = agent_data['total_value'].iloc[0]
                    st.metric('Total Portfolio', f"${total_value:,.2f}")
                
                with col4:
                    num_positions = len(agent_data)
                    st.metric('Positions', num_positions)
                
                # Position details
                st.markdown('#### Current Holdings')
                display_positions = agent_data[['symbol', 'amount', 'average_price', 'price', 'date']].copy()
                display_positions['current_value'] = display_positions['amount'] * display_positions['price']
                display_positions['unrealized_pnl'] = (
                    display_positions['price'] - display_positions['average_price']
                ) * display_positions['amount']
                display_positions['pnl_pct'] = (
                    (display_positions['price'] - display_positions['average_price']) / 
                    display_positions['average_price'] * 100
                )
                
                st.dataframe(display_positions, use_container_width=True)
                
                # Portfolio allocation pie chart
                fig_pie = px.pie(
                    display_positions,
                    values='current_value',
                    names='symbol',
                    title='Portfolio Allocation'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info('📭 No portfolio positions found. Execute trades to see positions.')

# ============================================================
# TAB 4: Trading History
# ============================================================
# ============================================================
# TAB 4: Trading History
# ============================================================
with tab4:
    st.header('📊 Recent Trading Activity')
    
    col1, col2 = st.columns([2, 1])
    with col1:
        agent_filter = st.selectbox(
            'Filter by Agent',
            ['All Agents'] + fetch_agent_performance_summary()['signature'].tolist()
        )
    with col2:
        limit = st.number_input('Number of trades', min_value=10, max_value=500, value=50)
    
    if agent_filter == 'All Agents':
        trades_df = fetch_recent_trades(limit=limit)
    else:
        trades_df = fetch_recent_trades(agent_signature=agent_filter, limit=limit)
    
    if not trades_df.empty:
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_trades = len(trades_df)
            st.metric('Total Trades', total_trades)
        
        with col2:
            buy_trades = len(trades_df[trades_df['action'] == 'buy'])
            sell_trades = len(trades_df[trades_df['action'] == 'sell'])
            st.metric('Buy/Sell', f"{buy_trades}/{sell_trades}")
        
        with col3:
            profitable_trades = trades_df['is_profitable'].sum()
            if total_trades > 0:
                win_rate = (profitable_trades / total_trades) * 100
                st.metric('Win Rate', f"{win_rate:.1f}%")
            else:
                st.metric('Win Rate', "N/A")
        
        with col4:
            total_pnl = trades_df['profit_loss'].sum()
            st.metric('Total P&L', f"${total_pnl:,.2f}")
        
        # Trade history table
        st.subheader('📋 Trade Details')
        
        display_trades = trades_df.copy()
        display_trades['executed_at'] = pd.to_datetime(display_trades['executed_at']).dt.strftime('%Y-%m-%d %H:%M')
        display_trades['profit_loss'] = display_trades['profit_loss'].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else "Open"
        )
        display_trades['confidence_score'] = display_trades['confidence_score'].apply(
            lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A"
        )
        
        st.dataframe(
            display_trades[[
                'executed_at', 'agent_name', 'symbol', 'action', 
                'quantity', 'price', 'total_value', 'profit_loss', 
                'confidence_score'
            ]],
            use_container_width=True,
            height=500
        )
        
        # Trade analysis charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Trades by symbol
            symbol_counts = trades_df['symbol'].value_counts().head(10)
            fig_symbols = px.bar(
                x=symbol_counts.index,
                y=symbol_counts.values,
                title='Most Traded Symbols',
                labels={'x': 'Symbol', 'y': 'Number of Trades'}
            )
            fig_symbols.update_layout(template='plotly_white')
            st.plotly_chart(fig_symbols, use_container_width=True)
        
        with col2:
            # P&L distribution
            closed_trades = trades_df[trades_df['profit_loss'].notnull()]
            if not closed_trades.empty:
                fig_pnl = px.histogram(
                    closed_trades,
                    x='profit_loss',
                    title='P&L Distribution',
                    nbins=30,
                    color_discrete_sequence=['steelblue']
                )
                fig_pnl.update_layout(template='plotly_white')
                st.plotly_chart(fig_pnl, use_container_width=True)
        
        # Trade reasoning (expandable)
        # FIXED: F-string formatting error
        with st.expander('🧠 View Trade Reasoning'):
            for idx, trade in trades_df.head(10).iterrows():
                if pd.notnull(trade['reasoning']):
                    confidence_text = f"{trade['confidence_score']:.2%}" if pd.notnull(trade['confidence_score']) else 'N/A'
                    st.markdown(f"""
                    **{trade['executed_at']}** - {trade['agent_name']}  
                    Action: **{trade['action'].upper()}** {trade['quantity']} shares of **{trade['symbol']}** @ ${trade['price']:.2f}  
                    Reasoning: {trade['reasoning']}  
                    Confidence: {confidence_text}
                    """)
                    st.divider()
    else:
        st.info('📭 No trade history available yet.')

# ============================================================
# TAB 5: Strategy Performance
# ============================================================
with tab5:
    st.header('🎯 Trading Strategy Performance')
    
    prompt_perf_df = fetch_prompt_performance()
    
    if not prompt_perf_df.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_strategies = len(prompt_perf_df)
            st.metric('Active Strategies', total_strategies)
        
        with col2:
            total_agents_using = prompt_perf_df['agents_using'].sum()
            st.metric('Agent Assignments', int(total_agents_using))
        
        with col3:
            total_strategy_trades = prompt_perf_df['total_trades'].sum()
            st.metric('Total Strategy Trades', int(total_strategy_trades))
        
        with col4:
            total_strategy_pnl = prompt_perf_df['total_profit_loss'].sum()
            st.metric('Total Strategy P&L', f"${total_strategy_pnl:,.2f}")
        
        # Strategy leaderboard
        st.subheader('🏆 Strategy Leaderboard')
        
        display_prompt_df = prompt_perf_df.copy()
        display_prompt_df['success_rate_percentage'] = display_prompt_df['success_rate_percentage'].apply(
            lambda x: f"{x:.2f}%" if pd.notnull(x) else "0.00%"
        )
        display_prompt_df['total_profit_loss'] = display_prompt_df['total_profit_loss'].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
        )
        display_prompt_df['avg_profit_loss_per_agent'] = display_prompt_df['avg_profit_loss_per_agent'].apply(
            lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
        )
        
        st.dataframe(
            display_prompt_df[[
                'prompt_name', 'version', 'agents_using', 'total_trades',
                'successful_trades', 'success_rate_percentage', 'total_profit_loss',
                'avg_profit_loss_per_agent'
            ]],
            use_container_width=True,
            height=400
        )
        
        # Strategy comparison charts
        col1, col2 = st.columns(2)
        
        with col1:
            # P&L by strategy
            fig_strategy_pnl = px.bar(
                prompt_perf_df,
                x='prompt_name',
                y='total_profit_loss',
                title='Strategy P&L Comparison',
                color='total_profit_loss',
                color_continuous_scale=['red', 'yellow', 'green']
            )
            fig_strategy_pnl.update_layout(template='plotly_white')
            st.plotly_chart(fig_strategy_pnl, use_container_width=True)
        
        with col2:
            # Success rate comparison
            fig_success = px.bar(
                prompt_perf_df,
                x='prompt_name',
                y='success_rate_percentage',
                title='Strategy Success Rate',
                color='success_rate_percentage',
                color_continuous_scale='Greens'
            )
            fig_success.update_layout(template='plotly_white')
            st.plotly_chart(fig_success, use_container_width=True)
        
        # Agent-Strategy matrix
        st.subheader('🔗 Agent-Strategy Assignments')
        
        session = db.get_session()
        try:
            query = text("""
                SELECT 
                    a.name as agent_name,
                    p.name as prompt_name,
                    ap.priority,
                    ap.total_trades,
                    ap.successful_trades,
                    ap.total_profit_loss
                FROM agent_prompts ap
                JOIN agents a ON ap.agent_id = a.id
                JOIN prompts p ON ap.prompt_id = p.id
                WHERE ap.is_active = true
                ORDER BY a.name, ap.priority
            """)
            result = session.execute(query)
            assignments_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            if not assignments_df.empty:
                # Format for display
                display_assignments = assignments_df.copy()
                display_assignments['total_profit_loss'] = display_assignments['total_profit_loss'].apply(
                    lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"
                )
                
                st.dataframe(display_assignments, use_container_width=True, height=400)
                
                # Heatmap of performance
                if len(assignments_df) > 0:
                    pivot_data = assignments_df.pivot_table(
                        index='agent_name',
                        columns='prompt_name',
                        values='total_profit_loss',
                        fill_value=0
                    )
                    
                    fig_heatmap = px.imshow(
                        pivot_data,
                        title='Agent-Strategy Performance Heatmap (P&L)',
                        color_continuous_scale='RdYlGn',
                        aspect='auto'
                    )
                    fig_heatmap.update_layout(template='plotly_white')
                    st.plotly_chart(fig_heatmap, use_container_width=True)
        except Exception as e:
            st.warning(f"Error loading agent-strategy assignments: {e}")
        finally:
            session.close()
    else:
        st.info('📭 No strategy performance data available yet.')

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.header('🚀 Quick Actions')
    
    # Database status
    st.subheader('📊 System Status')
    try:
        session = db.get_session()
        result = session.execute(text("SELECT COUNT(*) FROM agents"))
        agent_count = result.scalar()
        session.close()
        st.success(f'✅ Database Connected')
        st.info(f'Active Agents: {agent_count}')
    except Exception as e:
        st.error('❌ Database Connection Failed')
        st.exception(e)
    
    st.divider()
    
    # Quick stock lookup
    st.subheader('📈 Quick Stock Lookup')
    quick_symbols = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX']
    
    for symbol in quick_symbols:
        if st.button(f"📊 {symbol}", key=f"quick_{symbol}", use_container_width=True):
            st.session_state['selected_ticker'] = symbol
            st.rerun()
    
    st.divider()
    
    # Refresh data
    if st.button('🔄 Refresh All Data', use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # About
    st.subheader('ℹ️ About')
    st.info("""
    **AI-Trader Dashboard v2.0**
    
    Multi-agent trading system with:
    - Real-time stock data (Alpha Vantage)
    - AI-powered trading strategies
    - Performance analytics
    - Portfolio tracking
    - Strategy optimization
    
    Built with Streamlit, PostgreSQL, and SQLAlchemy
    """)