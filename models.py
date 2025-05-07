from datetime import datetime
from app import db

class OptionData(db.Model):
    """Model to store options market data"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    expiration_date = db.Column(db.Date, nullable=False, index=True)
    strike_price = db.Column(db.Float, nullable=False, index=True)
    option_type = db.Column(db.String(4), nullable=False, index=True)  # 'call' or 'put'
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
    exchange = db.Column(db.String(20), default='deribit', nullable=False, index=True)  # 'deribit', 'binance', 'okx'
    
    # 添加复合索引以加速常用查询
    __table_args__ = (
        db.Index('idx_option_symbol_timestamp', 'symbol', 'timestamp'),
        db.Index('idx_option_symbol_type_timestamp', 'symbol', 'option_type', 'timestamp'),
        db.Index('idx_option_exchange_timestamp', 'exchange', 'timestamp'),
    )

    def __repr__(self):
        return f'<OptionData {self.symbol} {self.option_type} {self.strike_price} {self.expiration_date} {self.exchange}>'

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

class StrikeDeviationMonitor(db.Model):
    """Model to store options strike price deviation monitoring data"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_period = db.Column(db.String(10), default='4h', nullable=False, index=True)
    exchange = db.Column(db.String(20), default='deribit', nullable=False, index=True)  # 'deribit', 'binance', 'okx'
    strike_price = db.Column(db.Float, nullable=False)
    market_price = db.Column(db.Float, nullable=False)
    deviation_percent = db.Column(db.Float, nullable=False)  # Absolute deviation percentage
    option_type = db.Column(db.String(4), nullable=False)  # 'call' or 'put'
    expiration_date = db.Column(db.Date, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    volume_change_percent = db.Column(db.Float, nullable=True)  # Volume change from previous period
    premium = db.Column(db.Float, nullable=False)  # Option premium/price
    premium_change_percent = db.Column(db.Float, nullable=True)  # Premium change from previous period
    market_price_change_percent = db.Column(db.Float, nullable=True)  # Market price change from previous period
    is_anomaly = db.Column(db.Boolean, default=False)  # Whether this deviation is considered anomalous
    anomaly_level = db.Column(db.String(20), nullable=True)  # 'attention', 'warning', 'severe'
    
    def __repr__(self):
        return f'<StrikeDeviationMonitor {self.symbol} {self.strike_price} {self.deviation_percent}% {self.time_period}>'
        
class DeviationAlert(db.Model):
    """Model to store strike price deviation alerts"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_period = db.Column(db.String(10), default='4h', nullable=False)
    exchange = db.Column(db.String(20), default='deribit', nullable=False, index=True)  # 'deribit', 'binance', 'okx'
    strike_price = db.Column(db.Float, nullable=False)
    market_price = db.Column(db.Float, nullable=False)
    deviation_percent = db.Column(db.Float, nullable=False)
    option_type = db.Column(db.String(4), nullable=True)  # 'call' or 'put'
    alert_type = db.Column(db.String(20), nullable=False)  # 'attention', 'warning', 'severe'
    message = db.Column(db.Text, nullable=False)
    trigger_condition = db.Column(db.String(100), nullable=False)  # What triggered the alert
    volume_change = db.Column(db.Float, nullable=True)
    premium_change = db.Column(db.Float, nullable=True)
    price_change = db.Column(db.Float, nullable=True)
    is_acknowledged = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<DeviationAlert {self.symbol} {self.strike_price} {self.alert_type} {self.time_period}>'

class ApiCredential(db.Model):
    """Model to store API credentials"""
    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(50), nullable=False, unique=True)
    api_key = db.Column(db.String(100), nullable=False)
    api_secret = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ApiCredential {self.id}: {self.api_name}>"
        
class SystemSetting(db.Model):
    """Model to store system settings"""
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(50), nullable=False, unique=True)
    setting_value = db.Column(db.String(255), nullable=False)
    setting_type = db.Column(db.String(20), nullable=False, default='string')  # string, boolean, integer, float
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def get_typed_value(self):
        """Return the value converted to the appropriate type"""
        if self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', 'yes', '1', 't', 'y')
        elif self.setting_type == 'integer':
            try:
                return int(self.setting_value)
            except ValueError:
                return 0
        elif self.setting_type == 'float':
            try:
                return float(self.setting_value)
            except ValueError:
                return 0.0
        else:  # string or any other type
            return self.setting_value
    
    def __repr__(self):
        return f"<SystemSetting {self.setting_name}: {self.setting_value} ({self.setting_type})>"
