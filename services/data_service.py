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
    Fetch the latest option data for a given symbol from multiple exchanges
    and store in the database.

    支持从Deribit, Binance, OKX获取期权数据
    """
    try:
        logger.info(f"Fetching latest option data for {symbol} from supported exchanges")

        # 导入所需的模块
        from app import db
        from models import ApiCredential

        # 使用所有支持的交易所：Deribit, Binance, OKX
        enabled_exchanges = ['deribit', 'binance', 'okx']
        logger.info(f"Using real data from all supported exchanges for {symbol}")

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