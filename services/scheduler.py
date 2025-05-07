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
        
        # 添加数据获取任务 - 每5分钟执行一次
        scheduler.add_job(id='fetch_option_data', func=fetch_option_data, 
                          trigger='interval', minutes=5)
        
        # 添加数据计算任务 - 每10分钟执行一次
        scheduler.add_job(id='calculate_all_data', func=calculate_all_data,
                          trigger='interval', minutes=10)
        
        scheduler.add_job(id='cleanup_old_data', func=cleanup_old_data, 
                          trigger='cron', hour=1)  # 每天凌晨1点清理旧数据
        
        logger.info("Scheduler initialized and jobs added")
        
        # Run initial data fetch for all symbols
        update_all_option_data()
        
    except Exception as e:
        logger.error(f"Error initializing scheduler: {str(e)}")
        
def fetch_option_data():
    """只获取期权数据，不进行计算"""
    logger.info("正在执行计划任务: 获取最新期权数据")
    
    # 导入应用实例以使用应用上下文
    from app import app
    
    # 在应用上下文中执行数据库操作
    with app.app_context():
        for symbol in Config.TRACKED_SYMBOLS:
            try:
                # 只获取期权数据
                success = fetch_latest_option_data(symbol)
                
                if success:
                    logger.info(f"已成功获取 {symbol} 的最新期权数据")
                else:
                    logger.warning(f"获取 {symbol} 期权数据失败")
                    
                # 添加小延迟，避免对数据源造成过大压力
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"获取 {symbol} 期权数据时出错: {str(e)}")

def calculate_all_data():
    """只计算风险指标和偏离指标，不获取新数据"""
    logger.info("正在执行计划任务: 计算风险指标和偏离指标")
    
    # 导入应用实例以使用应用上下文
    from app import app
    
    # 在应用上下文中执行数据库操作
    with app.app_context():
        for symbol in Config.TRACKED_SYMBOLS:
            try:
                # 计算风险指标
                calculate_risk_indicators(symbol)
                
                # 计算期权执行价偏离指标
                calculate_deviation_metrics(symbol)
                
                logger.info(f"已成功计算 {symbol} 的风险指标和偏离指标")
                    
            except Exception as e:
                logger.error(f"计算 {symbol} 指标时出错: {str(e)}")

def update_all_option_data():
    """兼容旧代码的函数，同时获取数据并计算指标"""
    logger.info("Running scheduled update of option data")
    
    # 导入应用实例以使用应用上下文
    from app import app
    
    # 在应用上下文中执行数据库操作
    with app.app_context():
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
