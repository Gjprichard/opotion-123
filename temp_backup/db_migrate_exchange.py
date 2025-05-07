"""
数据库迁移脚本 - 添加交易所支持
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_exchange_columns():
    """向StrikeDeviationMonitor和DeviationAlert表添加exchange列"""
    try:
        # 使用环境变量获取数据库连接信息
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            logger.error("数据库URL不可用")
            return False

        # 使用psycopg2直接从URL连接
        logger.info(f"使用URL连接到数据库")

        # 建立连接
        conn = psycopg2.connect(db_url)
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查StrikeDeviationMonitor表是否存在
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='strike_deviation_monitor')")
        if cursor.fetchone()[0]:
            logger.info("StrikeDeviationMonitor表存在，检查exchange列...")
            
            # 检查exchange列是否已存在
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='strike_deviation_monitor' AND column_name='exchange')")
            if not cursor.fetchone()[0]:
                logger.info("向StrikeDeviationMonitor表添加exchange列...")
                cursor.execute("ALTER TABLE strike_deviation_monitor ADD COLUMN exchange VARCHAR(20) DEFAULT 'deribit' NOT NULL")
                cursor.execute("CREATE INDEX ix_strike_deviation_monitor_exchange ON strike_deviation_monitor (exchange)")
                logger.info("成功添加exchange列到StrikeDeviationMonitor表")
            else:
                logger.info("StrikeDeviationMonitor表已有exchange列")
        else:
            logger.warning("StrikeDeviationMonitor表不存在，跳过")
            
        # 检查DeviationAlert表是否存在
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='deviation_alert')")
        if cursor.fetchone()[0]:
            logger.info("DeviationAlert表存在，检查exchange列...")
            
            # 检查exchange列是否已存在
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='deviation_alert' AND column_name='exchange')")
            if not cursor.fetchone()[0]:
                logger.info("向DeviationAlert表添加exchange列...")
                cursor.execute("ALTER TABLE deviation_alert ADD COLUMN exchange VARCHAR(20) DEFAULT 'deribit' NOT NULL")
                cursor.execute("CREATE INDEX ix_deviation_alert_exchange ON deviation_alert (exchange)")
                logger.info("成功添加exchange列到DeviationAlert表")
            else:
                logger.info("DeviationAlert表已有exchange列")
                
            # 检查option_type列是否已存在
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='deviation_alert' AND column_name='option_type')")
            if not cursor.fetchone()[0]:
                logger.info("向DeviationAlert表添加option_type列...")
                cursor.execute("ALTER TABLE deviation_alert ADD COLUMN option_type VARCHAR(4)")
                logger.info("成功添加option_type列到DeviationAlert表")
            else:
                logger.info("DeviationAlert表已有option_type列")
        else:
            logger.warning("DeviationAlert表不存在，跳过")
            
        cursor.close()
        conn.close()
        logger.info("数据库迁移成功完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    result = add_exchange_columns()
    if result:
        print("数据库迁移成功！")
    else:
        print("数据库迁移失败，请检查日志")