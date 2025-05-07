"""
数据库迁移脚本 - 为OptionData表添加exchange列
"""
import os
import psycopg2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def execute_migration():
    """执行数据库迁移：为OptionData表添加exchange列"""
    try:
        # 从环境变量获取数据库连接信息
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("未找到数据库连接URL环境变量")
            return False
            
        # 连接到数据库
        logger.info(f"正在连接到数据库...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # 检查是否已存在exchange列
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'option_data' 
            AND column_name = 'exchange'
        """)
        
        # 如果列不存在，则添加exchange列
        if cursor.fetchone() is None:
            logger.info("正在为OptionData表添加exchange列...")
            cursor.execute("""
                ALTER TABLE option_data 
                ADD COLUMN exchange VARCHAR(20) NOT NULL DEFAULT 'deribit'
            """)
            
            # 创建索引以提高查询性能
            logger.info("正在创建exchange列索引...")
            cursor.execute("""
                CREATE INDEX idx_option_data_exchange 
                ON option_data (exchange)
            """)
            
            conn.commit()
            logger.info("迁移成功：已添加exchange列")
        else:
            logger.info("exchange列已存在，无需迁移")
            
        # 关闭连接
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    execute_migration()