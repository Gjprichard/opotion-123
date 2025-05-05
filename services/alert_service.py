import logging
from datetime import datetime

from app import db
from models import Alert, AlertThreshold
from config import Config

logger = logging.getLogger(__name__)

def check_alert_thresholds(risk_indicator):
    """
    Check if any risk thresholds are crossed and generate alerts
    """
    try:
        logger.info(f"Checking alert thresholds for {risk_indicator.symbol}")
        
        # Get or create alert thresholds
        thresholds = {}
        for indicator_name, levels in Config.DEFAULT_ALERT_THRESHOLDS.items():
            threshold = AlertThreshold.query.filter_by(indicator=indicator_name).first()
            
            if not threshold:
                # Create with default values
                threshold = AlertThreshold(
                    indicator=indicator_name,
                    attention_threshold=levels['attention'],
                    warning_threshold=levels['warning'],
                    severe_threshold=levels['severe'],
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
        message = f"{symbol} {indicator_name.capitalize()} crossed {alert_type} threshold ({threshold_value:.2f})"
        
        # Check if a similar alert already exists (avoid duplicates)
        existing_alert = Alert.query.filter_by(
            symbol=symbol,
            indicator=indicator_name,
            alert_type=alert_type,
            is_acknowledged=False
        ).first()
        
        if not existing_alert:
            # Create new alert
            alert = Alert(
                symbol=symbol,
                timestamp=datetime.utcnow(),
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

def update_alert_threshold(indicator, attention, warning, severe):
    """
    Update alert threshold values
    """
    try:
        threshold = AlertThreshold.query.filter_by(indicator=indicator).first()
        
        if not threshold:
            # Create new threshold
            threshold = AlertThreshold(
                indicator=indicator,
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
        logger.info(f"Updated thresholds for {indicator}")
        return True
            
    except Exception as e:
        logger.error(f"Error updating threshold: {str(e)}")
        db.session.rollback()
        return False
