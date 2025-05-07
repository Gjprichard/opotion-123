import logging
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sqlalchemy import func

from app import db
from models import OptionData, RiskIndicator
from services.data_service import DataService

# 配置日志
logger = logging.getLogger(__name__)

class RiskService:
    """风险分析服务，计算各种风险指标"""
    
    def __init__(self):
        self.data_service = DataService()
        self.time_periods = {
            '15m': 0.01,     # 15分钟
            '1h': 0.042,     # 1小时
            '4h': 0.167,     # 4小时
            '1d': 1,         # 1天
            '7d': 7          # 7天
        }
    
    def calculate_risk_indicators(self, symbol: str, time_period: str = '1h') -> Dict[str, Any]:
        """
        计算风险指标
        
        Args:
            symbol: 标的资产符号
            time_period: 时间周期 ('15m', '1h', '4h', '1d', '7d')
            
        Returns:
            风险指标字典
        """
        try:
            if time_period not in self.time_periods:
                logger.error(f"不支持的时间周期: {time_period}")
                return {}
            
            # 计算时间参数 (以天为单位)
            days_param = self.time_periods[time_period]
            days_to_fetch = max(1, days_param * 2)  # 至少获取1天的数据
            
            # 获取最新的期权数据
            option_data = self.data_service.get_latest_option_data(
                symbol=symbol,
                days=days_to_fetch
            )
            
            if not option_data:
                logger.warning(f"没有找到 {symbol} 的期权数据")
                return {}
            
            # 将数据转换为DataFrame
            df = pd.DataFrame(option_data)
            
            # 提取最新的标的价格
            current_price = df['underlying_price'].iloc[0] if not df.empty else 0
            
            # 计算波动率指数
            volatility_index = self._calculate_volatility_index(df)
            
            # 计算波动率偏斜
            volatility_skew = self._calculate_volatility_skew(df)
            
            # 计算看跌/看涨比率
            pcr_data = self.data_service.get_put_call_ratio(
                symbol=symbol,
                days=days_to_fetch
            )
            put_call_ratio = pcr_data.get('put_call_ratio', 1.0)
            
            # 计算市场情绪
            market_sentiment = self._determine_market_sentiment(put_call_ratio, volatility_skew)
            
            # 计算头寸风险
            positions = self._calculate_position_risks(df, current_price)
            
            # 计算加密货币特有指标
            crypto_indicators = self._calculate_crypto_indicators(symbol)
            
            # 整合所有风险指标
            risk_indicators = {
                'symbol': symbol,
                'time_period': time_period,
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'volatility_index': volatility_index,
                'volatility_skew': volatility_skew,
                'put_call_ratio': put_call_ratio,
                'market_sentiment': market_sentiment,
                'delta_exposure': positions.get('delta_exposure', 0),
                'gamma_exposure': positions.get('gamma_exposure', 0),
                'vega_exposure': positions.get('vega_exposure', 0),
                'theta_exposure': positions.get('theta_exposure', 0),
                'funding_rate': crypto_indicators.get('funding_rate', 0),
                'liquidation_risk': crypto_indicators.get('liquidation_risk', 0),
                'risk_level': self._calculate_risk_level(
                    volatility_index, volatility_skew, put_call_ratio, positions
                ),
                'current_price': current_price
            }
            
            # 存储风险指标到数据库
            self._store_risk_indicators(risk_indicators)
            
            logger.info(f"计算了 {symbol} 的风险指标 (时间周期: {time_period})")
            return risk_indicators
        
        except Exception as e:
            logger.error(f"计算风险指标时出错: {str(e)}")
            return {}
    
    def get_historical_risk_indicators(self, symbol: str, time_period: str = '1h',
                                     days: int = 30) -> List[Dict[str, Any]]:
        """
        获取历史风险指标
        
        Args:
            symbol: 标的资产符号
            time_period: 时间周期
            days: 获取最近几天的数据
            
        Returns:
            风险指标列表
        """
        try:
            # 计算截止日期
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            # 构建查询
            query = db.session.query(RiskIndicator).filter(
                RiskIndicator.symbol == symbol,
                RiskIndicator.time_period == time_period,
                RiskIndicator.timestamp >= cutoff_date
            )
            
            # 执行查询
            results = query.order_by(RiskIndicator.timestamp.asc()).all()
            
            # 将模型对象转换为字典
            risk_indicators = []
            for indicator in results:
                indicator_data = {
                    'id': indicator.id,
                    'symbol': indicator.symbol,
                    'timestamp': indicator.timestamp.isoformat(),
                    'time_period': indicator.time_period,
                    'volatility_index': indicator.volatility_index,
                    'volatility_skew': indicator.volatility_skew,
                    'put_call_ratio': indicator.put_call_ratio,
                    'market_sentiment': indicator.market_sentiment,
                    'delta_exposure': indicator.delta_exposure,
                    'gamma_exposure': indicator.gamma_exposure,
                    'vega_exposure': indicator.vega_exposure,
                    'theta_exposure': indicator.theta_exposure,
                    'funding_rate': indicator.funding_rate,
                    'liquidation_risk': indicator.liquidation_risk,
                    'risk_level': indicator.risk_level
                }
                risk_indicators.append(indicator_data)
            
            logger.info(f"获取到 {len(risk_indicators)} 条 {symbol} 的历史风险指标 (时间周期: {time_period})")
            return risk_indicators
        
        except Exception as e:
            logger.error(f"获取历史风险指标时出错: {str(e)}")
            return []
    
    def _calculate_volatility_index(self, df: pd.DataFrame) -> float:
        """计算波动率指数"""
        try:
            if df.empty or 'implied_volatility' not in df.columns:
                return 0.0
            
            # 过滤掉无效的隐含波动率
            valid_iv = df['implied_volatility'].dropna()
            if len(valid_iv) == 0:
                return 0.0
            
            # 计算加权平均隐含波动率
            weights = np.ones(len(valid_iv))  # 简单起见使用等权重
            volatility_index = np.average(valid_iv, weights=weights)
            
            return float(volatility_index)
        
        except Exception as e:
            logger.error(f"计算波动率指数时出错: {str(e)}")
            return 0.0
    
    def _calculate_volatility_skew(self, df: pd.DataFrame) -> float:
        """计算波动率偏斜"""
        try:
            if df.empty or 'implied_volatility' not in df.columns or 'option_type' not in df.columns:
                return 0.0
            
            # 分离看涨和看跌期权
            call_options = df[df['option_type'] == 'call']
            put_options = df[df['option_type'] == 'put']
            
            # 检查是否有足够的数据
            if call_options.empty or put_options.empty:
                return 0.0
            
            # 计算看涨和看跌期权的平均隐含波动率
            call_iv = call_options['implied_volatility'].dropna().mean()
            put_iv = put_options['implied_volatility'].dropna().mean()
            
            # 计算偏斜 (看跌-看涨 IV差异)
            if np.isnan(call_iv) or np.isnan(put_iv):
                return 0.0
                
            skew = put_iv - call_iv
            
            return float(skew)
        
        except Exception as e:
            logger.error(f"计算波动率偏斜时出错: {str(e)}")
            return 0.0
    
    def _determine_market_sentiment(self, put_call_ratio: float, volatility_skew: float) -> str:
        """确定市场情绪"""
        try:
            # 基于看跌/看涨比率和波动率偏斜的简单情绪判断
            if put_call_ratio > 1.2 and volatility_skew > 0.05:
                return 'bearish'  # 偏空
            elif put_call_ratio < 0.8 and volatility_skew < -0.05:
                return 'bullish'  # 偏多
            else:
                return 'neutral'  # 中性
        
        except Exception as e:
            logger.error(f"确定市场情绪时出错: {str(e)}")
            return 'neutral'
    
    def _calculate_position_risks(self, df: pd.DataFrame, current_price: float) -> Dict[str, float]:
        """计算头寸风险"""
        try:
            if df.empty:
                return {
                    'delta_exposure': 0.0,
                    'gamma_exposure': 0.0,
                    'vega_exposure': 0.0,
                    'theta_exposure': 0.0
                }
            
            # 计算总的希腊字母敞口
            delta_sum = df['delta'].dropna().sum()
            gamma_sum = df['gamma'].dropna().sum()
            vega_sum = df['vega'].dropna().sum()
            theta_sum = df['theta'].dropna().sum()
            
            # 归一化处理，使其更具可比性
            delta_exposure = delta_sum / 100.0 if current_price > 0 else 0.0
            gamma_exposure = gamma_sum / 1000.0 if current_price > 0 else 0.0
            vega_exposure = vega_sum / 1000.0 if current_price > 0 else 0.0
            theta_exposure = theta_sum / 1000.0 if current_price > 0 else 0.0
            
            return {
                'delta_exposure': float(delta_exposure),
                'gamma_exposure': float(gamma_exposure),
                'vega_exposure': float(vega_exposure),
                'theta_exposure': float(theta_exposure)
            }
        
        except Exception as e:
            logger.error(f"计算头寸风险时出错: {str(e)}")
            return {
                'delta_exposure': 0.0,
                'gamma_exposure': 0.0,
                'vega_exposure': 0.0,
                'theta_exposure': 0.0
            }
    
    def _calculate_crypto_indicators(self, symbol: str) -> Dict[str, float]:
        """计算加密货币特有指标"""
        try:
            # 这里可以添加从交易所获取资金费率等数据的逻辑
            # 目前使用模拟数据
            funding_rate = 0.01  # 正常资金费率约为0.01% 每8小时
            
            # 根据资金费率估算清算风险
            liquidation_risk = abs(funding_rate) * 50  # 简单模型
            
            return {
                'funding_rate': funding_rate,
                'liquidation_risk': liquidation_risk
            }
        
        except Exception as e:
            logger.error(f"计算加密货币特有指标时出错: {str(e)}")
            return {
                'funding_rate': 0.0,
                'liquidation_risk': 0.0
            }
    
    def _calculate_risk_level(self, volatility_index: float, volatility_skew: float,
                            put_call_ratio: float, positions: Dict[str, float]) -> str:
        """计算综合风险等级"""
        try:
            # 定义风险因子权重
            weights = {
                'volatility_index': 0.3,
                'volatility_skew': 0.2,
                'put_call_ratio': 0.3,
                'positions': 0.2
            }
            
            # 归一化指标
            normalized_vol_index = min(1.0, volatility_index / 100.0)
            normalized_vol_skew = min(1.0, abs(volatility_skew) / 0.2)
            
            # 归一化PCR (1.0是中性，偏离1.0越远风险越高)
            normalized_pcr = min(1.0, abs(put_call_ratio - 1.0) / 0.5)
            
            # 归一化头寸风险
            position_risk = abs(positions.get('delta_exposure', 0)) + abs(positions.get('gamma_exposure', 0))
            normalized_position_risk = min(1.0, position_risk / 1.0)
            
            # 计算综合风险分数
            risk_score = (
                weights['volatility_index'] * normalized_vol_index +
                weights['volatility_skew'] * normalized_vol_skew +
                weights['put_call_ratio'] * normalized_pcr +
                weights['positions'] * normalized_position_risk
            )
            
            # 根据风险分数确定风险等级
            if risk_score < 0.25:
                return 'low'
            elif risk_score < 0.5:
                return 'medium'
            elif risk_score < 0.75:
                return 'high'
            else:
                return 'extreme'
        
        except Exception as e:
            logger.error(f"计算风险等级时出错: {str(e)}")
            return 'medium'
    
    def _store_risk_indicators(self, indicators: Dict[str, Any]) -> None:
        """将风险指标存储到数据库"""
        try:
            # 创建新的风险指标记录
            risk_indicator = RiskIndicator(
                symbol=indicators['symbol'],
                time_period=indicators['time_period'],
                volatility_index=indicators.get('volatility_index'),
                volatility_skew=indicators.get('volatility_skew'),
                put_call_ratio=indicators.get('put_call_ratio'),
                market_sentiment=indicators.get('market_sentiment'),
                delta_exposure=indicators.get('delta_exposure'),
                gamma_exposure=indicators.get('gamma_exposure'),
                vega_exposure=indicators.get('vega_exposure'),
                theta_exposure=indicators.get('theta_exposure'),
                funding_rate=indicators.get('funding_rate'),
                liquidation_risk=indicators.get('liquidation_risk'),
                risk_level=indicators.get('risk_level')
            )
            
            # 添加到数据库会话
            db.session.add(risk_indicator)
            db.session.commit()
            
            logger.info(f"存储了 {indicators['symbol']} 的风险指标 (时间周期: {indicators['time_period']})")
        
        except Exception as e:
            logger.error(f"存储风险指标时出错: {str(e)}")
            db.session.rollback()