import logging
import time
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from services.data_service import fetch_latest_option_data, cleanup_old_data
from services.risk_calculator import calculate_risk_indicators
from services.deviation_monitor_service import calculate_deviation_metrics
from config import Config

logger = logging.getLogger(__name__)
scheduler = APScheduler()

def init_scheduler(app):
    """Initialize the scheduler with jobs"""
    try:
        scheduler.init_app(app)
        scheduler.start()
        
        # Add jobs to the scheduler
        scheduler.add_job(id='update_option_data', func=update_all_option_data, 
                          trigger='interval', minutes=15)
        
        scheduler.add_job(id='cleanup_old_data', func=cleanup_old_data, 
                          trigger='cron', hour=1)  # Run daily at 1 AM
        
        logger.info("Scheduler initialized and jobs added")
        
        # Run initial data fetch for all symbols
        update_all_option_data()
        
    except Exception as e:
        logger.error(f"Error initializing scheduler: {str(e)}")
        
def update_all_option_data():
    """Update option data for all tracked symbols"""
    logger.info("Running scheduled update of option data")
    
    for symbol in Config.TRACKED_SYMBOLS:
        try:
            # Fetch new option data
            success = fetch_latest_option_data(symbol)
            
            if success:
                # Calculate risk indicators
                calculate_risk_indicators(symbol)
                
                # Calculate strike price deviation metrics
                calculate_deviation_metrics(symbol)
                
                logger.info(f"Updated option data, risk indicators and deviation metrics for {symbol}")
            else:
                logger.warning(f"Failed to update option data for {symbol}")
                
            # Add a small delay between symbols to avoid overwhelming the data source
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error updating option data for {symbol}: {str(e)}")
