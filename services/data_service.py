import logging
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from services.exchange_api import get_option_market_data, get_underlying_price
from app import db
from models import OptionData
from config import Config

logger = logging.getLogger(__name__)

def fetch_latest_option_data(symbol):
    """
    Fetch the latest option data for a given symbol from Deribit API
    and store in the database.
    """
    try:
        logger.info(f"Fetching latest option data for {symbol} from Deribit API")
        
        # 检查是否应该使用实时数据
        from app import db
        from models import SystemSetting, ApiCredential
        
        use_real_data_setting = SystemSetting.query.filter_by(setting_name='use_real_data').first()
        use_real_data = use_real_data_setting.get_typed_value() if use_real_data_setting else False
        
        # 如果不使用实时数据，直接使用模拟数据
        if not use_real_data:
            logger.info(f"Real data is disabled, using simulation for {symbol}")
            return fallback_option_data(symbol)
        
        # 检查是否有有效的API凭证
        api_credential = ApiCredential.query.filter_by(api_name='deribit', is_active=True).first()
        if not api_credential:
            logger.warning(f"No active API credentials found for Deribit, using fallback data for {symbol}")
            return fallback_option_data(symbol)
        
        # 设置API凭证
        from services.exchange_api import set_api_credentials
        set_api_credentials(api_credential.api_key, api_credential.api_secret)
        
        # 从Deribit API获取当前的期权市场数据
        from services.exchange_api import get_option_market_data
        option_data_list = get_option_market_data(symbol)
        
        if not option_data_list:
            logger.warning(f"No option data received from API for {symbol}, using fallback data")
            return fallback_option_data(symbol)
        
        logger.info(f"Received {len(option_data_list)} option contracts for {symbol}")
        
        # 将API数据转换为OptionData模型对象
        new_records = []
        for data in option_data_list:
            # 将Unix时间戳转换为日期对象
            if isinstance(data["expiration_date"], int):
                expiration_date = datetime.fromtimestamp(data["expiration_date"] / 1000).date()
            else:
                expiration_date = data["expiration_date"]
                
            # 转换为OptionData对象
            option = OptionData(
                symbol=data["symbol"],
                expiration_date=expiration_date,
                strike_price=float(data["strike_price"]),
                option_type=data["option_type"],
                underlying_price=float(data["underlying_price"]),
                option_price=float(data["option_price"]),
                volume=int(data.get("volume", 0) or 0),
                open_interest=int(data.get("open_interest", 0) or 0),
                implied_volatility=float(data["implied_volatility"]) if data.get("implied_volatility") else None,
                delta=float(data["delta"]) if data.get("delta") else None,
                gamma=float(data["gamma"]) if data.get("gamma") else None,
                theta=float(data["theta"]) if data.get("theta") else None,
                vega=float(data["vega"]) if data.get("vega") else None,
                timestamp=data.get("timestamp", datetime.utcnow())
            )
            new_records.append(option)
        
        # 保存到数据库
        db.session.bulk_save_objects(new_records)
        db.session.commit()
        
        # 清理旧数据
        cleanup_old_data()
        
        return True
        
    except Exception as e:
        logger.error(f"Error fetching option data from API: {str(e)}")
        db.session.rollback()
        # 尝试使用模拟数据作为备选方案
        return fallback_option_data(symbol)

def fallback_option_data(symbol):
    """
    仅当API连接失败时使用模拟数据作为备选方案
    """
    try:
        logger.warning(f"Using fallback simulation for {symbol} option data")
        
        # 获取当前日期并设置到期日为30天后
        current_date = datetime.now().date()
        expirations = [
            current_date + timedelta(days=30)
        ]
        
        # 尝试从API获取标的资产价格，如果失败则使用模拟价格
        current_price = get_underlying_price(symbol)
        if not current_price:
            base_price = get_base_price_for_symbol(symbol)
            current_price = base_price
        
        # 计算执行价范围
        min_strike = current_price * (1 - Config.OPTION_STRIKE_RANGE_PCT / 100)
        max_strike = current_price * (1 + Config.OPTION_STRIKE_RANGE_PCT / 100)
        
        # 生成执行价序列
        strikes = np.linspace(min_strike, max_strike, 10)
        
        # 为每个组合生成期权数据
        timestamp = datetime.utcnow()
        new_records = []
        
        for expiration in expirations:
            days_to_expiry = (expiration - current_date).days
            
            for strike in strikes:
                # 生成看涨期权
                call_option = generate_option_data(
                    symbol, expiration, strike, 'call', current_price, days_to_expiry, timestamp
                )
                new_records.append(call_option)
                
                # 生成看跌期权
                put_option = generate_option_data(
                    symbol, expiration, strike, 'put', current_price, days_to_expiry, timestamp
                )
                new_records.append(put_option)
        
        # 保存到数据库
        db.session.bulk_save_objects(new_records)
        db.session.commit()
        
        # 清理旧数据
        cleanup_old_data()
        
        return True
        
    except Exception as e:
        logger.error(f"Error in fallback option data generation: {str(e)}")
        db.session.rollback()
        return False

def fetch_historical_data(symbol, days=30):
    """
    Fetch historical option data for backtesting or analysis.
    Returns data directly without storing in the database.
    """
    try:
        from_date = datetime.utcnow() - timedelta(days=days)
        
        historical_data = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp > from_date
        ).order_by(OptionData.timestamp).all()
        
        return historical_data
    
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return []

def cleanup_old_data():
    """Remove data older than the retention period"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=Config.DATA_RETENTION_DAYS)
        
        # Delete old option data
        deleted_count = OptionData.query.filter(
            OptionData.timestamp < cutoff_date
        ).delete()
        
        db.session.commit()
        logger.info(f"Cleaned up {deleted_count} old option data records")
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
        db.session.rollback()

def get_base_price_for_symbol(symbol):
    """Return a realistic base price for the given symbol"""
    prices = {
        'BTC': 92500.0,  # Bitcoin price in USD
        'ETH': 3800.0    # Ethereum price in USD
    }
    return prices.get(symbol, 100.0)

def generate_option_data(symbol, expiration, strike, option_type, current_price, days_to_expiry, timestamp):
    """Generate realistic option data based on the Black-Scholes model"""
    # Parameters for the simulation
    risk_free_rate = 0.03  # 3% risk-free rate
    dividend_yield = 0.01  # 1% dividend yield
    
    # Base implied volatility that increases for farther expirations
    base_iv = 0.20 + (days_to_expiry / 365) * 0.05
    
    # Skew effect: further OTM options have higher IV (volatility smile)
    moneyness = strike / current_price
    skew_factor = abs(moneyness - 1.0) * 0.5
    
    # Puts typically have higher IV
    if option_type == 'put':
        skew_factor *= 1.2
    
    implied_volatility = base_iv + skew_factor
    implied_volatility = max(0.05, min(implied_volatility, 1.0))  # Cap between 5% and 100%
    
    # Calculate option price using Black-Scholes approximation
    if option_type == 'call':
        option_price = black_scholes_call(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility)
    else:
        option_price = black_scholes_put(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility)
    
    # Calculate the Greeks
    delta = calculate_delta(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility, option_type)
    gamma = calculate_gamma(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility)
    theta = calculate_theta(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility, option_type)
    vega = calculate_vega(current_price, strike, days_to_expiry/365, risk_free_rate, implied_volatility)
    
    # Generate volume and open interest
    atm_factor = 1.0 - abs(moneyness - 1.0) * 4  # ATM options have higher volume
    atm_factor = max(0.1, atm_factor)
    
    volume = int(random.uniform(50, 500) * atm_factor)
    open_interest = int(random.uniform(200, 2000) * atm_factor)
    
    # Create the option data object - convert numpy types to Python native types
    option_data = OptionData(
        symbol=str(symbol),
        expiration_date=expiration,
        strike_price=float(strike),
        option_type=str(option_type),
        underlying_price=float(current_price),
        option_price=float(option_price),
        volume=int(volume),
        open_interest=int(open_interest),
        implied_volatility=float(implied_volatility),
        delta=float(delta),
        gamma=float(gamma),
        theta=float(theta),
        vega=float(vega),
        timestamp=timestamp
    )
    
    return option_data

def black_scholes_call(S, K, T, r, sigma):
    """Calculate call option price using Black-Scholes formula"""
    from scipy.stats import norm
    import math
    
    # Calculate d1 and d2
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    # Calculate call price
    call_price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return call_price

def black_scholes_put(S, K, T, r, sigma):
    """Calculate put option price using Black-Scholes formula"""
    from scipy.stats import norm
    import math
    
    # Calculate d1 and d2
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    # Calculate put price
    put_price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return put_price

def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate delta of an option"""
    from scipy.stats import norm
    import math
    
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1

def calculate_gamma(S, K, T, r, sigma):
    """Calculate gamma of an option"""
    from scipy.stats import norm
    import math
    
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    return gamma

def calculate_theta(S, K, T, r, sigma, option_type):
    """Calculate theta of an option"""
    from scipy.stats import norm
    import math
    
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'call':
        theta = -S * sigma * norm.pdf(d1) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)
    else:
        theta = -S * sigma * norm.pdf(d1) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)
    
    # Convert from annual to daily
    return theta / 365

def calculate_vega(S, K, T, r, sigma):
    """Calculate vega of an option"""
    from scipy.stats import norm
    import math
    
    d1 = (math.log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    vega = S * math.sqrt(T) * norm.pdf(d1) * 0.01  # 1% change in volatility
    return vega
