import ccxt
import logging
import pprint

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def explore_deribit_api():
    """探索CCXT库对Deribit期权的支持情况"""
    
    try:
        # 创建Deribit交易所实例
        exchange = ccxt.deribit()
        
        # 打印交易所信息
        logger.info(f"Exchange: {exchange.id}")
        logger.info(f"Has options: {exchange.has.get('fetchOHLCV', False)}")
        
        # 获取交易所支持的市场
        markets = exchange.load_markets()
        
        # 查找期权市场
        option_markets = [market for market in markets.keys() if 'option' in exchange.markets[market].get('info', {}).get('kind', '')]
        
        if option_markets:
            logger.info(f"Found {len(option_markets)} option markets")
            logger.info(f"Sample option markets: {option_markets[:5]}")
            
            # 获取BTC期权
            btc_options = [market for market in option_markets if market.startswith('BTC')]
            if btc_options:
                logger.info(f"Found {len(btc_options)} BTC option markets")
                logger.info(f"Sample BTC options: {btc_options[:5]}")
                
                # 获取一个期权的详细信息
                option_symbol = btc_options[0]
                option_details = exchange.markets[option_symbol]
                logger.info(f"Option details for {option_symbol}:")
                pprint.pprint(option_details)
                
                # 尝试获取期权Greeks
                try:
                    ticker = exchange.fetch_ticker(option_symbol)
                    logger.info(f"Ticker for {option_symbol}:")
                    pprint.pprint(ticker)
                except Exception as e:
                    logger.error(f"Error fetching ticker: {str(e)}")
            else:
                logger.info("No BTC options found")
        else:
            logger.info("No option markets found")
        
        # 检查是否支持Deribit特有的API方法
        logger.info("Checking Deribit-specific methods:")
        logger.info(f"Has fetch_positions: {exchange.has.get('fetchPositions', False)}")
        logger.info(f"Has fetch_open_interest: {exchange.has.get('fetchOpenInterest', False)}")
        logger.info(f"Has fetch_funding_rate: {exchange.has.get('fetchFundingRate', False)}")
        
        # 检查可用的公共API方法
        public_methods = [method for method in dir(exchange) if not method.startswith('_') and callable(getattr(exchange, method)) and not method.startswith('private')]
        logger.info(f"Available public methods: {sorted(public_methods)[:20]}")
        
    except Exception as e:
        logger.error(f"Error exploring Deribit API: {str(e)}")

if __name__ == "__main__":
    explore_deribit_api()