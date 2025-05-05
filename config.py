import os

# Application configuration
class Config:
    # Data retention period in days
    DATA_RETENTION_DAYS = 30
    
    # Option strike price range (% from current price) to consider
    OPTION_STRIKE_RANGE_PCT = 10
    
    # Default alert thresholds
    DEFAULT_ALERT_THRESHOLDS = {
        'volaxivity': {
            'attention': 20,
            'warning': 30,
            'severe': 40
        },
        'volatility_skew': {
            'attention': 0.5,
            'warning': 1.0,
            'severe': 1.5
        },
        'delta_exposure': {
            'attention': 0.3,
            'warning': 0.5,
            'severe': 0.7
        },
        'gamma_exposure': {
            'attention': 0.1,
            'warning': 0.2,
            'severe': 0.3
        },
        'vega_exposure': {
            'attention': 10,
            'warning': 20,
            'severe': 30
        },
        'put_call_ratio': {
            'attention': 1.2,
            'warning': 1.5,
            'severe': 2.0
        },
        'reflexivity_indicator': {
            'attention': 0.3,
            'warning': 0.5,
            'severe': 0.7
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
