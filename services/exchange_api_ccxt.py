"""
使用CCXT库集成Deribit交易所API
用于获取BTC和ETH的期权市场数据
"""
import ccxt
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局交易所实例
exchange = None

def initialize_exchange(api_key=None, api_secret=None, test_mode=False):
    """初始化CCXT交易所实例"""
    global exchange
    
    try:
        # 创建Deribit交易所实例
        if test_mode:
            # 使用测试网
            exchange = ccxt.deribit({
                'apiKey': api_key,
                'secret': api_secret,
                'urls': {
                    'api': 'https://test.deribit.com',
                }
            })
        else:
            exchange = ccxt.deribit({
                'apiKey': api_key,
                'secret': api_secret
            })
        
        if api_key and api_secret:
            logger.info("交易所实例已初始化（附带API凭证）")
        else:
            logger.info("交易所实例已初始化（公共访问模式）")
            
        # 加载市场数据
        exchange.load_markets()
        return True
    except Exception as e:
        logger.error(f"初始化交易所实例失败: {str(e)}")
        exchange = None
        return False

def get_underlying_price(symbol):
    """获取标的资产当前价格"""
    global exchange
    
    try:
        if not exchange:
            logger.debug("交易所实例未初始化，正在初始化...")
            initialize_exchange()
        
        # 确保符号格式正确
        symbol = symbol.upper()
        
        # 获取Deribit指数价格 - 尝试直接使用fetch_ticker获取永续合约数据
        try:
            # Deribit永续合约格式：BTC-PERPETUAL
            perpetual_symbol = f"{symbol}-PERPETUAL"
            ticker = exchange.fetch_ticker(perpetual_symbol)
            # 优先使用指数价格，其次是标记价格，最后是最新成交价
            if ticker and ticker.get('indexPrice'):
                return ticker['indexPrice']
            elif ticker and ticker.get('markPrice'):
                return ticker['markPrice']
            elif ticker and ticker.get('last'):
                return ticker['last']
        except Exception as e:
            logger.debug(f"通过永续合约获取{symbol}价格失败: {str(e)}")
        
        # 尝试获取任何可用的期权来提取标的价格
        try:
            markets = [m for m in exchange.markets.keys() if m.startswith(f"{symbol}/")]
            if markets:
                ticker = exchange.fetch_ticker(markets[0])
                if ticker and 'info' in ticker and 'underlying_price' in ticker['info']:
                    return float(ticker['info']['underlying_price'])
        except Exception as e:
            logger.debug(f"通过期权获取{symbol}价格失败: {str(e)}")
            
        logger.error(f"无法获取 {symbol} 的价格")
        return None
    except Exception as e:
        logger.error(f"获取 {symbol} 价格时发生错误: {str(e)}")
        return None

def get_option_market_data(symbol):
    """获取期权市场数据 - 优化版
       仅获取BTC和ETH的期权数据，且只获取执行价偏离市场价 ±10% 的期权合约
    """
    global exchange
    
    try:
        if not exchange:
            logger.debug("交易所实例未初始化，正在初始化...")
            initialize_exchange()
        
        # 验证符号 - 仅处理BTC和ETH
        symbol = symbol.upper()
        if symbol not in ["BTC", "ETH"]:
            logger.warning(f"不支持的符号: {symbol}，仅支持BTC和ETH")
            return []
            
        # 获取当前价格
        current_price = get_underlying_price(symbol)
        if not current_price:
            logger.error(f"未能获取 {symbol} 的当前价格")
            return []
            
        # 计算价格范围 - 仅保留±10%范围内的期权
        strike_min = current_price * 0.9
        strike_max = current_price * 1.1
        
        logger.info(f"[优化] 获取 {symbol} 执行价范围 {strike_min:.2f} - {strike_max:.2f} 的期权数据")
        
        # 获取所有期权合约 - 优化：先筛选再处理
        markets = exchange.markets
        
        # 筛选特定条件的期权合约 - 一次性完成多条件筛选
        filtered_options = [
            market for market in markets.values() 
            if (market['base'] == symbol and 
                market['option'] and 
                market['active'] and
                market['strike'] and 
                strike_min <= market['strike'] <= strike_max)
        ]
        
        if not filtered_options:
            logger.warning(f"未找到符合条件的 {symbol} 期权合约")
            return []
            
        logger.info(f"找到 {len(filtered_options)} 个符合条件的 {symbol} 期权合约")
        
        # 按到期日排序
        filtered_options.sort(key=lambda x: x['expiry'])
        
        # 获取期权详细数据 - 优化：批量处理相似到期日的期权
        option_data = []
        batch_size = 10  # 每批处理的期权数量
        
        # 按到期日分组，减少API调用次数
        from itertools import groupby
        grouped_options = []
        for _, group in groupby(filtered_options, key=lambda x: x['expiry']):
            grouped_options.append(list(group))
        
        # 处理每组期权
        for group in grouped_options:
            # 每组最多处理batch_size个合约以减轻API负担
            for i in range(0, min(len(group), 20), batch_size):
                batch = group[i:i+batch_size]
                for option in batch:
                    try:
                        # 获取期权行情
                        ticker = exchange.fetch_ticker(option['symbol'])
                        if not ticker:
                            continue
                        
                        # 基本信息处理
                        expiry_date = datetime.fromtimestamp(option['expiry'] / 1000).date()
                        option_type = option['optionType']  # 'call' 或 'put'
                        strike_price = option['strike']
                        
                        # 计算价格
                        option_price = None
                        if ticker.get('bid') and ticker.get('ask'):
                            option_price = (ticker['bid'] + ticker['ask']) / 2
                        elif ticker.get('markPrice'):
                            option_price = ticker['markPrice']
                        else:
                            continue  # 跳过没有价格的期权
                        
                        # 只关注有成交量的期权
                        volume = ticker.get('baseVolume', 0)
                        if volume <= 0:
                            continue  # 跳过无成交量的期权
                            
                        open_interest = ticker.get('info', {}).get('open_interest', 0)
                        
                        # Greeks处理 - 优化：只提取必要的数据
                        greeks = ticker.get('info', {}).get('greeks', {})
                        
                        implied_volatility = ticker.get('info', {}).get('mark_iv', 0) / 100  # 转换为小数
                        delta = greeks.get('delta')
                        gamma = greeks.get('gamma')
                        theta = greeks.get('theta')
                        vega = greeks.get('vega')
                        
                        # 添加到结果集
                        option_data.append({
                            "symbol": symbol,
                            "expiration_date": expiry_date,
                            "strike_price": strike_price,
                            "option_type": option_type,
                            "underlying_price": current_price,
                            "option_price": option_price,
                            "volume": volume,
                            "open_interest": open_interest,
                            "implied_volatility": implied_volatility,
                            "delta": delta,
                            "gamma": gamma,
                            "theta": theta,
                            "vega": vega,
                            "timestamp": datetime.utcnow()
                        })
                        
                    except Exception as e:
                        logger.warning(f"处理期权 {option['symbol']} 时出错: {str(e)}")
                        continue
        
        logger.info(f"成功获取 {len(option_data)} 个 {symbol} 期权合约的详细数据")
        return option_data
    
    except Exception as e:
        logger.error(f"获取 {symbol} 期权市场数据时发生错误: {str(e)}")
        return []

def set_api_credentials(api_key, api_secret, test_mode=False):
    """设置API凭证"""
    try:
        return initialize_exchange(api_key, api_secret, test_mode)
    except Exception as e:
        logger.error(f"设置API凭证失败: {str(e)}")
        return False

def test_connection():
    """测试API连接"""
    try:
        if not exchange:
            logger.debug("交易所实例未初始化，正在初始化...")
            initialize_exchange()
            
        # 尝试获取BTC价格
        btc_price = get_underlying_price('BTC')
        if not btc_price:
            return False, "无法获取BTC价格"
            
        # 尝试获取ETH价格
        eth_price = get_underlying_price('ETH')
        if not eth_price:
            return False, "无法获取ETH价格"
            
        return True, f"连接成功! BTC: ${btc_price:.2f}, ETH: ${eth_price:.2f}"
    
    except Exception as e:
        logger.error(f"测试连接时发生错误: {str(e)}")
        return False, f"连接失败: {str(e)}"

# 初始化交易所实例
initialize_exchange()