import os

# Application configuration
class Config:
    # Data retention period in days
    DATA_RETENTION_DAYS = 30
    
    # Option strike price range (% from current price) to consider
    OPTION_STRIKE_RANGE_PCT = 10
    
    # 时间周期定义
    TIME_PERIODS = {
        '15m': {'label': '15分钟', 'minutes': 15},
        '1h': {'label': '1小时', 'minutes': 60},
        '4h': {'label': '4小时', 'minutes': 240},
        '1d': {'label': '1天', 'minutes': 1440},
        '7d': {'label': '7天', 'minutes': 10080},
        '30d': {'label': '30天', 'minutes': 43200}
    }
    
    # 按时间周期的动态阈值设置
    DEFAULT_ALERT_THRESHOLDS = {
        'volaxivity': {
            '15m': {'attention': 15, 'warning': 25, 'severe': 35},
            '1h': {'attention': 18, 'warning': 28, 'severe': 38},
            '4h': {'attention': 20, 'warning': 30, 'severe': 40},
            '1d': {'attention': 22, 'warning': 32, 'severe': 42},
            '7d': {'attention': 25, 'warning': 35, 'severe': 45},
            '30d': {'attention': 30, 'warning': 40, 'severe': 50}
        },
        'volatility_skew': {
            '15m': {'attention': 0.3, 'warning': 0.7, 'severe': 1.2},
            '1h': {'attention': 0.4, 'warning': 0.8, 'severe': 1.3},
            '4h': {'attention': 0.5, 'warning': 1.0, 'severe': 1.5},
            '1d': {'attention': 0.6, 'warning': 1.1, 'severe': 1.6},
            '7d': {'attention': 0.7, 'warning': 1.2, 'severe': 1.7},
            '30d': {'attention': 0.8, 'warning': 1.3, 'severe': 1.8}
        },
        'delta_exposure': {
            '15m': {'attention': 0.2, 'warning': 0.4, 'severe': 0.6},
            '1h': {'attention': 0.25, 'warning': 0.45, 'severe': 0.65},
            '4h': {'attention': 0.3, 'warning': 0.5, 'severe': 0.7},
            '1d': {'attention': 0.35, 'warning': 0.55, 'severe': 0.75},
            '7d': {'attention': 0.4, 'warning': 0.6, 'severe': 0.8},
            '30d': {'attention': 0.45, 'warning': 0.65, 'severe': 0.85}
        },
        'gamma_exposure': {
            '15m': {'attention': 0.08, 'warning': 0.15, 'severe': 0.25},
            '1h': {'attention': 0.09, 'warning': 0.18, 'severe': 0.28},
            '4h': {'attention': 0.1, 'warning': 0.2, 'severe': 0.3},
            '1d': {'attention': 0.12, 'warning': 0.22, 'severe': 0.32},
            '7d': {'attention': 0.15, 'warning': 0.25, 'severe': 0.35},
            '30d': {'attention': 0.18, 'warning': 0.28, 'severe': 0.38}
        },
        'vega_exposure': {
            '15m': {'attention': 8, 'warning': 15, 'severe': 25},
            '1h': {'attention': 9, 'warning': 18, 'severe': 28},
            '4h': {'attention': 10, 'warning': 20, 'severe': 30},
            '1d': {'attention': 12, 'warning': 22, 'severe': 32},
            '7d': {'attention': 15, 'warning': 25, 'severe': 35},
            '30d': {'attention': 18, 'warning': 28, 'severe': 38}
        },
        'put_call_ratio': {
            '15m': {'attention': 1.1, 'warning': 1.4, 'severe': 1.8},
            '1h': {'attention': 1.15, 'warning': 1.45, 'severe': 1.9},
            '4h': {'attention': 1.2, 'warning': 1.5, 'severe': 2.0},
            '1d': {'attention': 1.25, 'warning': 1.55, 'severe': 2.1},
            '7d': {'attention': 1.3, 'warning': 1.6, 'severe': 2.2},
            '30d': {'attention': 1.35, 'warning': 1.7, 'severe': 2.3}
        },
        'reflexivity_indicator': {
            '15m': {'attention': 0.2, 'warning': 0.4, 'severe': 0.6},
            '1h': {'attention': 0.25, 'warning': 0.45, 'severe': 0.65},
            '4h': {'attention': 0.3, 'warning': 0.5, 'severe': 0.7},
            '1d': {'attention': 0.35, 'warning': 0.55, 'severe': 0.75},
            '7d': {'attention': 0.4, 'warning': 0.6, 'severe': 0.8},
            '30d': {'attention': 0.45, 'warning': 0.65, 'severe': 0.85}
        }
    }
    
    # Only track cryptocurrency symbols
    TRACKED_SYMBOLS = ['BTC', 'ETH']
    
    # Available languages for UI
    LANGUAGES = {
        'en': 'English',
        'zh': '中文'
    }
    
    # Default language
    DEFAULT_LANGUAGE = 'en'
