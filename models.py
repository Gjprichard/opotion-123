from datetime import datetime
from app import db

class OptionData(db.Model):
    """Model to store options market data"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    expiration_date = db.Column(db.Date, nullable=False, index=True)
    strike_price = db.Column(db.Float, nullable=False)
    option_type = db.Column(db.String(4), nullable=False)  # 'call' or 'put'
    underlying_price = db.Column(db.Float, nullable=False)
    option_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=True)
    open_interest = db.Column(db.Integer, nullable=True)
    implied_volatility = db.Column(db.Float, nullable=True)
    delta = db.Column(db.Float, nullable=True)
    gamma = db.Column(db.Float, nullable=True)
    theta = db.Column(db.Float, nullable=True)
    vega = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f'<OptionData {self.symbol} {self.option_type} {self.strike_price} {self.expiration_date}>'

class RiskIndicator(db.Model):
    """Model to store calculated risk indicators"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_period = db.Column(db.String(10), default='4h', nullable=False, index=True)  # 新增: '15m', '1h', '4h', '1d', '7d', '30d'
    volaxivity = db.Column(db.Float, nullable=True)  # Custom volatility index
    volatility_skew = db.Column(db.Float, nullable=True)
    put_call_ratio = db.Column(db.Float, nullable=True)
    market_sentiment = db.Column(db.String(20), nullable=True)  # 'risk-on' or 'risk-off'
    reflexivity_indicator = db.Column(db.Float, nullable=True)  # Measure of market feedback loop intensity
    
    # Crypto-specific risk indicators
    funding_rate = db.Column(db.Float, nullable=True)  # Funding rate for perpetual futures (crypto-specific)
    liquidation_risk = db.Column(db.Float, nullable=True)  # Risk of cascading liquidations (crypto-specific) 
    
    def __repr__(self):
        return f'<RiskIndicator {self.symbol} {self.time_period} {self.timestamp}>'

class Alert(db.Model):
    """Model to store generated alerts"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_period = db.Column(db.String(10), default='4h', nullable=False)  # 新增时间周期
    alert_type = db.Column(db.String(20), nullable=False)  # 'attention', 'warning', 'severe'
    message = db.Column(db.Text, nullable=False)
    indicator = db.Column(db.String(50), nullable=False)  # Which indicator triggered the alert
    value = db.Column(db.Float, nullable=False)  # Current value of the indicator
    threshold = db.Column(db.Float, nullable=False)  # Threshold that was crossed
    is_acknowledged = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Alert {self.symbol} {self.alert_type} {self.time_period} {self.timestamp}>'

class AlertThreshold(db.Model):
    """Model to store alert threshold settings"""
    id = db.Column(db.Integer, primary_key=True)
    indicator = db.Column(db.String(50), nullable=False)
    time_period = db.Column(db.String(10), default='4h', nullable=False)  # 新增时间周期
    attention_threshold = db.Column(db.Float, nullable=False)
    warning_threshold = db.Column(db.Float, nullable=False)
    severe_threshold = db.Column(db.Float, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    
    __table_args__ = (db.UniqueConstraint('indicator', 'time_period'),)  # 复合唯一约束
    
    def __repr__(self):
        return f'<AlertThreshold {self.indicator} {self.time_period}>'

class ScenarioAnalysis(db.Model):
    """Model to store scenario analysis results"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    symbol = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    price_change = db.Column(db.Float, nullable=False)  # Percentage change
    volatility_change = db.Column(db.Float, nullable=False)  # Percentage change
    time_horizon = db.Column(db.Integer, nullable=False)  # Days
    estimated_pnl = db.Column(db.Float, nullable=False)
    estimated_delta = db.Column(db.Float, nullable=True)
    estimated_gamma = db.Column(db.Float, nullable=True)
    estimated_vega = db.Column(db.Float, nullable=True)
    estimated_theta = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<ScenarioAnalysis {self.name} {self.symbol}>'
