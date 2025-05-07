import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_apscheduler import APScheduler

# 创建基础类
class Base(DeclarativeBase):
    pass

# 初始化数据库
db = SQLAlchemy(model_class=Base)

# 初始化调度器
scheduler = APScheduler()

# 创建应用
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "crypto_options_secret")

# 配置数据库
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# 配置调度器
app.config["SCHEDULER_API_ENABLED"] = True

# 初始化扩展
db.init_app(app)
scheduler.init_app(app)

with app.app_context():
    # 导入模型
    from models import OptionData, RiskIndicator
    
    # 创建数据库表
    db.create_all()
    
    # 导入路由
    import routes
    
    # 导入服务
    from services.scheduler_service import configure_scheduler
    
    # 配置并启动调度器
    configure_scheduler(scheduler)
    scheduler.start()