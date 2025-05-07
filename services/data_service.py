import logging
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from services.exchange_api import get_option_market_data, get_underlying_price
from app import db
from models import OptionData
from config import Config

logger = logging.getLogger(__name__)

class DataService:
    """数据服务类，负责处理期权数据的获取、存储和检索"""
    
    def __init__(self):
        """初始化数据服务"""
        logger.info("DataService initialized")
        
    def fetch_and_store_option_data(self, symbol: str, days_range: int = 7) -> int:
        """
        从交易所获取期权数据并存储到数据库
        
        Args:
            symbol: 标的资产符号 (BTC或ETH)
            days_range: 获取未来多少天内到期的合约
            
        Returns:
            存储的期权数据数量
        """
        # 调用老函数来保持兼容性
        result = fetch_latest_option_data(symbol)
        if result:
            return 1  # 成功返回正数
        return 0
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理旧数据
        
        Args:
            days: 保留最近几天的数据
            
        Returns:
            删除的记录数量
        """
        # 调用老函数
        return cleanup_old_data()
    
    def get_latest_option_data(self, symbol: str, exchange: Optional[str] = None,
                              option_type: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最新的期权数据
        
        Args:
            symbol: 标的资产符号
            exchange: 可选，指定交易所
            option_type: 可选，期权类型 ('call' 或 'put')
            days: 获取最近几天的数据
            
        Returns:
            期权数据列表
        """
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # 构建查询
        query = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp > from_date
        )
        
        if exchange:
            query = query.filter(OptionData.exchange == exchange)
            
        if option_type:
            query = query.filter(OptionData.option_type == option_type)
            
        records = query.order_by(OptionData.timestamp.desc()).all()
        
        # 转换为字典列表
        return [self._option_data_to_dict(option) for option in records]
    
    def get_put_call_ratio(self, symbol: str, exchange: Optional[str] = None,
                          days: int = 1) -> Dict[str, Any]:
        """
        计算看跌/看涨比率
        
        Args:
            symbol: 标的资产符号
            exchange: 可选，指定交易所
            days: 计算最近几天的数据
            
        Returns:
            包含看跌/看涨比率和相关数据的字典
        """
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # 构建基本查询
        base_query = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp > from_date
        )
        
        if exchange:
            base_query = base_query.filter(OptionData.exchange == exchange)
        
        # 获取看跌期权
        put_volume = base_query.filter(
            OptionData.option_type == 'put'
        ).with_entities(
            db.func.sum(OptionData.volume)
        ).scalar() or 0
        
        # 获取看涨期权
        call_volume = base_query.filter(
            OptionData.option_type == 'call'
        ).with_entities(
            db.func.sum(OptionData.volume)
        ).scalar() or 0
        
        # 计算比率
        ratio = put_volume / call_volume if call_volume > 0 else 0
        
        return {
            'symbol': symbol,
            'put_volume': put_volume,
            'call_volume': call_volume,
            'ratio': ratio,
            'period': f'{days} days'
        }
        
    def _option_data_to_dict(self, option: OptionData) -> Dict[str, Any]:
        """将OptionData对象转换为字典"""
        return {
            'id': option.id,
            'symbol': option.symbol,
            'exchange': option.exchange,
            'timestamp': option.timestamp.isoformat(),
            'expiration_date': option.expiration_date.isoformat() if option.expiration_date else None,
            'strike_price': option.strike_price,
            'option_type': option.option_type,
            'underlying_price': option.underlying_price,
            'option_price': option.option_price,
            'volume': option.volume,
            'open_interest': option.open_interest,
            'implied_volatility': option.implied_volatility,
            'delta': option.delta,
            'gamma': option.gamma,
            'theta': option.theta,
            'vega': option.vega
        }
        
# 保留原始函数以保持兼容性
def fetch_latest_option_data(symbol):
    """
    Fetch the latest option data for a given symbol from multiple exchanges
    and store in the database.

    支持从Deribit, Binance, OKX获取期权数据
    """
    try:
        logger.info(f"Fetching latest option data for {symbol} from supported exchanges")

        # 导入所需的模块
        from app import db
        from models import ApiCredential

        # 使用可访问的支持交易所：Deribit, OKX (Binance可能受地区限制)
        enabled_exchanges = ['deribit', 'okx']
        logger.info(f"Using real data from accessible supported exchanges for {symbol}")

        logger.info(f"Fetching {symbol} option data from exchanges: {', '.join(enabled_exchanges)}")

        # 从CCXT集成的API获取当前的期权市场数据
        from services.exchange_api_ccxt import set_api_credentials, get_option_market_data

        # 设置各交易所的API凭证
        for exchange_id in enabled_exchanges:
            api_credential = ApiCredential.query.filter_by(
                api_name=exchange_id, 
                is_active=True
            ).first()

            if api_credential:
                set_api_credentials(
                    api_key=api_credential.api_key, 
                    api_secret=api_credential.api_secret, 
                    exchange_id=exchange_id
                )
                logger.info(f"Set API credentials for {exchange_id}")

        # 获取所有启用交易所的数据
        all_option_data = []
        for exchange_id in enabled_exchanges:
            try:
                # 直接获取数据，不使用超时控制
                result = get_option_market_data(symbol, exchange_id)
                
                if result:
                    logger.info(f"Received {len(result)} option contracts for {symbol} from {exchange_id}")
                    all_option_data.extend(result)
                else:
                    logger.warning(f"No option data received from {exchange_id} for {symbol}")
            except Exception as e:
                logger.error(f"Error fetching {symbol} data from {exchange_id}: {str(e)}")

        # 如果没有数据，返回错误
        if not all_option_data:
            logger.error(f"No option data received from any exchange for {symbol}")
            return False

        logger.info(f"Total {len(all_option_data)} option contracts received for {symbol} from all exchanges")

        # 将API数据转换为OptionData模型对象
        new_records = []
        for data in all_option_data:
            # 将Unix时间戳转换为日期对象
            if isinstance(data["expiration_date"], int):
                expiration_date = datetime.fromtimestamp(data["expiration_date"] / 1000).date()
            else:
                expiration_date = data["expiration_date"]

            # 处理可能的None值
            if expiration_date is None:
                continue  # 跳过没有到期日的记录

            # 安全转换为OptionData对象，处理可能的空值
            try:
                # 提供默认值0或None处理可能的无效值
                option = OptionData(
                    symbol=data["symbol"],
                    expiration_date=expiration_date,
                    strike_price=float(data["strike_price"]),
                    option_type=data["option_type"],
                    underlying_price=float(data["underlying_price"]),
                    option_price=float(data.get("option_price", 0) or 0),
                    volume=int(float(data.get("volume", 0) or 0)),
                    open_interest=int(float(data.get("open_interest", 0) or 0)),
                    implied_volatility=float(data.get("implied_volatility", 0) or 0),
                    delta=float(data.get("delta", 0) or 0),
                    gamma=float(data.get("gamma", 0) or 0),
                    theta=float(data.get("theta", 0) or 0),
                    vega=float(data.get("vega", 0) or 0),
                    timestamp=data.get("timestamp", datetime.utcnow()),
                    # 添加交易所信息
                    exchange=data.get("exchange", "okx")  # 默认为okx作为主交易所
                )
                new_records.append(option)
            except (ValueError, TypeError) as e:
                logger.error(f"处理期权数据时出错: {e}，数据: {data}")
                # 跳过无效数据但不中断整个处理

        # 保存到数据库
        db.session.bulk_save_objects(new_records)
        db.session.commit()

        # 清理旧数据
        cleanup_old_data()

        return True

    except Exception as e:
        logger.error(f"Error fetching option data from API: {str(e)}")
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
    """获取真实交易所的标的资产价格"""
    try:
        from services.exchange_api_ccxt import get_underlying_price
        price = get_underlying_price(symbol)
        if price:
            return price
    except Exception as e:
        logger.error(f"获取{symbol}基准价格时出错: {str(e)}")

    # 如果无法获取真实价格，返回默认值
    prices = {
        'BTC': 92500.0,  # Bitcoin price in USD
        'ETH': 3800.0    # Ethereum price in USD
    }
    return prices.get(symbol, 100.0)