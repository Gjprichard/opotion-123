import ccxt
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deribit():
    """测试Deribit交易所API的基本使用"""
    try:
        # 初始化交易所
        exchange = ccxt.deribit({
            'enableRateLimit': True,
        })
        
        # 获取所有市场
        logger.info("获取所有市场信息...")
        markets = exchange.load_markets()
        logger.info(f"成功加载 {len(markets)} 个市场")
        
        # 打印一些BTC永续合约的市场信息
        btc_perp = 'BTC-PERPETUAL'
        if btc_perp in markets:
            logger.info(f"BTC永续合约信息: {markets[btc_perp]}")
        else:
            logger.info(f"未找到BTC永续合约: {btc_perp}")
            # 查找包含'BTC'和'PERPETUAL'的市场
            btc_markets = [k for k in markets.keys() if 'BTC' in k and 'PERPETUAL' in k]
            logger.info(f"找到的BTC永续合约: {btc_markets}")
        
        # 获取交易对价格
        logger.info("获取BTC价格...")
        # 测试几种不同的格式
        symbols_to_test = ['BTC-PERPETUAL', 'BTC/USD:PERPETUAL', 'BTC/USD:BTC-PERPETUAL', 'BTC-USD', 'BTC/USD']
        
        for symbol in symbols_to_test:
            try:
                ticker = exchange.fetch_ticker(symbol)
                logger.info(f"使用 {symbol} 成功获取价格: {ticker['last']}")
            except Exception as e:
                logger.error(f"使用 {symbol} 获取价格失败: {str(e)}")
        
        # 列出一些ETH期权合约
        logger.info("查找ETH期权合约...")
        eth_options = [k for k in markets.keys() if 'ETH' in k and markets[k]['type'] == 'option'][:5]
        logger.info(f"ETH期权示例: {eth_options}")
        
        # 列出所有可用的交易类型
        market_types = set(market['type'] for market in markets.values())
        logger.info(f"可用的交易类型: {market_types}")
        
    except Exception as e:
        logger.error(f"测试Deribit时出错: {str(e)}")

def test_binance():
    """测试Binance交易所API的基本使用"""
    try:
        # 初始化交易所
        exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        
        # 获取所有市场
        logger.info("获取所有市场信息...")
        markets = exchange.load_markets()
        logger.info(f"成功加载 {len(markets)} 个市场")
        
        # 获取BTC/USDT价格
        logger.info("获取BTC价格...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        logger.info(f"BTC/USDT价格: {ticker['last']}")
        
    except Exception as e:
        logger.error(f"测试Binance时出错: {str(e)}")

def test_okx():
    """测试OKX交易所API的基本使用"""
    try:
        # 初始化交易所
        exchange = ccxt.okx({
            'enableRateLimit': True,
        })
        
        # 获取所有市场
        logger.info("获取所有市场信息...")
        markets = exchange.load_markets()
        logger.info(f"成功加载 {len(markets)} 个市场")
        
        # 获取BTC-USDT价格
        logger.info("获取BTC价格...")
        # 测试几种不同的格式
        symbols_to_test = ['BTC/USDT', 'BTC/USDT:USDT', 'BTC-USDT', 'BTC-USDT-SWAP']
        
        for symbol in symbols_to_test:
            try:
                ticker = exchange.fetch_ticker(symbol)
                logger.info(f"使用 {symbol} 成功获取价格: {ticker['last']}")
            except Exception as e:
                logger.error(f"使用 {symbol} 获取价格失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"测试OKX时出错: {str(e)}")

if __name__ == "__main__":
    logger.info("开始测试CCXT交易所API...")
    test_deribit()
    logger.info("-" * 40)
    test_binance()
    logger.info("-" * 40)
    test_okx()
    logger.info("CCXT交易所API测试完成")