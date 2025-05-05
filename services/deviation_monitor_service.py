"""
服务模块：期权执行价偏离监控系统
实时监控BTC/ETH期权中执行价偏离当前市场价±10%的合约
"""

import logging
from datetime import datetime, timedelta
import numpy as np
from statistics import mean, stdev
from models import db, OptionData, StrikeDeviationMonitor, DeviationAlert
from config import Config

logger = logging.getLogger(__name__)

def calculate_deviation_metrics(symbol, time_periods=None):
    """
    计算期权执行价偏离指标
    
    参数:
    symbol - 要计算的交易对符号
    time_periods - 要计算的时间周期列表，如果为None则计算所有配置的时间周期
    """
    # 默认计算所有时间周期
    if time_periods is None:
        # 剔除30d时间周期，偏离监控只关注较短时间周期
        time_periods = [period for period in Config.TIME_PERIODS.keys() 
                        if period != '30d']
    
    logger.info(f"计算{symbol}的期权执行价偏离指标，时间周期: {time_periods}")
    
    # 获取最新的市场价格
    latest_option = OptionData.query.filter_by(symbol=symbol).order_by(
        OptionData.timestamp.desc()).first()
    
    if not latest_option:
        logger.warning(f"没有找到{symbol}的期权数据")
        return False
    
    current_market_price = latest_option.underlying_price
    
    for period in time_periods:
        # 计算时间窗口
        time_window_minutes = Config.TIME_PERIODS[period]['minutes']
        from_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        # 获取当前时间窗口内的期权数据
        current_options = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp >= from_time
        ).all()
        
        # 获取上一个时间窗口的期权数据用于计算变化率
        prev_from_time = from_time - timedelta(minutes=time_window_minutes)
        prev_options = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp >= prev_from_time,
            OptionData.timestamp < from_time
        ).all()
        
        # 建立前一时间段数据的映射，用于快速查找
        prev_option_map = {}
        for opt in prev_options:
            key = f"{opt.option_type}_{opt.strike_price}_{opt.expiration_date}"
            if key not in prev_option_map or opt.timestamp > prev_option_map[key].timestamp:
                prev_option_map[key] = opt
        
        # 计算偏离率，并筛选出偏离率小于或等于10%且成交量不为0的合约
        for option in current_options:
            # 跳过成交量为0的期权
            if option.volume is None or option.volume == 0:
                continue
                
            # 计算偏离率
            deviation_percent = abs((option.strike_price - current_market_price) / current_market_price * 100)
            
            # 只关注偏离率小于或等于10%的期权
            if deviation_percent <= Config.OPTION_STRIKE_RANGE_PCT:  # 10%
                # 查找前一时间段的同一合约
                key = f"{option.option_type}_{option.strike_price}_{option.expiration_date}"
                prev_option = prev_option_map.get(key)
                
                # 计算变化率
                volume_change_pct = None
                premium_change_pct = None
                market_price_change_pct = None
                
                if prev_option:
                    # 成交量变化率
                    if prev_option.volume and prev_option.volume > 0:
                        volume_change_pct = ((option.volume or 0) - prev_option.volume) / prev_option.volume * 100
                    
                    # 权利金变化率
                    if prev_option.option_price > 0:
                        premium_change_pct = (option.option_price - prev_option.option_price) / prev_option.option_price * 100
                    
                    # 市场价格变化率
                    if prev_option.underlying_price > 0:
                        market_price_change_pct = (option.underlying_price - prev_option.underlying_price) / prev_option.underlying_price * 100
                
                # 检查是否是异常情况
                is_anomaly, anomaly_level = check_deviation_anomaly(
                    volume_change_pct, premium_change_pct, market_price_change_pct, 
                    option.option_type, option.strike_price, current_market_price
                )
                
                # 保存监控记录
                deviation = StrikeDeviationMonitor(
                    symbol=symbol,
                    time_period=period,
                    strike_price=option.strike_price,
                    market_price=current_market_price,
                    deviation_percent=deviation_percent,
                    option_type=option.option_type,
                    expiration_date=option.expiration_date,
                    volume=option.volume or 0,
                    volume_change_percent=volume_change_pct,
                    premium=option.option_price,
                    premium_change_percent=premium_change_pct,
                    market_price_change_percent=market_price_change_pct,
                    is_anomaly=is_anomaly,
                    anomaly_level=anomaly_level
                )
                
                db.session.add(deviation)
                
                # 如果是异常情况，生成警报
                if is_anomaly:
                    generate_deviation_alert(
                        deviation, anomaly_level, 
                        volume_change_pct, premium_change_pct, market_price_change_pct
                    )
        
        # 提交数据库事务
        try:
            db.session.commit()
            logger.info(f"已保存{symbol}在{period}时间周期内的期权偏离数据")
        except Exception as e:
            db.session.rollback()
            logger.error(f"保存{symbol}偏离数据时出错: {str(e)}")
            return False
    
    return True

def check_deviation_anomaly(volume_change, premium_change, price_change, option_type, strike_price, market_price):
    """
    检查期权偏离是否异常
    满足以下任一条件即为异常:
    1. 成交量变化率 >= 50%
    2. 权利金变化率 >= 30%
    3. 权利金变化率和市场价格变化率方向相反（背离）
    
    异常级别:
    - 关注级: 单一指标超过阈值
    - 警告级: 两项指标超过阈值或出现方向背离
    - 严重级: 三项指标都超过阈值
    """
    is_anomaly = False
    anomaly_level = None
    anomaly_count = 0
    
    # 检查成交量变化率
    if volume_change is not None and volume_change >= 50:
        is_anomaly = True
        anomaly_count += 1
    
    # 检查权利金变化率
    if premium_change is not None and abs(premium_change) >= 30:
        is_anomaly = True
        anomaly_count += 1
    
    # 检查背离情况 - 权利金变化率和市场价格变化率方向相反
    divergence = False
    if premium_change is not None and price_change is not None:
        # 计算相关性：如果权利金和价格变化方向相反
        if premium_change * price_change < 0:
            is_anomaly = True
            divergence = True
            anomaly_count += 1
    
    # 确定异常级别
    if is_anomaly:
        if anomaly_count == 1:
            anomaly_level = 'attention'  # 关注级
        elif anomaly_count == 2 or divergence:
            anomaly_level = 'warning'    # 警告级
        else:
            anomaly_level = 'severe'     # 严重级
    
    return is_anomaly, anomaly_level

def generate_deviation_alert(deviation, anomaly_level, volume_change, premium_change, price_change):
    """
    生成期权执行价偏离警报
    """
    trigger_conditions = []
    
    if volume_change is not None and volume_change >= 50:
        trigger_conditions.append(f"成交量变化率: {volume_change:.1f}%")
    
    if premium_change is not None and abs(premium_change) >= 30:
        trigger_conditions.append(f"权利金变化率: {premium_change:.1f}%")
    
    if premium_change is not None and price_change is not None and premium_change * price_change < 0:
        direction1 = "上涨" if premium_change > 0 else "下跌"
        direction2 = "上涨" if price_change > 0 else "下跌"
        trigger_conditions.append(f"出现背离: 权利金{direction1} {abs(premium_change):.1f}%, 市场价格{direction2} {abs(price_change):.1f}%")
    
    trigger_condition = ", ".join(trigger_conditions)
    
    # 生成消息
    option_type_str = "看涨" if deviation.option_type == 'call' else "看跌"
    message = (
        f"{deviation.symbol} {option_type_str}期权合约，执行价 {deviation.strike_price} "
        f"偏离市场价 {deviation.deviation_percent:.1f}%，"
        f"触发条件: {trigger_condition}"
    )
    
    # 创建警报
    alert = DeviationAlert(
        symbol=deviation.symbol,
        time_period=deviation.time_period,
        strike_price=deviation.strike_price,
        market_price=deviation.market_price,
        deviation_percent=deviation.deviation_percent,
        alert_type=anomaly_level,
        message=message,
        trigger_condition=trigger_condition,
        volume_change=volume_change,
        premium_change=premium_change,
        price_change=price_change
    )
    
    db.session.add(alert)
    logger.info(f"生成{anomaly_level}级别期权偏离警报: {message}")

def get_deviation_data(symbol=None, time_period='4h', is_anomaly=None, days=7, exchange=None, option_type=None, volume_change_min=None):
    """
    获取期权执行价偏离数据
    
    参数:
    symbol - 交易对符号
    time_period - 时间周期
    is_anomaly - 是否只返回异常数据
    days - 返回过去几天的数据
    exchange - 交易所，如deribit, binance, okx
    option_type - 期权类型，call或put
    volume_change_min - 成交量变化率最小值（过滤结果只显示大于此值的条目）
    """
    from_date = datetime.utcnow() - timedelta(days=days)
    
    query = StrikeDeviationMonitor.query.filter(
        StrikeDeviationMonitor.timestamp >= from_date,
        StrikeDeviationMonitor.time_period == time_period
    )
    
    if symbol:
        query = query.filter(StrikeDeviationMonitor.symbol == symbol)
    
    if is_anomaly is not None:
        query = query.filter(StrikeDeviationMonitor.is_anomaly == is_anomaly)
    
    if exchange:
        query = query.filter(StrikeDeviationMonitor.exchange == exchange)
        
    if option_type:
        query = query.filter(StrikeDeviationMonitor.option_type == option_type)
        
    if volume_change_min is not None and volume_change_min > 0:
        query = query.filter(StrikeDeviationMonitor.volume_change_percent >= volume_change_min)
    
    # 按时间降序排序
    deviations = query.order_by(StrikeDeviationMonitor.timestamp.desc()).all()
    
    return deviations

def get_deviation_alerts(symbol=None, time_period='4h', acknowledged=None, limit=100, exchange=None, option_type=None):
    """
    获取期权执行价偏离警报
    
    参数:
    symbol - 交易对符号
    time_period - 时间周期
    acknowledged - 是否确认状态
    limit - 返回结果数量限制
    exchange - 交易所，如deribit, binance, okx
    option_type - 期权类型，call或put
    """
    query = DeviationAlert.query.filter(
        DeviationAlert.time_period == time_period
    )
    
    if symbol:
        query = query.filter(DeviationAlert.symbol == symbol)
    
    if acknowledged is not None:
        query = query.filter(DeviationAlert.is_acknowledged == acknowledged)
        
    if exchange:
        query = query.filter(DeviationAlert.exchange == exchange)
        
    if option_type:
        query = query.filter(DeviationAlert.option_type == option_type)
    
    # 按时间降序排序
    alerts = query.order_by(DeviationAlert.timestamp.desc()).limit(limit).all()
    
    return alerts

def acknowledge_deviation_alert(alert_id):
    """
    确认期权执行价偏离警报
    """
    alert = DeviationAlert.query.get(alert_id)
    
    if alert:
        alert.is_acknowledged = True
        db.session.commit()
        return True
    
    return False