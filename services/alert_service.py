import logging
from datetime import datetime

from app import db
from models import Alert, AlertThreshold
from config import Config

logger = logging.getLogger(__name__)

def check_alert_thresholds(risk_indicator):
    """
    Check if any risk thresholds are crossed and generate alerts
    根据风险指标的时间周期选择对应的阈值
    """
    try:
        logger.info(f"Checking alert thresholds for {risk_indicator.symbol} ({risk_indicator.time_period})")
        
        # Get or create alert thresholds
        thresholds = {}
        time_period = risk_indicator.time_period
        
        # 确保时间周期有效
        if time_period not in Config.TIME_PERIODS:
            time_period = '4h'  # 默认使用4小时
            
        for indicator_name, periods in Config.DEFAULT_ALERT_THRESHOLDS.items():
            # 获取该指标在当前时间周期的阈值
            threshold = AlertThreshold.query.filter_by(
                indicator=indicator_name,
                time_period=time_period
            ).first()
            
            if not threshold:
                # 从配置中获取默认值
                default_levels = periods.get(time_period, periods.get('4h'))
                
                # 创建新的阈值设置
                threshold = AlertThreshold(
                    indicator=indicator_name,
                    time_period=time_period,
                    attention_threshold=default_levels['attention'],
                    warning_threshold=default_levels['warning'],
                    severe_threshold=default_levels['severe'],
                    is_enabled=True
                )
                db.session.add(threshold)
                db.session.commit()
            
            thresholds[indicator_name] = threshold
        
        # Check Volaxivity threshold
        if hasattr(risk_indicator, 'volaxivity') and risk_indicator.volaxivity is not None:
            check_individual_threshold(
                risk_indicator.symbol,
                'volaxivity',
                risk_indicator.volaxivity,
                thresholds['volaxivity']
            )
        
        # Check Volatility Skew threshold
        if hasattr(risk_indicator, 'volatility_skew') and risk_indicator.volatility_skew is not None:
            check_individual_threshold(
                risk_indicator.symbol,
                'volatility_skew',
                risk_indicator.volatility_skew,
                thresholds['volatility_skew']
            )
        
        # Check Put/Call Ratio threshold
        if hasattr(risk_indicator, 'put_call_ratio') and risk_indicator.put_call_ratio is not None:
            check_individual_threshold(
                risk_indicator.symbol,
                'put_call_ratio',
                risk_indicator.put_call_ratio,
                thresholds['put_call_ratio']
            )
        
        # Check Reflexivity Indicator threshold
        if hasattr(risk_indicator, 'reflexivity_indicator') and risk_indicator.reflexivity_indicator is not None:
            check_individual_threshold(
                risk_indicator.symbol,
                'reflexivity_indicator',
                risk_indicator.reflexivity_indicator,
                thresholds['reflexivity_indicator']
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking alert thresholds: {str(e)}")
        db.session.rollback()
        return False

def check_individual_threshold(symbol, indicator_name, current_value, threshold):
    """
    Check an individual indicator against its thresholds
    Generate an alert if any threshold is exceeded
    """
    if not threshold.is_enabled:
        return
    
    alert_type = None
    threshold_value = None
    
    # Check from most severe to least severe
    if current_value >= threshold.severe_threshold:
        alert_type = 'severe'
        threshold_value = threshold.severe_threshold
    elif current_value >= threshold.warning_threshold:
        alert_type = 'warning'
        threshold_value = threshold.warning_threshold
    elif current_value >= threshold.attention_threshold:
        alert_type = 'attention'
        threshold_value = threshold.attention_threshold
    
    if alert_type:
        # Create alert message
        message = f"{symbol} {indicator_name.capitalize()} ({threshold.time_period}) crossed {alert_type} threshold ({threshold_value:.2f})"
        
        # Check if a similar alert already exists (avoid duplicates)
        existing_alert = Alert.query.filter_by(
            symbol=symbol,
            indicator=indicator_name,
            time_period=threshold.time_period,
            alert_type=alert_type,
            is_acknowledged=False
        ).first()
        
        if not existing_alert:
            # Create new alert
            alert = Alert(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                time_period=threshold.time_period,
                alert_type=alert_type,
                message=message,
                indicator=indicator_name,
                value=current_value,
                threshold=threshold_value,
                is_acknowledged=False
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.info(f"Generated {alert_type} alert: {message}")

def get_active_alerts(symbol=None, limit=100):
    """
    Get active (unacknowledged) alerts
    If symbol is provided, only get alerts for that symbol
    """
    query = Alert.query.filter_by(is_acknowledged=False)
    
    if symbol:
        query = query.filter_by(symbol=symbol)
    
    return query.order_by(Alert.timestamp.desc()).limit(limit).all()

def acknowledge_alert(alert_id):
    """
    Mark an alert as acknowledged
    """
    try:
        alert = Alert.query.get(alert_id)
        
        if alert:
            alert.is_acknowledged = True
            db.session.commit()
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        else:
            logger.warning(f"Alert {alert_id} not found")
            return False
            
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        db.session.rollback()
        return False

def update_alert_threshold(indicator, time_period, attention, warning, severe):
    """
    Update alert threshold values for specific indicator and time period
    """
    try:
        threshold = AlertThreshold.query.filter_by(
            indicator=indicator,
            time_period=time_period
        ).first()
        
        if not threshold:
            # Create new threshold
            threshold = AlertThreshold(
                indicator=indicator,
                time_period=time_period,
                attention_threshold=attention,
                warning_threshold=warning,
                severe_threshold=severe,
                is_enabled=True
            )
            db.session.add(threshold)
        else:
            # Update existing threshold
            threshold.attention_threshold = attention
            threshold.warning_threshold = warning
            threshold.severe_threshold = severe
        
        db.session.commit()
        logger.info(f"Updated thresholds for {indicator} ({time_period})")
        return True
            
    except Exception as e:
        logger.error(f"Error updating threshold: {str(e)}")
        db.session.rollback()
        return False
        
def get_alert_thresholds_by_period(indicator=None, time_period='4h'):
    """
    获取指定时间周期的所有阈值设置
    如果指定了indicator，则只返回该指标的阈值
    """
    try:
        query = AlertThreshold.query.filter_by(time_period=time_period)
        
        if indicator:
            query = query.filter_by(indicator=indicator)
            
        return query.all()
        
    except Exception as e:
        logger.error(f"Error getting alert thresholds: {str(e)}")
        return []
from datetime import datetime, timedelta
from app import db, app
from models import Alert, AlertThreshold
from config import Config
import logging

# Set up logging
logger = logging.getLogger(__name__)

# 警报缓存超时时间（秒）
ALERT_CACHE_TIMEOUT = 60

def get_active_alerts(symbol=None, time_period=None, indicator=None, limit=50):
    """
    获取活跃的警报（未确认的）
    
    参数:
        symbol (str, optional): 筛选特定交易对的警报
        time_period (str, optional): 筛选特定时间周期的警报
        indicator (str, optional): 筛选特定指标的警报
        limit (int): 返回结果的最大数量
        
    返回:
        list: 警报对象列表
    """
    try:
        # 缓存键
        cache_key = f"active_alerts_{symbol}_{time_period}_{indicator}_{limit}"
        cache_time_key = f"{cache_key}_time"
        
        # 获取缓存时间
        cache_time = getattr(app, cache_time_key, None)
        
        # 检查缓存是否有效
        if cache_time and (datetime.utcnow() - cache_time).total_seconds() < ALERT_CACHE_TIMEOUT:
            cached_alerts = getattr(app, cache_key, None)
            if cached_alerts is not None:
                return cached_alerts
        
        # 构建查询
        query = Alert.query.filter_by(is_acknowledged=False)
        
        if symbol:
            query = query.filter_by(symbol=symbol)
        
        if time_period:
            query = query.filter_by(time_period=time_period)
        
        if indicator:
            query = query.filter_by(indicator=indicator)
        
        # 执行查询
        alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()
        
        # 更新缓存
        setattr(app, cache_key, alerts)
        setattr(app, cache_time_key, datetime.utcnow())
        
        return alerts
    except Exception as e:
        logger.error(f"Error getting active alerts: {str(e)}")
        return []

def acknowledge_alert(alert_id):
    """
    确认警报
    
    参数:
        alert_id (int): 警报ID
        
    返回:
        bool: 操作是否成功
    """
    try:
        alert = Alert.query.get(alert_id)
        
        if not alert:
            return False
        
        alert.is_acknowledged = True
        db.session.commit()
        
        # 清除可能受此操作影响的缓存
        for key in dir(app):
            if key.startswith('active_alerts_'):
                delattr(app, key)
        
        return True
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        db.session.rollback()
        return False

def update_alert_threshold(indicator, time_period, attention, warning, severe):
    """
    更新警报阈值设置
    
    参数:
        indicator (str): 指标名称
        time_period (str): 时间周期
        attention (float): 注意级别阈值
        warning (float): 警告级别阈值
        severe (float): 严重级别阈值
        
    返回:
        bool: 操作是否成功
    """
    try:
        # 查找现有的阈值设置
        threshold = AlertThreshold.query.filter_by(
            indicator=indicator,
            time_period=time_period
        ).first()
        
        if threshold:
            # 更新现有阈值
            threshold.attention_threshold = attention
            threshold.warning_threshold = warning
            threshold.severe_threshold = severe
        else:
            # 创建新的阈值设置
            threshold = AlertThreshold(
                indicator=indicator,
                time_period=time_period,
                attention_threshold=attention,
                warning_threshold=warning,
                severe_threshold=severe
            )
            db.session.add(threshold)
        
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating alert threshold: {str(e)}")
        db.session.rollback()
        return False

def create_alert(symbol, alert_type, message, indicator, value, threshold, time_period='15m'):
    """
    创建新的警报
    
    参数:
        symbol (str): 交易对符号
        alert_type (str): 警报类型 ('attention', 'warning', 'severe')
        message (str): 警报消息
        indicator (str): 触发警报的指标
        value (float): 指标当前值
        threshold (float): 触发阈值
        time_period (str, optional): 时间周期，默认为'15m'
        
    返回:
        Alert: 创建的警报对象，如果创建失败则返回None
    """
    try:
        # 检查是否已存在相同的未确认警报
        existing_alert = Alert.query.filter_by(
            symbol=symbol,
            indicator=indicator,
            alert_type=alert_type,
            is_acknowledged=False,
            time_period=time_period
        ).order_by(Alert.timestamp.desc()).first()
        
        # 如果存在类似的警报并且创建时间在1小时内，则不创建新警报
        if existing_alert and (datetime.utcnow() - existing_alert.timestamp).total_seconds() < 3600:
            return existing_alert
        
        # 创建新警报
        alert = Alert(
            symbol=symbol,
            alert_type=alert_type,
            message=message,
            indicator=indicator,
            value=value,
            threshold=threshold,
            time_period=time_period
        )
        
        db.session.add(alert)
        db.session.commit()
        
        # 清除可能受此操作影响的缓存
        for key in dir(app):
            if key.startswith('active_alerts_'):
                delattr(app, key)
        
        return alert
    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}")
        db.session.rollback()
        return None

def get_alert_thresholds(time_period='15m'):
    """
    获取特定时间周期的所有警报阈值设置
    
    参数:
        time_period (str): 时间周期
        
    返回:
        dict: 以指标名称为键的阈值设置字典
    """
    try:
        # 缓存键
        cache_key = f"alert_thresholds_{time_period}"
        cache_time_key = f"{cache_key}_time"
        
        # 获取缓存时间
        cache_time = getattr(app, cache_time_key, None)
        
        # 检查缓存是否有效
        if cache_time and (datetime.utcnow() - cache_time).total_seconds() < ALERT_CACHE_TIMEOUT * 5:  # 阈值缓存时间较长
            cached_thresholds = getattr(app, cache_key, None)
            if cached_thresholds is not None:
                return cached_thresholds
        
        # 从数据库获取阈值设置
        thresholds = AlertThreshold.query.filter_by(time_period=time_period).all()
        
        # 构建结果字典
        result = {}
        for t in thresholds:
            result[t.indicator] = {
                'attention': t.attention_threshold,
                'warning': t.warning_threshold,
                'severe': t.severe_threshold
            }
        
        # 合并默认阈值
        for indicator, periods in Config.DEFAULT_ALERT_THRESHOLDS.items():
            if indicator not in result and time_period in periods:
                result[indicator] = periods[time_period]
        
        # 更新缓存
        setattr(app, cache_key, result)
        setattr(app, cache_time_key, datetime.utcnow())
        
        return result
    except Exception as e:
        logger.error(f"Error getting alert thresholds: {str(e)}")
        
        # 出错时返回默认阈值
        result = {}
        for indicator, periods in Config.DEFAULT_ALERT_THRESHOLDS.items():
            if time_period in periods:
                result[indicator] = periods[time_period]
        
        return result
