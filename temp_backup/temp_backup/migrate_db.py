#!/usr/bin/env python3
"""
简单的数据库迁移脚本 - 添加多时间周期支持
直接使用psycopg2连接数据库，不依赖SQLAlchemy的ORM
"""
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def execute_migration():
    """执行数据库迁移"""
    # 从环境变量获取数据库连接信息
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("没有找到DATABASE_URL环境变量，无法连接数据库")
        return False
    
    try:
        # 建立数据库连接
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 向RiskIndicator表添加time_period列
        try:
            cursor.execute("""
                ALTER TABLE risk_indicator 
                ADD COLUMN time_period VARCHAR(10) NOT NULL DEFAULT '4h'
            """)
            print("成功添加time_period列到RiskIndicator表")
        except psycopg2.errors.DuplicateColumn:
            print("time_period列已存在于RiskIndicator表中，跳过添加")
        
        # 向Alert表添加time_period列
        try:
            cursor.execute("""
                ALTER TABLE alert 
                ADD COLUMN time_period VARCHAR(10) NOT NULL DEFAULT '4h'
            """)
            print("成功添加time_period列到Alert表")
        except psycopg2.errors.DuplicateColumn:
            print("time_period列已存在于Alert表中，跳过添加")
        
        # 修改AlertThreshold表结构
        # 1. 备份现有数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_threshold_backup AS
            SELECT * FROM alert_threshold
        """)
        print("成功备份AlertThreshold表数据")
        
        # 2. 删除现有表
        cursor.execute("""
            DROP TABLE IF EXISTS alert_threshold
        """)
        print("成功删除旧的AlertThreshold表")
        
        # 3. 创建新表
        cursor.execute("""
            CREATE TABLE alert_threshold (
                id SERIAL PRIMARY KEY,
                indicator VARCHAR(50) NOT NULL,
                time_period VARCHAR(10) NOT NULL DEFAULT '4h',
                attention_threshold FLOAT NOT NULL,
                warning_threshold FLOAT NOT NULL,
                severe_threshold FLOAT NOT NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                UNIQUE (indicator, time_period)
            )
        """)
        print("成功创建新的AlertThreshold表")
        
        # 4. 从备份表恢复数据
        try:
            cursor.execute("""
                INSERT INTO alert_threshold
                (indicator, time_period, attention_threshold, warning_threshold, severe_threshold, is_enabled)
                SELECT 
                    indicator, 
                    '4h', 
                    attention_threshold, 
                    warning_threshold, 
                    severe_threshold, 
                    is_enabled
                FROM alert_threshold_backup
            """)
            print("成功从备份恢复AlertThreshold表数据")
        except psycopg2.Error as e:
            print(f"恢复数据时出错: {str(e)}")
        
        # 5. 删除备份表
        cursor.execute("""
            DROP TABLE IF EXISTS alert_threshold_backup
        """)
        print("成功删除备份表")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        print("数据库迁移成功完成")
        return True
        
    except psycopg2.Error as e:
        print(f"数据库迁移失败: {str(e)}")
        return False

if __name__ == "__main__":
    execute_migration()