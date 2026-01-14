# AI-Trader Docker Setup

This Docker Compose setup integrates the AI-Trader project with a Streamlit stock dashboard, both connected to a PostgreSQL database.

## 🏗️ Architecture

The setup consists of 4 services:

1. **PostgreSQL Database** (port 5432) - Shared data storage
2. **AI-Trader Web UI** (port 8888) - Original AI-Trader interface
3. **AI-Trader Agent** - Trading agent backend (runs in background)
4. **Streamlit Dashboard** (port 8501) - Enhanced stock analysis dashboard

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- API Keys:
  - OpenAI API Key
  - Alpha Vantage API Key
  - Jina AI API Key
  - Tushare Token (optional, for A-shares)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/HKUDS/AI-Trader.git
cd AI-Trader

# Create environment file
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your API keys:

```bash
# AI Model API
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_key_here

# Data Sources
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key
JINA_API_KEY=your_jina_api_key
TUSHARE_TOKEN=your_tushare_token  # Optional

# System Configuration
RUNTIME_ENV_PATH=/app/runtime_env.json
```

### 3. Create Required Directories

```bash
# Create directory structure
mkdir -p streamlit
mkdir -p docs
mkdir -p data/{agent_data,agent_data_astock,agent_data_crypto}
mkdir -p configs

# Copy Streamlit dashboard
cp stock_dashboard.py streamlit/
```

### 4. Launch Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

## 🌐 Access Points

After starting, access the services at:

- **AI-Trader Web UI**: http://localhost:8888
- **Streamlit Dashboard**: http://localhost:8501
- **PostgreSQL Database**: localhost:5432
  - Database: `trading_db`
  - User: `aitrader`
  - Password: `aitrader_password`

## 🎮 Usage

### Running the AI-Trader Agent

```bash
# Enter the agent container
docker-compose exec ai-trader-agent bash

# Prepare data (US stocks)
cd data
python get_daily_price.py
python merge_jsonl.py
cd ..

# Start MCP services
cd agent_tools
python start_mcp_services.py &
cd ..

# Run trading agent
python main.py configs/default_config.json
```

### Running A-Share Trading

```bash
# In agent container
cd data/A_stock

# Get A-share data
python get_daily_price_tushare.py
python merge_jsonl_tushare.py
cd ../..

# Run A-share agent
python main.py configs/astock_config.json
```

### Running Cryptocurrency Trading

```bash
# In agent container
cd data/crypto

# Get crypto data
python get_daily_price_crypto.py
python merge_crypto_jsonl.py
cd ../..

# Run crypto agent
python main.py configs/default_crypto_config.json
```

## 📊 Database Schema

The PostgreSQL database includes:

- **positions** - Agent trading positions
- **stock_prices** - Historical price data
- **agent_metrics** - Performance metrics
- **trading_logs** - Trading activity logs
- **watchlist** - Watched stock symbols

## 🔧 Configuration Files

### docker-compose.yml
Main orchestration file defining all services.

### Dockerfile.ui
Web UI container for AI-Trader interface.

### Dockerfile.agent
Agent container with all trading logic and tools.

### Dockerfile.streamlit
Streamlit dashboard container.

### init-db.sql
Database initialization script with schema.

## 🛠️ Management Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (clears database)
docker-compose down -v

# Rebuild containers
docker-compose build

# View logs
docker-compose logs -f [service_name]

# Execute commands in containers
docker-compose exec ai-trader-agent bash
docker-compose exec postgres psql -U aitrader -d trading_db

# Restart specific service
docker-compose restart streamlit-dashboard
```

## 📦 Data Persistence

Data is persisted in Docker volumes:

- **postgres_data** - Database files
- **./data** - Trading data and logs (mounted from host)
- **./configs** - Configuration files (mounted from host)

## 🔍 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U aitrader

# View database logs
docker-compose logs postgres
```

### Agent Not Running

```bash
# Check agent logs
docker-compose logs ai-trader-agent

# Verify MCP services are running
docker-compose exec ai-trader-agent ps aux | grep python
```

### Streamlit Dashboard Issues

```bash
# Restart Streamlit
docker-compose restart streamlit-dashboard

# Check Streamlit logs
docker-compose logs streamlit-dashboard
```

## 🔐 Security Notes

- Change default PostgreSQL password in production
- Use strong API keys
- Don't commit `.env` file to version control
- Restrict database port exposure in production

## 📝 Development

### Adding Custom Agents

1. Create agent file in `./agent/custom/`
2. Register in `main.py` AGENT_REGISTRY
3. Create config in `./configs/`
4. Rebuild containers:
   ```bash
   docker-compose build ai-trader-agent
   docker-compose up -d
   ```

### Modifying Database Schema

1. Edit `init-db.sql`
2. Rebuild database:
   ```bash
   docker-compose down -v
   docker-compose up -d postgres
   ```

## 🆘 Support

For issues:
- Check logs: `docker-compose logs`
- Review configuration files
- Consult main AI-Trader documentation
- Open GitHub issue

## 📄 License

MIT License - Same as AI-Trader project