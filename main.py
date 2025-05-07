import logging
import requests
from app import app, db
import routes  # 导入路由

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 应用初始化
with app.app_context():
    # 导入模型
    from models import OptionData, RiskIndicator
    
    # 创建数据库表
    db.create_all()
    
    # 初始化日志
    logging.info("应用程序初始化...")
    
    # 检查交易所API连接
    try:
        from services.exchange_api import ExchangeAPI
        api = ExchangeAPI()
        exchanges = list(api.exchanges.keys())
        logging.info(f"已连接的交易所: {', '.join(exchanges)}")
    except Exception as e:
        logging.error(f"交易所API初始化失败: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)