import logging
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import func
import pandas as pd

from app import db
from models import OptionData, RiskIndicator
from services.exchange_api import ExchangeAPI

# 配置日志
logger = logging.getLogger(__name__)

class DataService:
    """数据服务类，负责处理期权数据的获取、存储和检索"""
    
    def __init__(self):
        self.exchange_api = ExchangeAPI()
        self.supported_symbols = ["BTC", "ETH"]
        self.supported_exchanges = ["deribit", "okx", "binance"]
    
    def fetch_and_store_option_data(self, symbol: str, days_range: int = 7) -> int:
        """
        从交易所获取期权数据并存储到数据库
        
        Args:
            symbol: 标的资产符号 (BTC或ETH)
            days_range: 获取未来多少天内到期的合约
            
        Returns:
            存储的期权数据数量
        """
        if symbol not in self.supported_symbols:
            logger.error(f"不支持的标的资产: {symbol}")
            return 0
        
        total_stored = 0
        
        for exchange_id in self.supported_exchanges:
            try:
                logger.info(f"从 {exchange_id} 获取 {symbol} 期权数据...")
                
                # 获取期权数据
                option_data_list = self.exchange_api.get_option_data(
                    exchange_id=exchange_id,
                    symbol=symbol,
                    expiry_days_range=days_range
                )
                
                if not option_data_list:
                    logger.warning(f"从 {exchange_id} 未获取到 {symbol} 的期权数据")
                    continue
                
                logger.info(f"从 {exchange_id} 获取到 {len(option_data_list)} 个 {symbol} 期权合约")
                
                # 存储期权数据
                for data in option_data_list:
                    try:
                        # 只保留需要的数据字段
                        option_entry = OptionData(
                            symbol=symbol,
                            exchange=exchange_id,
                            expiration_date=datetime.date.fromisoformat(data['expiration_date']),
                            strike_price=data['strike_price'],
                            option_type=data['option_type'],
                            underlying_price=data['underlying_price'],
                            option_price=data['option_price'],
                            volume=data['volume'],
                            open_interest=data['open_interest'],
                            implied_volatility=data['implied_volatility'],
                            delta=data['delta'],
                            gamma=data['gamma'],
                            theta=data['theta'],
                            vega=data['vega']
                        )
                        
                        # 添加到数据库会话
                        db.session.add(option_entry)
                        total_stored += 1
                    
                    except Exception as e:
                        logger.error(f"存储期权数据时出错: {str(e)}")
                        continue
                
                # 提交数据库事务
                db.session.commit()
                
            except Exception as e:
                logger.error(f"从 {exchange_id} 获取 {symbol} 期权数据时出错: {str(e)}")
                db.session.rollback()
        
        logger.info(f"成功存储 {total_stored} 个 {symbol} 期权数据记录")
        return total_stored
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理旧数据
        
        Args:
            days: 保留最近几天的数据
            
        Returns:
            删除的记录数量
        """
        try:
            # 计算截止日期
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            # 删除旧的期权数据
            option_result = db.session.query(OptionData).filter(
                OptionData.timestamp < cutoff_date
            ).delete()
            
            # 删除旧的风险指标数据
            risk_result = db.session.query(RiskIndicator).filter(
                RiskIndicator.timestamp < cutoff_date
            ).delete()
            
            # 提交事务
            db.session.commit()
            
            total_deleted = option_result + risk_result
            logger.info(f"清理了 {total_deleted} 条旧数据记录")
            return total_deleted
        
        except Exception as e:
            logger.error(f"清理旧数据时出错: {str(e)}")
            db.session.rollback()
            return 0
    
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
        try:
            # 构建查询
            query = db.session.query(OptionData).filter(OptionData.symbol == symbol)
            
            # 应用过滤条件
            if exchange:
                query = query.filter(OptionData.exchange == exchange)
            
            if option_type:
                query = query.filter(OptionData.option_type == option_type)
            
            # 获取最近几天的数据
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            query = query.filter(OptionData.timestamp >= cutoff_date)
            
            # 执行查询
            results = query.order_by(OptionData.timestamp.desc()).all()
            
            # 将模型对象转换为字典
            option_data_list = []
            for option in results:
                option_data = {
                    'id': option.id,
                    'symbol': option.symbol,
                    'exchange': option.exchange,
                    'timestamp': option.timestamp.isoformat(),
                    'expiration_date': option.expiration_date.isoformat(),
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
                option_data_list.append(option_data)
            
            logger.info(f"获取到 {len(option_data_list)} 条 {symbol} 期权数据记录")
            return option_data_list
        
        except Exception as e:
            logger.error(f"获取期权数据时出错: {str(e)}")
            return []
    
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
        try:
            # 获取最近的期权数据
            options = self.get_latest_option_data(
                symbol=symbol,
                exchange=exchange,
                days=days
            )
            
            if not options:
                logger.warning(f"没有找到 {symbol} 的期权数据")
                return {
                    'symbol': symbol,
                    'put_call_ratio': 1.0,
                    'call_volume': 0,
                    'put_volume': 0,
                    'exchange_data': {}
                }
            
            # 将数据转换为DataFrame
            df = pd.DataFrame(options)
            
            # 计算总体看跌/看涨比率
            call_volume = df[df['option_type'] == 'call']['volume'].sum()
            put_volume = df[df['option_type'] == 'put']['volume'].sum()
            
            # 避免除以零
            put_call_ratio = put_volume / call_volume if call_volume > 0 else 1.0
            
            # 计算每个交易所的数据
            exchange_data = {}
            
            if 'exchange' in df.columns:
                for exchange_name in df['exchange'].unique():
                    exchange_df = df[df['exchange'] == exchange_name]
                    ex_call_volume = exchange_df[exchange_df['option_type'] == 'call']['volume'].sum()
                    ex_put_volume = exchange_df[exchange_df['option_type'] == 'put']['volume'].sum()
                    ex_ratio = ex_put_volume / ex_call_volume if ex_call_volume > 0 else 1.0
                    
                    exchange_data[exchange_name] = {
                        'call_volume': int(ex_call_volume),
                        'put_volume': int(ex_put_volume),
                        'ratio': float(ex_ratio)
                    }
            
            result = {
                'symbol': symbol,
                'put_call_ratio': float(put_call_ratio),
                'call_volume': int(call_volume),
                'put_volume': int(put_volume),
                'exchange_data': exchange_data
            }
            
            logger.info(f"{symbol} 的看跌/看涨比率: {put_call_ratio:.2f}")
            return result
        
        except Exception as e:
            logger.error(f"计算看跌/看涨比率时出错: {str(e)}")
            return {
                'symbol': symbol,
                'put_call_ratio': 1.0,
                'call_volume': 0,
                'put_volume': 0,
                'exchange_data': {}
            }