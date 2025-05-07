import sys
import os
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入exchange_api_ccxt模块
try:
    from services.exchange_api_ccxt import get_underlying_price
    
    # 尝试获取BTC价格
    btc_price = get_underlying_price('BTC')
    print(f"BTC价格: {btc_price}")
    
    # 尝试获取ETH价格
    eth_price = get_underlying_price('ETH')
    print(f"ETH价格: {eth_price}")
    
except Exception as e:
    logger.error(f"导入或执行出错: {str(e)}", exc_info=True)