"""
提供模拟市场数据以防真实API调用失败
注意：仅用于开发环境和演示目的，生产环境应采用真实数据
"""

import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 基础价格参考值（USD）
BASE_PRICES = {
    'BTC': 66000.0,
    'ETH': 3500.0,
}

# 波动率参考值 (%)
VOLATILITY = {
    'BTC': 3.5,
    'ETH': 4.2,
}

def get_mock_price(symbol, use_variation=False):
    """
    生成模拟价格数据
    
    Args:
        symbol: 资产符号 ('BTC' 或 'ETH')
        use_variation: 是否添加随机波动
        
    Returns:
        模拟的市场价格
    """
    if symbol not in BASE_PRICES:
        logger.warning(f"未知的资产符号: {symbol}，使用默认价格")
        return 1000.0
    
    base_price = BASE_PRICES[symbol]
    
    if not use_variation:
        return base_price
    
    # 添加最多±2%的随机波动
    variation_pct = (random.random() - 0.5) * 4
    variation = base_price * (variation_pct / 100)
    
    return base_price + variation

def get_mock_ohlcv(symbol, timeframe='1d', bars=100):
    """
    生成模拟的OHLCV数据
    
    Args:
        symbol: 资产符号
        timeframe: 时间周期
        bars: 生成的数据条数
        
    Returns:
        OHLCV数据列表 [[timestamp, open, high, low, close, volume], ...]
    """
    if symbol not in BASE_PRICES:
        logger.warning(f"未知的资产符号: {symbol}，使用默认价格")
        base_price = 1000.0
        volatility = 2.0
    else:
        base_price = BASE_PRICES[symbol]
        volatility = VOLATILITY[symbol]
    
    now = datetime.utcnow()
    
    # 确定时间间隔
    if timeframe == '1h':
        interval = timedelta(hours=1)
    elif timeframe == '4h':
        interval = timedelta(hours=4)
    elif timeframe == '1d':
        interval = timedelta(days=1)
    elif timeframe == '15m':
        interval = timedelta(minutes=15)
    else:
        interval = timedelta(days=1)
    
    result = []
    current_price = base_price
    
    for i in range(bars):
        timestamp = int((now - (interval * i)).timestamp() * 1000)
        
        # 生成随机价格变动 (基于波动率)
        daily_volatility = (volatility / 100) * current_price
        change = random.uniform(-daily_volatility, daily_volatility)
        
        # 计算价格
        close_price = current_price + change
        high_price = close_price + abs(change) * random.uniform(0.2, 0.5)
        low_price = close_price - abs(change) * random.uniform(0.2, 0.5)
        open_price = current_price
        
        # 生成随机交易量
        volume = random.uniform(100, 1000) * (base_price / 1000)
        
        # 添加数据点
        result.append([timestamp, open_price, high_price, low_price, close_price, volume])
        
        # 更新当前价格用于下一个周期
        current_price = close_price
    
    # 反转列表，使最新的数据在最后
    return result[::-1]

def get_mock_ticker(symbol):
    """
    生成模拟的行情数据
    
    Args:
        symbol: 资产符号
        
    Returns:
        模拟的行情数据字典
    """
    base_price = get_mock_price(symbol, True)
    return {
        'symbol': symbol,
        'timestamp': datetime.utcnow().timestamp() * 1000,
        'datetime': datetime.utcnow().isoformat(),
        'high': base_price * 1.02,
        'low': base_price * 0.98,
        'bid': base_price * 0.999,
        'bidVolume': random.uniform(1, 10),
        'ask': base_price * 1.001,
        'askVolume': random.uniform(1, 10),
        'vwap': base_price,
        'open': base_price * 0.995,
        'close': base_price,
        'last': base_price,
        'previousClose': base_price * 0.99,
        'change': base_price * 0.01,
        'percentage': 1.0,
        'average': base_price,
        'baseVolume': random.uniform(1000, 5000),
        'quoteVolume': random.uniform(1000, 5000) * base_price,
        'info': {
            'volume': random.uniform(1000, 5000),
            'openInterest': random.uniform(5000, 20000),
            'impliedVolatility': VOLATILITY[symbol] if symbol in VOLATILITY else 3.0,
            'delta': random.uniform(0.3, 0.7),
            'gamma': random.uniform(0.01, 0.05),
            'theta': random.uniform(-10, -5),
            'vega': random.uniform(10, 50)
        }
    }