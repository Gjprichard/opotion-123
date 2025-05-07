import logging
from flask_apscheduler import APScheduler
from datetime import datetime

from app import db
from services.data_service import DataService
from services.risk_service import RiskService

# 配置日志
logger = logging.getLogger(__name__)

# 初始化服务
data_service = DataService()
risk_service = RiskService()

def configure_scheduler(scheduler: APScheduler) -> None:
    """配置定时任务调度器"""
    
    # 添加默认任务
    scheduler.add_job(
        id='fetch_option_data',
        func=fetch_option_data_task,
        trigger='interval',
        minutes=5,
        replace_existing=True
    )
    
    scheduler.add_job(
        id='calculate_risk_indicators',
        func=calculate_risk_indicators_task,
        trigger='interval',
        minutes=10,
        replace_existing=True
    )
    
    scheduler.add_job(
        id='cleanup_old_data',
        func=cleanup_old_data_task,
        trigger='cron',
        hour=0,  # 每天0点执行
        replace_existing=True
    )
    
    logger.info("已配置定时任务")

def fetch_option_data_task() -> None:
    """定时任务: 获取最新的期权数据"""
    try:
        logger.info("正在执行计划任务: 获取最新期权数据")
        
        # 获取BTC期权数据
        btc_count = data_service.fetch_and_store_option_data("BTC")
        logger.info(f"获取并存储了 {btc_count} 条BTC期权数据")
        
        # 获取ETH期权数据
        eth_count = data_service.fetch_and_store_option_data("ETH")
        logger.info(f"获取并存储了 {eth_count} 条ETH期权数据")
        
    except Exception as e:
        logger.error(f"获取期权数据任务出错: {str(e)}")

def calculate_risk_indicators_task() -> None:
    """定时任务: 计算风险指标"""
    try:
        logger.info("正在执行计划任务: 计算风险指标")
        
        # 计算不同时间周期的风险指标
        time_periods = ['15m', '1h', '4h', '1d', '7d']
        
        for symbol in ["BTC", "ETH"]:
            for period in time_periods:
                logger.info(f"计算 {symbol} 的风险指标 (时间周期: {period})")
                risk_service.calculate_risk_indicators(symbol, period)
        
    except Exception as e:
        logger.error(f"计算风险指标任务出错: {str(e)}")

def cleanup_old_data_task() -> None:
    """定时任务: 清理旧数据"""
    try:
        logger.info("正在执行计划任务: 清理旧数据")
        
        # 清理30天前的数据
        deleted_count = data_service.cleanup_old_data(days=30)
        logger.info(f"清理了 {deleted_count} 条旧数据")
        
    except Exception as e:
        logger.error(f"清理旧数据任务出错: {str(e)}")