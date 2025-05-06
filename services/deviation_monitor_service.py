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
                    else:
                        # 如果前一时段没有成交量数据，但当前有成交量，则视为100%的增长
                        if option.volume and option.volume > 0:
                            volume_change_pct = 100.0
                    
                    # 权利金变化率
                    if prev_option.option_price > 0:
                        premium_change_pct = (option.option_price - prev_option.option_price) / prev_option.option_price * 100
                    
                    # 市场价格变化率
                    if prev_option.underlying_price > 0:
                        market_price_change_pct = (option.underlying_price - prev_option.underlying_price) / prev_option.underlying_price * 100
                else:
                    # 如果找不到前一时段的数据，但当前有成交量，则视为新增合约，设置默认变化率
                    if option.volume and option.volume > 0:
                        volume_change_pct = 100.0  # 新增合约，默认成交量增长100%
                
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

def get_deviation_data(symbol=None, time_period='4h', is_anomaly=None, days=7, exchange=None, option_type=None, volume_change_filter=None):
    """
    获取期权执行价偏离数据 - 优化版
    
    参数:
    symbol - 交易对符号 (BTC或ETH)
    time_period - 时间周期
    is_anomaly - 是否只返回异常数据
    days - 返回过去几天的数据
    exchange - 交易所，如deribit, binance, okx
    option_type - 期权类型，call或put
    volume_change_filter - 成交量变化率最小值（过滤结果只显示大于此值的条目）
    
    返回:
    {
        'deviations': [StrikeDeviationMonitor对象列表],
        'statistics': {
            'avg_deviation': 平均偏离率,
            'avg_volume_change': 平均成交量变化率,
            'avg_premium_change': 平均权利金变化率,
            'max_deviation': 最大偏离率,
            'min_deviation': 最小偏离率,
            'call_count': 看涨期权数量,
            'put_count': 看跌期权数量,
            'put_call_ratio': 看跌/看涨比率,
            'anomaly_percentage': 异常数据占比,
            'volume_change_distribution': 成交量变化分布,
            'deviation_distribution': 偏离率分布,
            'trend_analysis': 趋势分析数据
        }
    }
    """
    from_date = datetime.utcnow() - timedelta(days=days)
    
    # 验证symbol，仅支持BTC和ETH
    if symbol and symbol not in ["BTC", "ETH"]:
        logger.warning(f"不支持的符号: {symbol}，仅支持BTC和ETH")
        return {'deviations': [], 'statistics': {}}
    
    # 构建查询 - 使用缓存优化查询性能
    query = StrikeDeviationMonitor.query.filter(
        StrikeDeviationMonitor.timestamp >= from_date,
        StrikeDeviationMonitor.time_period == time_period
    )
    
    # 添加其他筛选条件 - 按优先级排序，先应用可能过滤掉更多数据的条件
    if symbol:
        query = query.filter(StrikeDeviationMonitor.symbol == symbol)
    
    if is_anomaly is not None:
        query = query.filter(StrikeDeviationMonitor.is_anomaly == is_anomaly)
    
    if exchange:
        query = query.filter(StrikeDeviationMonitor.exchange == exchange)
        
    if option_type:
        query = query.filter(StrikeDeviationMonitor.option_type == option_type)
        
    if volume_change_filter is not None and volume_change_filter > 0:
        # 确保只返回volume_change_percent非null且大于等于指定值的记录
        query = query.filter(
            StrikeDeviationMonitor.volume_change_percent.isnot(None),
            StrikeDeviationMonitor.volume_change_percent >= volume_change_filter
        )
    
    # 优化：限制返回记录数量，避免内存溢出
    max_records = 1000
    
    # 按时间降序排序，并限制记录数
    deviations = query.order_by(
        StrikeDeviationMonitor.timestamp.desc()
    ).limit(max_records).all()
    
    logger.info(f"获取到 {len(deviations)} 条偏离数据记录 (限制: {max_records})")
    
    # 创建结果结构
    result = {
        'deviations': deviations,
        'statistics': {}
    }
    
    # 计算统计指标
    if deviations:
        # 基础统计
        deviation_values = [d.deviation_percent for d in deviations]
        
        valid_volume_changes = [d.volume_change_percent for d in deviations 
                              if d.volume_change_percent is not None]
        
        valid_premium_changes = [d.premium_change_percent for d in deviations 
                               if d.premium_change_percent is not None]
        
        # 期权类型统计
        call_deviations = [d for d in deviations if d.option_type == 'call']
        put_deviations = [d for d in deviations if d.option_type == 'put']
        
        # 异常数据统计
        anomaly_deviations = [d for d in deviations if d.is_anomaly]
        
        # 计算平均值、最大值、最小值等
        statistics = {
            'avg_deviation': mean(deviation_values) if deviation_values else 0,
            'max_deviation': max(deviation_values) if deviation_values else 0,
            'min_deviation': min(deviation_values) if deviation_values else 0,
            'deviation_std': stdev(deviation_values) if len(deviation_values) > 1 else 0,
            
            'avg_volume_change': mean(valid_volume_changes) if valid_volume_changes else 0,
            'max_volume_change': max(valid_volume_changes) if valid_volume_changes else 0,
            'volume_change_std': stdev(valid_volume_changes) if len(valid_volume_changes) > 1 else 0,
            
            'avg_premium_change': mean(valid_premium_changes) if valid_premium_changes else 0,
            'max_premium_change': max(valid_premium_changes) if valid_premium_changes else 0,
            'premium_change_std': stdev(valid_premium_changes) if len(valid_premium_changes) > 1 else 0,
            
            'call_count': len(call_deviations),
            'put_count': len(put_deviations),
            'put_call_ratio': len(put_deviations) / len(call_deviations) if call_deviations else 0,
            
            'total_count': len(deviations),
            'anomaly_count': len(anomaly_deviations),
            'anomaly_percentage': (len(anomaly_deviations) / len(deviations)) * 100 if deviations else 0
        }
        
        # 成交量变化分布 - 分析大成交量区间的分布情况
        volume_bins = [0, 20, 50, 100, 200, float('inf')]
        volume_labels = ['0-20%', '20-50%', '50-100%', '100-200%', '>200%']
        volume_distribution = [0] * len(volume_labels)
        
        for vc in valid_volume_changes:
            for i, upper in enumerate(volume_bins[1:], 0):
                if vc < upper:
                    volume_distribution[i] += 1
                    break
        
        # 偏离率分布 - 分析不同偏离率区间的分布情况
        deviation_bins = [0, 2, 4, 6, 8, 10]
        deviation_labels = ['0-2%', '2-4%', '4-6%', '6-8%', '8-10%']
        deviation_distribution = [0] * len(deviation_labels)
        
        for dv in deviation_values:
            for i, upper in enumerate(deviation_bins[1:], 0):
                if dv < upper:
                    deviation_distribution[i] += 1
                    break
                elif i == len(deviation_bins) - 2 and dv <= deviation_bins[-1]:
                    deviation_distribution[i] += 1
                    break
        
        # 趋势分析 - 按时间分组数据，计算每个时间点的统计值
        # 首先按天分组
        from collections import defaultdict
        import time
        
        # 计算每天的数据
        daily_data = defaultdict(list)
        for d in deviations:
            # 使用日期作为键
            day_key = d.timestamp.strftime('%Y-%m-%d')
            daily_data[day_key].append(d)
        
        # 计算每天的统计指标
        trend_data = []
        for day, day_deviations in sorted(daily_data.items()):
            # 计算每天的平均偏离率
            day_dev_avg = mean([d.deviation_percent for d in day_deviations])
            
            # 计算每天的平均成交量变化率
            day_vol_changes = [d.volume_change_percent for d in day_deviations if d.volume_change_percent is not None]
            day_vol_avg = mean(day_vol_changes) if day_vol_changes else 0
            
            # 统计每天的异常数量和比例
            day_anomalies = len([d for d in day_deviations if d.is_anomaly])
            day_anomaly_pct = (day_anomalies / len(day_deviations)) * 100
            
            trend_data.append({
                'date': day,
                'timestamp': time.mktime(datetime.strptime(day, '%Y-%m-%d').timetuple()) * 1000,  # Unix时间戳(毫秒)
                'avg_deviation': day_dev_avg,
                'avg_volume_change': day_vol_avg,
                'anomaly_count': day_anomalies,
                'anomaly_percentage': day_anomaly_pct,
                'total_count': len(day_deviations)
            })
        
        # 添加到统计结果中
        statistics['volume_distribution'] = {
            'labels': volume_labels,
            'data': volume_distribution
        }
        
        statistics['deviation_distribution'] = {
            'labels': deviation_labels,
            'data': deviation_distribution
        }
        
        statistics['trend_analysis'] = trend_data
        
        result['statistics'] = statistics
        
        logger.info(f"偏离数据统计: 平均偏离率 {statistics['avg_deviation']:.2f}%, " +
                   f"平均成交量变化 {statistics['avg_volume_change']:.2f}%, " +
                   f"异常占比 {statistics['anomaly_percentage']:.2f}%")
    
    return result

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
        
def get_call_put_volume_analysis(symbol, time_period='15m', days=7, include_history=True):
    """
    获取期权成交量多空分析数据
    
    参数:
    symbol - 交易对符号
    time_period - 时间周期，默认'15m' ('15m', '1h', '4h', '1d', '7d')
    days - 数据天数
    include_history - 是否包含历史数据
    
    返回:
    {
        'call_put_ratio': 总的看涨/看跌比率,
        'volume_stats': {
            'total_volume': 总成交量,
            'call_volume': 看涨期权总成交量,
            'put_volume': 看跌期权总成交量,
            'call_volume_percent': 看涨期权成交量百分比,
            'put_volume_percent': 看跌期权成交量百分比,
            'volume_change_24h': 24小时成交量变化率,
            'call_volume_change': 看涨期权24小时成交量变化率,
            'put_volume_change': 看跌期权24小时成交量变化率
        },
        'exchange_data': {
            'deribit': {
                'call_volume': 看涨期权成交量,
                'put_volume': 看跌期权成交量,
                'ratio': 看涨/看跌比率
            },
            'binance': {...},
            'okx': {...}
        },
        'anomaly_stats': {
            'total_anomalies': 异常总数,
            'call_anomalies': 看涨期权异常数,
            'put_anomalies': 看跌期权异常数,
            'alert_level': 预警级别,
            'alert_trigger': 触发条件
        },
        'history': [
            {
                'timestamp': 时间戳,
                'call_put_ratio': 看涨/看跌比率,
                'call_volume': 看涨期权成交量,
                'put_volume': 看跌期权成交量,
                'market_price': 市场价格
            }
        ]
    }
    """
    try:
        # 检查是否需要模拟其他交易所的数据
        use_simulated_exchange_data = True
        
        # 查询系统设置表中是否有"use_simulated_exchange_data"设置
        try:
            from models import SystemSetting
            setting = SystemSetting.query.filter_by(setting_name='use_simulated_exchange_data').first()
            if setting:
                use_simulated_exchange_data = setting.get_typed_value() in (True, 'true', 'True', '1')
        except Exception as e:
            logger.warning(f"获取use_simulated_exchange_data设置时出错: {str(e)}，将使用默认值True")
            
        logger.info(f"使用模拟交易所数据: {use_simulated_exchange_data}")
        # 设置时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # 查询所有交易所的数据
        exchanges = ['deribit', 'binance', 'okx']
        
        # 获取每个交易所的看涨/看跌期权成交量数据
        exchange_data = {}
        total_call_volume = 0
        total_put_volume = 0
        anomaly_call_count = 0
        anomaly_put_count = 0
        
        # 处理每个交易所的数据
        for exchange in exchanges:
            # 获取该交易所的期权数据
            call_data = StrikeDeviationMonitor.query.filter(
                StrikeDeviationMonitor.symbol == symbol,
                StrikeDeviationMonitor.timestamp >= start_time,
                StrikeDeviationMonitor.timestamp <= end_time,
                StrikeDeviationMonitor.time_period == time_period,
                StrikeDeviationMonitor.exchange == exchange,
                StrikeDeviationMonitor.option_type == 'call'
            ).all()
            
            put_data = StrikeDeviationMonitor.query.filter(
                StrikeDeviationMonitor.symbol == symbol,
                StrikeDeviationMonitor.timestamp >= start_time,
                StrikeDeviationMonitor.timestamp <= end_time,
                StrikeDeviationMonitor.time_period == time_period,
                StrikeDeviationMonitor.exchange == exchange,
                StrikeDeviationMonitor.option_type == 'put'
            ).all()
            
            # 计算该交易所的成交量统计
            call_volume = sum(item.volume for item in call_data)
            put_volume = sum(item.volume for item in put_data)
            ratio = call_volume / put_volume if put_volume > 0 else 1.0
            
            # 计算异常数据
            anomaly_calls = sum(1 for item in call_data if item.is_anomaly)
            anomaly_puts = sum(1 for item in put_data if item.is_anomaly)
            
            # 添加到交易所数据
            exchange_data[exchange] = {
                'call_volume': call_volume,
                'put_volume': put_volume,
                'ratio': ratio,
                'anomaly_calls': anomaly_calls,
                'anomaly_puts': anomaly_puts
            }
            
            # 累加到总量
            total_call_volume += call_volume
            total_put_volume += put_volume
            anomaly_call_count += anomaly_calls
            anomaly_put_count += anomaly_puts
            
        # 禁用模拟数据，仅使用真实API数据
        # 2025.05.06: 停用模拟数据，改为使用真实OKX交易所数据
        logger.info(f"使用真实交易所数据: {exchange_data.keys()}")
        
        # 计算总体统计数据
        total_volume = total_call_volume + total_put_volume
        call_volume_percent = (total_call_volume / total_volume * 100) if total_volume > 0 else 50
        put_volume_percent = (total_put_volume / total_volume * 100) if total_volume > 0 else 50
        call_put_ratio = total_call_volume / total_put_volume if total_put_volume > 0 else 1.0
        
        # 计算24小时变化率 (与前一天对比)
        yesterday_end = end_time - timedelta(days=1)
        yesterday_start = yesterday_end - timedelta(days=1)
        
        yesterday_data = StrikeDeviationMonitor.query.filter(
            StrikeDeviationMonitor.symbol == symbol,
            StrikeDeviationMonitor.timestamp >= yesterday_start,
            StrikeDeviationMonitor.timestamp <= yesterday_end,
            StrikeDeviationMonitor.time_period == time_period
        ).all()
        
        yesterday_call_volume = sum(item.volume for item in yesterday_data if item.option_type == 'call')
        yesterday_put_volume = sum(item.volume for item in yesterday_data if item.option_type == 'put')
        
        # 计算变化率
        call_volume_change = ((total_call_volume - yesterday_call_volume) / yesterday_call_volume * 100) if yesterday_call_volume > 0 else 100
        put_volume_change = ((total_put_volume - yesterday_put_volume) / yesterday_put_volume * 100) if yesterday_put_volume > 0 else 100
        total_volume_change = ((total_volume - (yesterday_call_volume + yesterday_put_volume)) / 
                              (yesterday_call_volume + yesterday_put_volume) * 100) if (yesterday_call_volume + yesterday_put_volume) > 0 else 100
        
        # 生成预警信号和级别
        alert_level = 'normal'
        alert_trigger = '无'
        
        # 根据规则判断预警级别 
        # 多空比例变化过大或成交量变化过大
        if call_put_ratio > 1.5 or call_put_ratio < 0.65:
            alert_level = 'attention'
            alert_trigger = f'多空比例异常: {call_put_ratio:.2f}'
        
        if abs(total_volume_change) > 100:
            alert_level = 'warning'
            alert_trigger = f'成交量异常波动: {total_volume_change:.1f}%'
            
        # 如果成交量变化很大且多空比例显著变化，则为严重预警
        if abs(total_volume_change) > 150 and (call_put_ratio > 1.8 or call_put_ratio < 0.5):
            alert_level = 'severe'
            alert_trigger = f'成交量剧增且多空显著偏离: 成交量变化 {total_volume_change:.1f}%, 多空比 {call_put_ratio:.2f}'
            
        # 异常比例过高
        total_anomalies = anomaly_call_count + anomaly_put_count
        total_contracts = len(yesterday_data)
        if total_contracts > 0 and total_anomalies / total_contracts > 0.5:
            if alert_level != 'severe':
                alert_level = 'warning'
                alert_trigger = f'异常合约比例过高: {total_anomalies}/{total_contracts}'
        
        # 创建结果对象
        result = {
            'call_put_ratio': call_put_ratio,
            'volume_stats': {
                'total_volume': total_volume,
                'call_volume': total_call_volume,
                'put_volume': total_put_volume,
                'call_volume_percent': call_volume_percent,
                'put_volume_percent': put_volume_percent,
                'volume_change_24h': total_volume_change,
                'call_volume_change': call_volume_change,
                'put_volume_change': put_volume_change
            },
            'exchange_data': exchange_data,
            'anomaly_stats': {
                'total_anomalies': anomaly_call_count + anomaly_put_count,
                'call_anomalies': anomaly_call_count,
                'put_anomalies': anomaly_put_count,
                'alert_level': alert_level,
                'alert_trigger': alert_trigger
            }
        }
        
        # 如果需要包含历史数据
        if include_history:
            history = []
            
            # 获取历史数据
            # 按天聚合数据
            time_range = end_time - start_time
            delta = timedelta(hours=8)  # 以8小时为间隔
            intervals = int(time_range.total_seconds() / delta.total_seconds())
            
            # 保护措施，确保间隔数量不超过30
            intervals = min(intervals, 30)
            
            # 获取市场价格基准线（用于模拟数据）
            market_price_base = 0
            try:
                from services.data_service import get_base_price_for_symbol
                market_price_base = get_base_price_for_symbol(symbol)
            except:
                # 默认价格
                market_price_base = 90000 if symbol == 'BTC' else 1800 if symbol == 'ETH' else 1.0
            
            # 2025.05.06: 停用模拟数据，改为完全使用真实数据
            logger.info(f"分析{symbol}在{time_period}时间周期的真实数据，数据区间: {days}天")
            
            # 生成历史数据
            for i in range(intervals):
                period_end = end_time - (delta * i)
                period_start = period_end - delta
                
                # 查询该时间段的数据
                period_data = StrikeDeviationMonitor.query.filter(
                    StrikeDeviationMonitor.symbol == symbol,
                    StrikeDeviationMonitor.timestamp >= period_start,
                    StrikeDeviationMonitor.timestamp <= period_end,
                    StrikeDeviationMonitor.time_period == time_period
                ).all()
                
                # 计算该段的统计数据
                period_call_volume = sum(item.volume for item in period_data if item.option_type == 'call')
                period_put_volume = sum(item.volume for item in period_data if item.option_type == 'put')
                real_period_ratio = period_call_volume / period_put_volume if period_put_volume > 0 else 1.0
                
                # 获取市场价格
                real_market_prices = [item.market_price for item in period_data if item.market_price]
                real_market_price = np.mean(real_market_prices) if real_market_prices else 0
                
                # 是否使用真实数据
                if period_call_volume > 0 and period_put_volume > 0 and real_market_price > 0:
                    # 使用真实数据
                    history.append({
                        'timestamp': period_end.strftime('%Y-%m-%d %H:%M'),
                        'call_put_ratio': real_period_ratio,
                        'call_volume': period_call_volume,
                        'put_volume': period_put_volume,
                        'market_price': real_market_price
                    })
                else:
                    # 添加空记录
                    history.append({
                        'timestamp': period_end.strftime('%Y-%m-%d %H:%M'),
                        'call_put_ratio': 1.0,
                        'call_volume': 0,
                        'put_volume': 0,
                        'market_price': 0
                    })
            
            # 按时间正序排列
            history.reverse()
            result['history'] = history
            
        return result
            
    except Exception as e:
        logger.error(f"获取多空成交量分析数据时出错: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'call_put_ratio': 1.0,
            'volume_stats': {
                'total_volume': 0,
                'call_volume': 0,
                'put_volume': 0,
                'call_volume_percent': 50,
                'put_volume_percent': 50,
                'volume_change_24h': 0,
                'call_volume_change': 0,
                'put_volume_change': 0
            },
            'exchange_data': {
                'deribit': {'call_volume': 0, 'put_volume': 0, 'ratio': 1.0, 'anomaly_calls': 0, 'anomaly_puts': 0},
                'binance': {'call_volume': 0, 'put_volume': 0, 'ratio': 1.0, 'anomaly_calls': 0, 'anomaly_puts': 0},
                'okx': {'call_volume': 0, 'put_volume': 0, 'ratio': 1.0, 'anomaly_calls': 0, 'anomaly_puts': 0}
            },
            'anomaly_stats': {
                'total_anomalies': 0,
                'call_anomalies': 0,
                'put_anomalies': 0,
                'alert_level': 'normal',
                'alert_trigger': '数据获取错误'
            }
        }
    
    return False