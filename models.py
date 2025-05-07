from datetime import datetime
from app import db

class OptionData(db.Model):
    """期权数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)  # BTC 或 ETH
    exchange = db.Column(db.String(20), nullable=False, index=True)  # 交易所名称: deribit, binance, okx
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 期权合约信息
    expiration_date = db.Column(db.Date, nullable=False, index=True)
    strike_price = db.Column(db.Float, nullable=False)
    option_type = db.Column(db.String(4), nullable=False)  # 'call' 或 'put'
    
    # 价格信息
    underlying_price = db.Column(db.Float, nullable=False)  # 标的资产价格
    option_price = db.Column(db.Float, nullable=False)  # 期权价格/权利金
    
    # 成交量和持仓量
    volume = db.Column(db.Integer, nullable=True)
    open_interest = db.Column(db.Integer, nullable=True)
    
    # 希腊字母
    implied_volatility = db.Column(db.Float, nullable=True)
    delta = db.Column(db.Float, nullable=True)
    gamma = db.Column(db.Float, nullable=True)
    theta = db.Column(db.Float, nullable=True)
    vega = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f"<OptionData(id={self.id}, symbol={self.symbol}, exchange={self.exchange}, "\
               f"strike={self.strike_price}, type={self.option_type}, expiration={self.expiration_date})>"


class RiskIndicator(db.Model):
    """风险指标模型"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_period = db.Column(db.String(10), default='1h', nullable=False, index=True)  # 时间周期: '15m', '1h', '4h', '1d', '7d'
    
    # 核心风险指标
    volatility_index = db.Column(db.Float, nullable=True)  # 波动率指数
    volatility_skew = db.Column(db.Float, nullable=True)  # 波动率偏斜
    put_call_ratio = db.Column(db.Float, nullable=True)  # 看跌/看涨比率
    market_sentiment = db.Column(db.String(20), nullable=True)  # 市场情绪: 'bullish', 'bearish', 'neutral'
    
    # 期权头寸风险
    delta_exposure = db.Column(db.Float, nullable=True)  # Delta敞口
    gamma_exposure = db.Column(db.Float, nullable=True)  # Gamma敞口
    vega_exposure = db.Column(db.Float, nullable=True)  # Vega敞口
    theta_exposure = db.Column(db.Float, nullable=True)  # Theta敞口
    
    # 加密货币特有指标
    funding_rate = db.Column(db.Float, nullable=True)  # 资金费率
    liquidation_risk = db.Column(db.Float, nullable=True)  # 清算风险
    
    # 风险评级
    risk_level = db.Column(db.String(20), nullable=True)  # 'low', 'medium', 'high', 'extreme'
    
    def __repr__(self):
        return f"<RiskIndicator(id={self.id}, symbol={self.symbol}, time_period={self.time_period}, "\
               f"risk_level={self.risk_level}, pcr={self.put_call_ratio})>"