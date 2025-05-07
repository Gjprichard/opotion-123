import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from sqlalchemy import desc

from app import db
from models import OptionData, RiskIndicator

# 配置日志
logger = logging.getLogger(__name__)

class RiskService:
    """风险服务类，负责计算和分析风险指标"""
    
    def __init__(self):
        """初始化风险服务"""
        pass
    
    def calculate_risk_indicators(self, symbol: str, time_period: str = '4h') -> Optional[Dict[str, Any]]:
        """
        计算给定资产的风险指标
        
        Args:
            symbol: 资产符号 ('BTC'或'ETH')
            time_period: 时间周期 ('15m', '1h', '4h', '1d', '7d', '30d')
            
        Returns:
            包含风险指标的字典，计算失败时返回None
        """
        try:
            logger.info(f"计算 {symbol} 的风险指标 (时间周期: {time_period})")
            
            # 根据时间周期确定查询时间范围
            period_minutes = self._get_period_minutes(time_period)
            from_time = datetime.utcnow() - timedelta(minutes=period_minutes)
            
            # 从数据库获取期权数据
            query = db.session.query(OptionData).filter(
                OptionData.symbol == symbol,
                OptionData.timestamp >= from_time
            ).order_by(desc(OptionData.timestamp))
            
            option_data = query.all()
            
            if not option_data:
                logger.warning(f"没有找到 {symbol} 的期权数据进行风险计算")
                # 创建空的风险指标
                risk_indicator = self._create_empty_risk_indicator(symbol, time_period)
                return self._risk_indicator_to_dict(risk_indicator)
            
            # 计算风险指标
            indicators = self._compute_indicators(option_data, symbol, time_period)
            
            # 保存到数据库
            risk_indicator = RiskIndicator(
                symbol=symbol,
                time_period=time_period,
                **indicators
            )
            
            db.session.add(risk_indicator)
            db.session.commit()
            
            return self._risk_indicator_to_dict(risk_indicator)
        
        except Exception as e:
            logger.error(f"计算风险指标时出错: {str(e)}")
            db.session.rollback()
            return None
    
    def get_historical_risk_indicators(self, symbol: str, time_period: str = '4h', days: int = 30) -> List[Dict[str, Any]]:
        """
        获取历史风险指标数据
        
        Args:
            symbol: 资产符号
            time_period: 时间周期
            days: 获取最近几天的数据
            
        Returns:
            风险指标数据列表
        """
        try:
            logger.info(f"获取 {symbol} 的历史风险指标 (时间周期: {time_period}, 天数: {days})")
            
            from_time = datetime.utcnow() - timedelta(days=days)
            
            query = db.session.query(RiskIndicator).filter(
                RiskIndicator.symbol == symbol,
                RiskIndicator.time_period == time_period,
                RiskIndicator.timestamp >= from_time
            ).order_by(RiskIndicator.timestamp)
            
            indicators = query.all()
            
            return [self._risk_indicator_to_dict(indicator) for indicator in indicators]
        
        except Exception as e:
            logger.error(f"获取历史风险指标时出错: {str(e)}")
            return []
    
    def _compute_indicators(self, option_data: List[OptionData], symbol: str, time_period: str) -> Dict[str, Any]:
        """
        计算风险指标
        
        Args:
            option_data: 期权数据列表
            symbol: 资产符号
            time_period: 时间周期
            
        Returns:
            包含计算出的风险指标的字典
        """
        # 创建DataFrame方便处理
        df = pd.DataFrame([{
            'strike_price': opt.strike_price,
            'option_type': opt.option_type,
            'underlying_price': opt.underlying_price,
            'option_price': opt.option_price,
            'volume': opt.volume or 0,
            'open_interest': opt.open_interest or 0,
            'implied_volatility': opt.implied_volatility or 0,
            'delta': opt.delta or 0,
            'gamma': opt.gamma or 0,
            'theta': opt.theta or 0,
            'vega': opt.vega or 0,
            'exchange': opt.exchange,
            'timestamp': opt.timestamp
        } for opt in option_data])
        
        # 如果数据为空，返回空的指标集
        if df.empty:
            return {
                'volaxivity': 0.0,
                'volatility_skew': 0.0,
                'put_call_ratio': 1.0,
                'market_sentiment': 'neutral',
                'delta_exposure': 0.0,
                'gamma_exposure': 0.0,
                'vega_exposure': 0.0,
                'theta_exposure': 0.0,
                'funding_rate': 0.01,
                'liquidation_risk': 0.5,
                'risk_level': 'medium'
            }
        
        # 计算波动率指数 (Volaxivity) - 结合当前隐含波动率(70%)和波动率变化率(30%)
        current_iv = df['implied_volatility'].mean()
        iv_change = self._calculate_iv_change(symbol, time_period, current_iv)
        volaxivity = (current_iv * 0.7) + (abs(iv_change) * 0.3)
        
        # 计算波动率偏斜 - 看跌期权与看涨期权隐含波动率的差异
        call_iv = df[df['option_type'] == 'call']['implied_volatility'].mean()
        put_iv = df[df['option_type'] == 'put']['implied_volatility'].mean()
        volatility_skew = put_iv - call_iv if (not np.isnan(put_iv) and not np.isnan(call_iv)) else 0
        
        # 计算看跌/看涨比率
        call_volume = df[df['option_type'] == 'call']['volume'].sum()
        put_volume = df[df['option_type'] == 'put']['volume'].sum()
        put_call_ratio = put_volume / call_volume if call_volume > 0 else 1.0
        
        # 确定市场情绪
        market_sentiment = self._determine_market_sentiment(put_call_ratio, volatility_skew)
        
        # 计算希腊字母敞口
        delta_exposure = self._calculate_weighted_exposure(df, 'delta', 'volume')
        gamma_exposure = self._calculate_weighted_exposure(df, 'gamma', 'volume')
        vega_exposure = self._calculate_weighted_exposure(df, 'vega', 'volume')
        theta_exposure = self._calculate_weighted_exposure(df, 'theta', 'volume')
        
        # 模拟资金费率和清算风险（实际中应从交易所API获取）
        funding_rate = 0.01  # 假设值，实际应从交易所获取
        liquidation_risk = self._calculate_liquidation_risk(delta_exposure, volaxivity)
        
        # 计算整体风险级别
        risk_level = self._determine_risk_level(
            volaxivity, volatility_skew, put_call_ratio, 
            delta_exposure, gamma_exposure, vega_exposure
        )
        
        # 计算反身性指标 (reflexivity_indicator)
        reflexivity_value = self._calculate_reflexivity_indicator(delta_exposure, gamma_exposure, put_call_ratio)
        
        return {
            'volaxivity': float(volaxivity),
            'volatility_skew': float(volatility_skew),
            'put_call_ratio': float(put_call_ratio),
            'market_sentiment': market_sentiment,
            'reflexivity_indicator': float(reflexivity_value),
            'funding_rate': float(funding_rate),
            'liquidation_risk': float(liquidation_risk),
            'risk_level': risk_level
        }
    
    def _calculate_iv_change(self, symbol: str, time_period: str, current_iv: float) -> float:
        """
        计算隐含波动率变化率
        
        Args:
            symbol: 资产符号
            time_period: 时间周期
            current_iv: 当前隐含波动率
            
        Returns:
            隐含波动率变化率
        """
        try:
            # 获取上一个时间周期的风险指标
            period_minutes = self._get_period_minutes(time_period)
            from_time = datetime.utcnow() - timedelta(minutes=period_minutes * 2)
            to_time = datetime.utcnow() - timedelta(minutes=period_minutes)
            
            previous_indicator = db.session.query(RiskIndicator).filter(
                RiskIndicator.symbol == symbol,
                RiskIndicator.time_period == time_period,
                RiskIndicator.timestamp >= from_time,
                RiskIndicator.timestamp <= to_time
            ).order_by(desc(RiskIndicator.timestamp)).first()
            
            if previous_indicator and previous_indicator.volaxivity:
                return (current_iv - previous_indicator.volaxivity) / previous_indicator.volaxivity
            
            return 0.0
        
        except Exception as e:
            logger.warning(f"计算隐含波动率变化率时出错: {str(e)}")
            return 0.0
    
    def _determine_market_sentiment(self, put_call_ratio: float, volatility_skew: float) -> str:
        """
        根据看跌/看涨比率和波动率偏斜确定市场情绪
        
        Args:
            put_call_ratio: 看跌/看涨比率
            volatility_skew: 波动率偏斜
            
        Returns:
            市场情绪: 'bullish', 'bearish', 或 'neutral'
        """
        # PCR > 1.2 强烈看跌信号
        if put_call_ratio > 1.2:
            return 'bearish'
        
        # PCR < 0.8 强烈看涨信号
        elif put_call_ratio < 0.8:
            return 'bullish'
        
        # 波动率偏斜显著为正，看跌情绪
        elif volatility_skew > 0.1:
            return 'bearish'
        
        # 波动率偏斜显著为负，看涨情绪
        elif volatility_skew < -0.1:
            return 'bullish'
        
        # 其他情况为中性
        else:
            return 'neutral'
    
    def _calculate_weighted_exposure(self, df: pd.DataFrame, greek: str, weight_col: str) -> float:
        """
        计算加权的希腊字母敞口
        
        Args:
            df: 期权数据DataFrame
            greek: 希腊字母名称
            weight_col: 权重列名
            
        Returns:
            加权希腊字母敞口
        """
        if df.empty or greek not in df.columns or weight_col not in df.columns:
            return 0.0
        
        # 计算加权敞口
        total_weight = df[weight_col].sum()
        
        if total_weight == 0:
            return 0.0
        
        weighted_exposure = (df[greek] * df[weight_col]).sum() / total_weight
        return weighted_exposure
    
    def _calculate_liquidation_risk(self, delta_exposure: float, volatility: float) -> float:
        """
        计算清算风险
        
        Args:
            delta_exposure: Delta敞口
            volatility: 波动率
            
        Returns:
            清算风险分数 (0-1 范围)
        """
        # 简化模型: 清算风险与Delta敞口的绝对值和波动率正相关
        base_risk = abs(delta_exposure) * 0.3
        vol_component = volatility * 0.7
        
        risk = (base_risk + vol_component) / 2
        
        # 确保值在0-1范围内
        return max(0.0, min(1.0, risk))
    
    def _determine_risk_level(self, volatility: float, skew: float, pcr: float, 
                             delta: float, gamma: float, vega: float) -> str:
        """
        确定整体风险等级
        
        Args:
            volatility: 波动率指数
            skew: 波动率偏斜
            pcr: 看跌/看涨比率
            delta: Delta敞口
            gamma: Gamma敞口
            vega: Vega敞口
            
        Returns:
            风险等级: 'low', 'medium', 'high', 或 'extreme'
        """
        # 计算各指标的风险分数
        vol_score = self._score_volatility(volatility)
        skew_score = self._score_skew(skew)
        pcr_score = self._score_pcr(pcr)
        greek_score = self._score_greeks(delta, gamma, vega)
        
        # 计算加权平均分数
        total_score = (vol_score * 0.3) + (skew_score * 0.2) + (pcr_score * 0.3) + (greek_score * 0.2)
        
        # 根据分数确定风险等级
        if total_score < 0.25:
            return 'low'
        elif total_score < 0.5:
            return 'medium'
        elif total_score < 0.75:
            return 'high'
        else:
            return 'extreme'
    
    def _score_volatility(self, volatility: float) -> float:
        """对波动率进行评分"""
        if volatility < 0.15:
            return 0.0
        elif volatility < 0.25:
            return 0.25
        elif volatility < 0.35:
            return 0.5
        elif volatility < 0.45:
            return 0.75
        else:
            return 1.0
    
    def _score_skew(self, skew: float) -> float:
        """对波动率偏斜进行评分"""
        abs_skew = abs(skew)
        if abs_skew < 0.05:
            return 0.0
        elif abs_skew < 0.1:
            return 0.25
        elif abs_skew < 0.2:
            return 0.5
        elif abs_skew < 0.3:
            return 0.75
        else:
            return 1.0
    
    def _score_pcr(self, pcr: float) -> float:
        """对看跌/看涨比率进行评分"""
        # 看跌/看涨比率偏离1越多，风险越高
        deviation = abs(pcr - 1.0)
        if deviation < 0.1:
            return 0.0
        elif deviation < 0.3:
            return 0.25
        elif deviation < 0.5:
            return 0.5
        elif deviation < 0.8:
            return 0.75
        else:
            return 1.0
    
    def _score_greeks(self, delta: float, gamma: float, vega: float) -> float:
        """对希腊字母敞口进行综合评分"""
        # 简化模型：取三个主要希腊字母敞口绝对值的加权平均
        score = (abs(delta) * 0.5) + (abs(gamma) * 100 * 0.3) + (abs(vega) * 0.01 * 0.2)
        
        # 归一化到0-1范围
        return min(1.0, max(0.0, score / 5.0))
        
    def _calculate_reflexivity_indicator(self, delta: float, gamma: float, pcr: float) -> float:
        """
        计算金融反身性指标
        
        Args:
            delta: Delta敞口
            gamma: Gamma敞口
            pcr: 看跌/看涨比率
            
        Returns:
            反身性指标值 (0-1范围)
        """
        # 反身性指标是对市场自我强化趋势的衡量
        # 高gamma与非中性delta组合表示市场可能处于反身性循环中
        
        # Delta偏离中性点的程度
        delta_deviation = abs(delta)
        
        # Gamma大小表示期权头寸如何放大价格变动
        gamma_impact = abs(gamma) * 100
        
        # PCR偏离1的程度表示市场看涨或看跌情绪的强烈程度
        pcr_deviation = abs(pcr - 1.0)
        
        # 综合计算反身性指标
        reflexivity = (delta_deviation * 0.4) + (gamma_impact * 0.4) + (pcr_deviation * 0.2)
        
        # 归一化到0-1范围
        return min(1.0, max(0.0, reflexivity))
    
    def _create_empty_risk_indicator(self, symbol: str, time_period: str) -> RiskIndicator:
        """创建空的风险指标对象"""
        return RiskIndicator(
            symbol=symbol,
            time_period=time_period,
            volaxivity=0.0,
            volatility_skew=0.0,
            put_call_ratio=1.0,
            market_sentiment='neutral',
            reflexivity_indicator=0.0,
            funding_rate=0.01,
            liquidation_risk=0.5,
            risk_level='medium'
        )
    
    def _risk_indicator_to_dict(self, indicator: RiskIndicator) -> Dict[str, Any]:
        """将RiskIndicator对象转换为字典"""
        result = {
            'id': indicator.id,
            'symbol': indicator.symbol,
            'timestamp': indicator.timestamp.isoformat() if indicator.timestamp else None,
            'time_period': indicator.time_period,
            'volaxivity': indicator.volaxivity,
            'volatility_skew': indicator.volatility_skew,
            'put_call_ratio': indicator.put_call_ratio,
            'market_sentiment': indicator.market_sentiment,
            'reflexivity_indicator': indicator.reflexivity_indicator,
            'funding_rate': indicator.funding_rate,
            'liquidation_risk': indicator.liquidation_risk,
            'risk_level': indicator.risk_level if hasattr(indicator, 'risk_level') else 'medium'
        }
        
        # 添加用于前端显示的价格字段，应从API获取真实数据
        try:
            # 从交易所API获取最新价格
            from services.exchange_api import ExchangeAPI
            exchange_api = ExchangeAPI()
            if indicator.symbol == 'BTC':
                price = exchange_api.get_underlying_price('deribit', 'BTC-USD')
                prev_price = exchange_api.get_underlying_price('deribit', 'BTC-USD', '1d')
            elif indicator.symbol == 'ETH':
                price = exchange_api.get_underlying_price('deribit', 'ETH-USD')
                prev_price = exchange_api.get_underlying_price('deribit', 'ETH-USD', '1d')
            else:
                price = 0
                prev_price = 0
                
            result['price'] = price or 0
            result['price_change'] = ((price - prev_price) / prev_price * 100) if prev_price and price else 0
            
            # 从数据库获取成交量数据
            from models import OptionData
            from sqlalchemy import func, and_
            from datetime import datetime, timedelta
            
            # 计算24小时内的总成交量
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            volume_sum = db.session.query(func.sum(OptionData.volume)).filter(
                and_(
                    OptionData.symbol == indicator.symbol,
                    OptionData.timestamp >= cutoff_time
                )
            ).scalar() or 0
            
            result['total_volume'] = volume_sum
        except Exception as e:
            logger.error(f"获取真实价格和成交量数据时出错: {str(e)}")
            # 发生错误时不提供数据，而不是使用模拟数据
            result['price'] = 0
            result['price_change'] = 0
            result['total_volume'] = 0
        
        return result
    
    def _get_period_minutes(self, time_period: str) -> int:
        """
        将时间周期转换为分钟数
        
        Args:
            time_period: 时间周期字符串
            
        Returns:
            分钟数
        """
        periods = {
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440,  # 24 * 60
            '7d': 10080,  # 7 * 24 * 60
            '30d': 43200  # 30 * 24 * 60
        }
        
        return periods.get(time_period, 60)  # 默认返回1小时(60分钟)