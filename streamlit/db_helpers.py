# db_helpers.py - Helper functions for AI-Trader database operations

import os
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from models import (
    Agent, Prompt, AgentPrompt, Trade, Position, 
    StockPrice, AgentMetric, TradingLog, Watchlist, Base
)
import uuid


class DatabaseHelper:
    """Helper class for common database operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            database_url: PostgreSQL connection string. If None, uses DATABASE_URL env var.
        """
        if database_url is None:
            database_url = os.getenv(
                'DATABASE_URL',
                'postgresql://aitrader:aitrader_password@localhost:5432/trading_db'
            )
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    # ============================================================
    # Agent Operations
    # ============================================================
    
    def create_agent(
        self,
        signature: str,
        name: str,
        description: str = None,
        model_type: str = 'gpt-4',
        base_model: str = 'openai',
        initial_cash: float = 10000.00
    ) -> Agent:
        """Create a new trading agent"""
        session = self.get_session()
        try:
            agent = Agent(
                signature=signature,
                name=name,
                description=description,
                model_type=model_type,
                base_model=base_model,
                initial_cash=initial_cash,
                status='active'
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return agent
        finally:
            session.close()
    
    def get_agent(self, signature: str) -> Optional[Agent]:
        """Get agent by signature"""
        session = self.get_session()
        try:
            return session.query(Agent).filter(Agent.signature == signature).first()
        finally:
            session.close()
    
    def list_agents(self, status: str = None) -> List[Agent]:
        """List all agents, optionally filtered by status"""
        session = self.get_session()
        try:
            query = session.query(Agent)
            if status:
                query = query.filter(Agent.status == status)
            return query.all()
        finally:
            session.close()
    
    # ============================================================
    # Prompt Operations
    # ============================================================
    
    def create_prompt(
        self,
        name: str,
        prompt_text: str,
        description: str = None,
        prompt_type: str = 'trading',
        version: str = '1.0',
        parameters: Dict = None
    ) -> Prompt:
        """Create a new trading prompt"""
        session = self.get_session()
        try:
            prompt = Prompt(
                name=name,
                description=description,
                prompt_text=prompt_text,
                prompt_type=prompt_type,
                version=version,
                is_active=True,
                parameters=parameters or {}
            )
            session.add(prompt)
            session.commit()
            session.refresh(prompt)
            return prompt
        finally:
            session.close()
    
    def get_prompt(self, name: str, version: str = None) -> Optional[Prompt]:
        """Get prompt by name and version"""
        session = self.get_session()
        try:
            query = session.query(Prompt).filter(Prompt.name == name)
            if version:
                query = query.filter(Prompt.version == version)
            else:
                # Get latest version
                query = query.order_by(desc(Prompt.version))
            return query.first()
        finally:
            session.close()
    
    def list_prompts(self, prompt_type: str = None, active_only: bool = True) -> List[Prompt]:
        """List all prompts"""
        session = self.get_session()
        try:
            query = session.query(Prompt)
            if prompt_type:
                query = query.filter(Prompt.prompt_type == prompt_type)
            if active_only:
                query = query.filter(Prompt.is_active == True)
            return query.all()
        finally:
            session.close()
    
    # ============================================================
    # Agent-Prompt Assignment
    # ============================================================
    
    def assign_prompt_to_agent(
        self,
        agent_signature: str,
        prompt_name: str,
        prompt_version: str = None,
        priority: int = 0,
        custom_parameters: Dict = None
    ) -> AgentPrompt:
        """Assign a prompt to an agent"""
        session = self.get_session()
        try:
            # Get agent and prompt
            agent = session.query(Agent).filter(Agent.signature == agent_signature).first()
            if not agent:
                raise ValueError(f"Agent {agent_signature} not found")
            
            prompt_query = session.query(Prompt).filter(Prompt.name == prompt_name)
            if prompt_version:
                prompt_query = prompt_query.filter(Prompt.version == prompt_version)
            else:
                prompt_query = prompt_query.order_by(desc(Prompt.version))
            
            prompt = prompt_query.first()
            if not prompt:
                raise ValueError(f"Prompt {prompt_name} not found")
            
            # Create assignment
            agent_prompt = AgentPrompt(
                agent_id=agent.id,
                prompt_id=prompt.id,
                is_active=True,
                priority=priority,
                custom_parameters=custom_parameters or {}
            )
            session.add(agent_prompt)
            session.commit()
            session.refresh(agent_prompt)
            return agent_prompt
        finally:
            session.close()
    
    def get_agent_prompts(self, agent_signature: str, active_only: bool = True) -> List[Dict]:
        """Get all prompts assigned to an agent"""
        session = self.get_session()
        try:
            query = session.query(AgentPrompt, Prompt).join(Prompt).join(Agent)
            query = query.filter(Agent.signature == agent_signature)
            if active_only:
                query = query.filter(AgentPrompt.is_active == True)
            query = query.order_by(AgentPrompt.priority)
            
            results = []
            for ap, p in query.all():
                results.append({
                    'agent_prompt_id': ap.id,
                    'prompt_name': p.name,
                    'prompt_version': p.version,
                    'prompt_text': p.prompt_text,
                    'priority': ap.priority,
                    'custom_parameters': ap.custom_parameters,
                    'total_trades': ap.total_trades,
                    'successful_trades': ap.successful_trades,
                    'total_profit_loss': float(ap.total_profit_loss) if ap.total_profit_loss else 0.0
                })
            return results
        finally:
            session.close()
    
    # ============================================================
    # Trade Operations
    # ============================================================
    
    def record_trade(
        self,
        agent_signature: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        agent_prompt_id: int = None,
        reasoning: str = None,
        confidence_score: float = None,
        cash_before: float = None,
        cash_after: float = None,
        commission: float = 0.0
    ) -> Trade:
        """Record a new trade"""
        session = self.get_session()
        try:
            agent = session.query(Agent).filter(Agent.signature == agent_signature).first()
            if not agent:
                raise ValueError(f"Agent {agent_signature} not found")
            
            total_value = quantity * price
            
            trade = Trade(
                trade_uuid=uuid.uuid4(),
                agent_id=agent.id,
                agent_prompt_id=agent_prompt_id,
                symbol=symbol,
                action=action.lower(),
                quantity=quantity,
                price=price,
                total_value=total_value,
                executed_at=datetime.now(),
                market_date=datetime.now().date(),
                cash_before=cash_before,
                cash_after=cash_after,
                reasoning=reasoning,
                confidence_score=confidence_score,
                commission=commission,
                status='executed'
            )
            session.add(trade)
            session.commit()
            session.refresh(trade)
            
            # Update agent_prompt stats if provided
            if agent_prompt_id:
                ap = session.query(AgentPrompt).filter(AgentPrompt.id == agent_prompt_id).first()
                if ap:
                    ap.total_trades += 1
                    session.commit()
            
            return trade
        finally:
            session.close()
    
    def update_trade_outcome(
        self,
        trade_id: int,
        profit_loss: float,
        is_profitable: bool
    ):
        """Update trade outcome when position is closed"""
        session = self.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                raise ValueError(f"Trade {trade_id} not found")
            
            trade.profit_loss = profit_loss
            trade.is_profitable = is_profitable
            if trade.total_value > 0:
                trade.profit_loss_percentage = (profit_loss / trade.total_value) * 100
            
            # Update agent_prompt performance
            if trade.agent_prompt_id:
                ap = session.query(AgentPrompt).filter(
                    AgentPrompt.id == trade.agent_prompt_id
                ).first()
                if ap:
                    if is_profitable:
                        ap.successful_trades += 1
                    ap.total_profit_loss += profit_loss
            
            session.commit()
        finally:
            session.close()
    
    def get_agent_trades(
        self,
        agent_signature: str,
        limit: int = 100,
        symbol: str = None
    ) -> List[Trade]:
        """Get trades for an agent"""
        session = self.get_session()
        try:
            query = session.query(Trade).join(Agent)
            query = query.filter(Agent.signature == agent_signature)
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            query = query.order_by(desc(Trade.executed_at)).limit(limit)
            return query.all()
        finally:
            session.close()
    
    # ============================================================
    # Position Operations
    # ============================================================
    
    def update_position(
        self,
        agent_signature: str,
        symbol: str,
        amount: float,
        average_price: float,
        current_price: float,
        cash_balance: float,
        total_value: float,
        action: str = None
    ) -> Position:
        """Update or create position snapshot"""
        session = self.get_session()
        try:
            agent = session.query(Agent).filter(Agent.signature == agent_signature).first()
            if not agent:
                raise ValueError(f"Agent {agent_signature} not found")
            
            position = Position(
                agent_id=agent.id,
                date=datetime.now(),
                symbol=symbol,
                action=action,
                amount=amount,
                average_price=average_price,
                current_price=current_price,
                cash_balance=cash_balance,
                total_value=total_value
            )
            session.add(position)
            session.commit()
            session.refresh(position)
            return position
        finally:
            session.close()
    
    # ============================================================
    # Reporting
    # ============================================================
    
    def get_agent_summary(self, agent_signature: str) -> Dict:
        """Get comprehensive summary for an agent"""
        session = self.get_session()
        try:
            agent = session.query(Agent).filter(Agent.signature == agent_signature).first()
            if not agent:
                raise ValueError(f"Agent {agent_signature} not found")
            
            # Get trade statistics
            trades = session.query(Trade).filter(Trade.agent_id == agent.id).all()
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.is_profitable)
            total_profit = sum(t.profit_loss or 0 for t in trades)
            
            # Get latest position
            latest_position = session.query(Position).filter(
                Position.agent_id == agent.id
            ).order_by(desc(Position.date)).first()
            
            # Get active prompts
            active_prompts = self.get_agent_prompts(agent_signature, active_only=True)
            
            return {
                'agent': {
                    'signature': agent.signature,
                    'name': agent.name,
                    'model_type': agent.model_type,
                    'status': agent.status,
                    'initial_cash': float(agent.initial_cash)
                },
                'performance': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    'total_profit_loss': float(total_profit),
                    'current_cash': float(latest_position.cash_balance) if latest_position else float(agent.initial_cash),
                    'total_value': float(latest_position.total_value) if latest_position else float(agent.initial_cash)
                },
                'prompts': active_prompts
            }
        finally:
            session.close()


# ============================================================
# Usage Examples
# ============================================================

if __name__ == '__main__':
    db = DatabaseHelper()
    
    # Example 1: Create agents and prompts
    print("Creating agents and prompts...")
    
    try:
        agent1 = db.create_agent(
            signature='example-agent-001',
            name='Example Trading Bot',
            model_type='gpt-4',
            initial_cash=10000.00
        )
        print(f"✅ Created agent: {agent1.signature}")
    except Exception as e:
        print(f"Agent might already exist: {e}")
    
    try:
        prompt1 = db.create_prompt(
            name='Example Strategy',
            prompt_text='This is a sample trading strategy prompt...',
            prompt_type='trading',
            version='1.0',
            parameters={'risk_level': 'medium'}
        )
        print(f"✅ Created prompt: {prompt1.name}")
    except Exception as e:
        print(f"Prompt might already exist: {e}")
    
    # Example 2: Assign prompt to agent
    print("\nAssigning prompt to agent...")
    try:
        assignment = db.assign_prompt_to_agent(
            agent_signature='example-agent-001',
            prompt_name='Example Strategy',
            priority=1
        )
        print(f"✅ Assigned prompt to agent")
    except Exception as e:
        print(f"Assignment error: {e}")
    
    # Example 3: Record a trade
    print("\nRecording a trade...")
    try:
        trade = db.record_trade(
            agent_signature='example-agent-001',
            symbol='AAPL',
            action='buy',
            quantity=10.0,
            price=150.00,
            reasoning='Strong momentum',
            confidence_score=0.85,
            cash_before=10000.00,
            cash_after=8500.00
        )
        print(f"✅ Recorded trade: {trade.trade_uuid}")
    except Exception as e:
        print(f"Trade error: {e}")
    
    # Example 4: Get agent summary
    print("\nGetting agent summary...")
    try:
        summary = db.get_agent_summary('example-agent-001')
        print(f"✅ Agent Summary:")
        print(f"   Total Trades: {summary['performance']['total_trades']}")
        print(f"   Win Rate: {summary['performance']['win_rate']:.2f}%")
        print(f"   Total P&L: ${summary['performance']['total_profit_loss']:.2f}")
    except Exception as e:
        print(f"Summary error: {e}")