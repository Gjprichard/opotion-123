import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import desc, func
import pandas as pd

from app import db
from models import OptionData
from services.exchange_api import ExchangeAPI

# 配置日志
logger = logging.getLogger(__name__)

class DataService:
    """数据服务类，负责处理期权数据的获取、存储和检索"""
    
    def __init__(self):
        """初始化数据服务"""
        self.exchange_api = ExchangeAPI()
    
    def fetch_and_store_option_data(self, symbol: str, days_range: int = 7) -> int:
        """
        从交易所获取期权数据并存储到数据库
        
        Args:
            symbol: 标的资产符号 (BTC或ETH)
            days_range: 获取未来多少天内到期的合约
            
        Returns:
            存储的期权数据数量
        """
        total_stored = 0
        
        try:
            exchanges = ['deribit', 'okx', 'binance']
            
            for exchange in exchanges:
                logger.info(f"从 {exchange} 获取 {symbol} 期权数据...")
                
                try:
                    # 获取期权数据
                    option_data = self.exchange_api.get_option_data(exchange, symbol, days_range)
                    
                    if not option_data:
                        logger.warning(f"从 {exchange} 未获取到 {symbol} 的期权数据")
                        continue
                    
                    # 存储到数据库
                    stored_count = self._store_option_data(option_data)
                    total_stored += stored_count
                    
                except Exception as e:
                    logger.error(f"从 {exchange} 获取 {symbol} 期权数据时出错: {str(e)}")
            
            logger.info(f"成功存储 {total_stored} 个 {symbol} 期权数据记录")
            return total_stored
            
        except Exception as e:
            logger.error(f"获取期权数据时出错: {str(e)}")
            return 0
    
    def _store_option_data(self, option_data: List[Dict[str, Any]]) -> int:
        """
        将期权数据存储到数据库
        
        Args:
            option_data: 期权数据列表
            
        Returns:
            存储的记录数量
        """
        stored_count = 0
        
        try:
            for data in option_data:
                # 检查是否已存在相同的记录
                existing = db.session.query(OptionData).filter(
                    OptionData.symbol == data['symbol'],
                    OptionData.exchange == data['exchange'],
                    OptionData.strike_price == data['strike_price'],
                    OptionData.option_type == data['option_type'],
                    OptionData.expiration_date == data['expiration_date'],
                    OptionData.timestamp >= datetime.utcnow() - timedelta(minutes=30)
                ).first()
                
                if existing:
                    # 更新现有记录
                    for key, value in data.items():
                        if key != 'id':  # 不更新主键
                            setattr(existing, key, value)
                else:
                    # 创建新记录
                    option = OptionData(**data)
                    db.session.add(option)
                
                stored_count += 1
            
            db.session.commit()
            return stored_count
            
        except Exception as e:
            logger.error(f"存储期权数据时出错: {str(e)}")
            db.session.rollback()
            return 0
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理旧数据
        
        Args:
            days: 保留最近几天的数据
            
        Returns:
            删除的记录数量
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 删除旧的期权数据
            deleted = db.session.query(OptionData).filter(OptionData.timestamp < cutoff_date).delete()
            
            db.session.commit()
            logger.info(f"清理了 {deleted} 条旧期权数据")
            
            return deleted
            
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
            query = db.session.query(OptionData).filter(
                OptionData.symbol == symbol,
                OptionData.timestamp >= datetime.utcnow() - timedelta(days=days)
            )
            
            if exchange:
                query = query.filter(OptionData.exchange == exchange)
            
            if option_type:
                query = query.filter(OptionData.option_type == option_type)
            
            # 按时间戳降序排序，获取最新数据
            results = query.order_by(desc(OptionData.timestamp)).all()
            
            # 转换为字典列表
            return [self._option_data_to_dict(option) for option in results]
            
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
            # 计算时间范围
            from_time = datetime.utcnow() - timedelta(days=days)
            
            # 基本查询
            query = db.session.query(
                OptionData.option_type,
                OptionData.exchange,
                func.sum(OptionData.volume).label('total_volume')
            ).filter(
                OptionData.symbol == symbol,
                OptionData.timestamp >= from_time
            ).group_by(
                OptionData.option_type,
                OptionData.exchange
            )
            
            # 如果指定了交易所，添加过滤条件
            if exchange:
                query = query.filter(OptionData.exchange == exchange)
            
            # 执行查询
            results = query.all()
            
            # 转换为字典处理
            data = {}
            exchange_data = {}
            
            call_volume = 0
            put_volume = 0
            
            for r in results:
                option_type, exch, volume = r
                
                # 累计总成交量
                if option_type == 'call':
                    call_volume += volume
                elif option_type == 'put':
                    put_volume += volume
                
                # 构建交易所数据
                if exch not in exchange_data:
                    exchange_data[exch] = {'call_volume': 0, 'put_volume': 0}
                
                if option_type == 'call':
                    exchange_data[exch]['call_volume'] = volume
                elif option_type == 'put':
                    exchange_data[exch]['put_volume'] = volume
            
            # 计算每个交易所的比率
            for exch in exchange_data:
                call_vol = exchange_data[exch]['call_volume']
                put_vol = exchange_data[exch]['put_volume']
                
                ratio = put_vol / call_vol if call_vol > 0 else 1.0
                exchange_data[exch]['ratio'] = ratio
            
            # 计算总比率
            put_call_ratio = put_volume / call_volume if call_volume > 0 else 1.0
            
            # 构建响应数据
            data = {
                'symbol': symbol,
                'call_volume': call_volume,
                'put_volume': put_volume,
                'put_call_ratio': put_call_ratio,
                'days': days,
                'exchange_data': exchange_data
            }
            
            return data
            
        except Exception as e:
            logger.error(f"计算看跌/看涨比率时出错: {str(e)}")
            
            # 返回空数据
            return {
                'symbol': symbol,
                'call_volume': 0,
                'put_volume': 0,
                'put_call_ratio': 1.0,
                'days': days,
                'exchange_data': {}
            }
    
    def _option_data_to_dict(self, option: OptionData) -> Dict[str, Any]:
        """将OptionData对象转换为字典"""
        return {
            'id': option.id,
            'symbol': option.symbol,
            'exchange': option.exchange,
            'timestamp': option.timestamp.isoformat() if option.timestamp else None,
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