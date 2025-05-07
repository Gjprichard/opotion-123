import sys
import os
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import func

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入Flask应用和其他依赖
from app import app, db
from models import RiskIndicator
from services.risk_service import RiskService

def test_get_historical_risk_indicators():
    """测试获取历史风险指标的功能"""
    with app.app_context():
        try:
            # 创建RiskService实例
            risk_service = RiskService()
            
            # 测试不同的参数组合
            symbol = 'BTC'
            time_periods = ['15m', '1h', '4h', '1d']
            
            for time_period in time_periods:
                logger.info(f"测试获取{symbol}的{time_period}历史风险指标")
                
                # 获取最近30天的历史数据
                indicators = risk_service.get_historical_risk_indicators(symbol, time_period, 30)
                
                # 输出结果
                logger.info(f"获取到{len(indicators)}条历史风险指标")
                
                # 显示第一条记录的内容（如果有）
                if indicators:
                    logger.info(f"第一条记录: {json.dumps(indicators[0], indent=2, default=str)}")
                else:
                    logger.warning(f"没有找到{symbol}的{time_period}历史风险指标")
                
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}", exc_info=True)

def test_get_latest_risk_indicators():
    """测试获取最新风险指标的功能"""
    with app.app_context():
        try:
            # 创建RiskService实例
            risk_service = RiskService()
            
            # 测试不同的参数组合
            symbols = ['BTC', 'ETH']
            time_periods = ['15m', '1h', '4h', '1d']
            
            for symbol in symbols:
                for time_period in time_periods:
                    logger.info(f"测试获取{symbol}的{time_period}最新风险指标")
                    
                    # 获取最新的风险指标
                    indicator = risk_service.get_latest_risk_indicators(symbol, time_period)
                    
                    # 输出结果
                    if indicator:
                        logger.info(f"获取到{symbol}的{time_period}最新风险指标: {json.dumps(indicator, indent=2, default=str)}")
                    else:
                        logger.warning(f"没有找到{symbol}的{time_period}最新风险指标")
                    
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}", exc_info=True)

def check_database_connection():
    """检查数据库连接和查询"""
    with app.app_context():
        try:
            # 尝试一个简单的查询
            count = db.session.query(func.count(RiskIndicator.id)).scalar()
            logger.info(f"数据库中有{count}条风险指标记录")
            
            # 检查每个交易对和时间周期的记录数
            symbols = ['BTC', 'ETH']
            time_periods = ['15m', '1h', '4h', '1d', '7d', '30d']
            
            for symbol in symbols:
                for period in time_periods:
                    period_count = db.session.query(func.count(RiskIndicator.id)).filter(
                        RiskIndicator.symbol == symbol,
                        RiskIndicator.time_period == period
                    ).scalar()
                    
                    logger.info(f"{symbol} {period}: {period_count}条记录")
            
        except Exception as e:
            logger.error(f"数据库查询出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("开始测试RiskService...")
    
    # 测试数据库连接
    check_database_connection()
    
    # 测试获取最新风险指标
    test_get_latest_risk_indicators()
    
    # 测试获取历史风险指标
    test_get_historical_risk_indicators()
    
    logger.info("RiskService测试完成")