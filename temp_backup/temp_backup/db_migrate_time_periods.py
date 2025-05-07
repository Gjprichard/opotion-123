"""
数据库迁移脚本 - 添加多时间周期支持
"""
from app import app, db
from sqlalchemy import Column, String, text

def add_time_period_columns():
    """
    向RiskIndicator和Alert表添加time_period列
    """
    with app.app_context():
        # 检查RiskIndicator表中是否已存在time_period列
        try:
            db.session.execute(text("SELECT time_period FROM risk_indicator LIMIT 1"))
            print("time_period列已存在于RiskIndicator表中，跳过添加")
        except Exception:
            # 添加time_period列到RiskIndicator表
            db.session.execute(text(
                "ALTER TABLE risk_indicator ADD COLUMN time_period VARCHAR(10) NOT NULL DEFAULT '4h'"
            ))
            db.session.commit()
            print("成功添加time_period列到RiskIndicator表")
        
        # 检查Alert表中是否已存在time_period列
        try:
            db.session.execute(text("SELECT time_period FROM alert LIMIT 1"))
            print("time_period列已存在于Alert表中，跳过添加")
        except Exception:
            # 添加time_period列到Alert表
            db.session.execute(text(
                "ALTER TABLE alert ADD COLUMN time_period VARCHAR(10) NOT NULL DEFAULT '4h'"
            ))
            db.session.commit()
            print("成功添加time_period列到Alert表")
        
        # 修改AlertThreshold表结构
        try:
            # 检查AlertThreshold表是否有现有记录
            existing_thresholds = db.session.execute(text(
                "SELECT id, indicator, attention_threshold, warning_threshold, severe_threshold, is_enabled FROM alert_threshold"
            )).fetchall()
            
            # 删除唯一约束
            db.session.execute(text(
                "ALTER TABLE alert_threshold DROP CONSTRAINT IF EXISTS alert_threshold_indicator_key"
            ))
            
            # 尝试添加time_period列
            try:
                db.session.execute(text("SELECT time_period FROM alert_threshold LIMIT 1"))
                print("time_period列已存在于AlertThreshold表中，跳过添加")
            except Exception:
                # 添加time_period列
                db.session.execute(text(
                    "ALTER TABLE alert_threshold ADD COLUMN time_period VARCHAR(10) NOT NULL DEFAULT '4h'"
                ))
                db.session.commit()
                print("成功添加time_period列到AlertThreshold表")
            
            # 添加新的复合唯一约束
            db.session.execute(text(
                "ALTER TABLE alert_threshold ADD CONSTRAINT alert_threshold_indicator_time_period_key UNIQUE (indicator, time_period)"
            ))
            db.session.commit()
            print("成功添加复合唯一约束到AlertThreshold表")
            
            # 如果有必要，还原旧数据
            if existing_thresholds:
                for threshold in existing_thresholds:
                    # 检查这个指标的4h记录是否已存在
                    exists = db.session.execute(text(
                        "SELECT id FROM alert_threshold WHERE indicator = :indicator AND time_period = '4h'"
                    ), {"indicator": threshold[1]}).fetchone()
                    
                    if not exists:
                        db.session.execute(text(
                            """
                            INSERT INTO alert_threshold 
                            (indicator, time_period, attention_threshold, warning_threshold, severe_threshold, is_enabled)
                            VALUES (:indicator, '4h', :attention, :warning, :severe, :enabled)
                            """
                        ), {
                            "indicator": threshold[1],
                            "attention": threshold[2],
                            "warning": threshold[3],
                            "severe": threshold[4],
                            "enabled": threshold[5]
                        })
                        print(f"还原{threshold[1]}的阈值设置")
                db.session.commit()
        
        except Exception as e:
            db.session.rollback()
            print(f"修改AlertThreshold表时出错: {str(e)}")

if __name__ == "__main__":
    add_time_period_columns()
    print("数据库迁移完成")