#!/bin/bash
# AI-Trader Docker Setup Script

set -e

echo "🚀 AI-Trader Docker Setup"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p streamlit
mkdir -p docs
mkdir -p data/agent_data
mkdir -p data/agent_data_astock
mkdir -p data/agent_data_crypto
mkdir -p data/A_stock/A_stock_data
mkdir -p data/crypto/coin
mkdir -p configs
mkdir -p agent/base_agent
mkdir -p agent/base_agent_astock
mkdir -p agent/base_agent_crypto
mkdir -p prompts
mkdir -p tools
mkdir -p agent_tools

echo -e "${GREEN}✅ Directory structure created${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created. Please edit it with your API keys.${NC}"
    else
        echo -e "${YELLOW}⚠️  .env.example not found. Creating template...${NC}"
        cat > .env << 'EOF'
# AI Model API Configuration
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_key_here

# Data Source Configuration
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key
JINA_API_KEY=your_jina_api_key
TUSHARE_TOKEN=your_tushare_token

# System Configuration
RUNTIME_ENV_PATH=/app/runtime_env.json

# Service Port Configuration
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003
CRYPTO_HTTP_PORT=8005

# AI Agent Configuration
AGENT_MAX_STEP=30
EOF
        echo -e "${GREEN}✅ .env template created. Please edit it with your API keys.${NC}"
    fi
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env file with your API keys before continuing!${NC}"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
fi

# Copy stock dashboard if it exists
if [ -f stock_dashboard.py ]; then
    echo "📋 Copying stock dashboard to streamlit directory..."
    cp stock_dashboard.py streamlit/
    echo -e "${GREEN}✅ Stock dashboard copied${NC}"
else
    echo -e "${YELLOW}⚠️  stock_dashboard.py not found in root. Make sure it's in the streamlit/ directory.${NC}"
fi
echo ""

# Build Docker images
echo "🔨 Building Docker images..."
echo "This may take several minutes on first run..."
echo ""

if docker-compose build; then
    echo -e "${GREEN}✅ Docker images built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build Docker images${NC}"
    exit 1
fi
echo ""

# Start services
echo "🚀 Starting services..."
if docker-compose up -d; then
    echo -e "${GREEN}✅ Services started successfully${NC}"
else
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""

# Display access information
echo "🌐 Access Points:"
echo "================================"
echo -e "${GREEN}AI-Trader Web UI:${NC}      http://localhost:8888"
echo -e "${GREEN}Streamlit Dashboard:${NC}   http://localhost:8501"
echo -e "${GREEN}PostgreSQL Database:${NC}   localhost:5432"
echo ""
echo "Database Credentials:"
echo "  - Database: trading_db"
echo "  - User: aitrader"
echo "  - Password: aitrader_password"
echo ""

# Display next steps
echo "📝 Next Steps:"
echo "================================"
echo "1. Access Streamlit Dashboard at http://localhost:8501"
echo "2. To run the AI trading agent:"
echo "   docker-compose exec ai-trader-agent bash"
echo "   cd data && python get_daily_price.py && python merge_jsonl.py"
echo "   cd ../agent_tools && python start_mcp_services.py &"
echo "   cd .. && python main.py configs/default_config.json"
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "4. Stop services:"
echo "   docker-compose down"
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"