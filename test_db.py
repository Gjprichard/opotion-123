import sys
import os
import logging
from datetime import datetime

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入应用
from app import app, db
from models import RiskIndicator

def test_database_connection():
    """测试数据库连接"""
    try:
        with app.app_context():
            # 尝试执行一个简单查询
            count = db.session.query(db.func.count(RiskIndicator.id)).scalar()
            logger.info(f"数据库中有 {count} 条风险指标记录")
            
            # 获取数据库连接信息
            logger.info(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("开始测试数据库连接...")
    success = test_database_connection()
    
    if success:
        logger.info("数据库连接测试成功")
    else:
        logger.error("数据库连接测试失败")