"""
使用CCXT库集成多个交易所API
支持Deribit、Binance、OKX交易所
用于获取BTC和ETH的期权市场数据
"""
import ccxt
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

# 全局交易所实例字典
exchanges = {
    'deribit': None,
    'binance': None,
    'okx': None
}

# 交易所API客户端缓存
_exchange_cache = {}

def initialize_exchange(exchange_id='deribit', api_key=None, api_secret=None, test_mode=False):
    """
    Initialize exchange API client using CCXT - 添加缓存和重试机制

    Parameters:
    exchange_id - 交易所ID，例如 'deribit', 'binance'
    api_key - API Key
    api_secret - API Secret
    test_mode - 是否使用测试网

    Returns:
    ccxt exchange instance
    """
    global _exchange_cache

    # 缓存键
    cache_key = f"{exchange_id}_{test_mode}_{api_key is not None}"

    # 如果有有效的缓存，直接返回
    if cache_key in _exchange_cache:
        try:
            # 测试连接是否正常
            _exchange_cache[cache_key].fetchStatus()
            # 如果没有异常，则缓存有效
            return _exchange_cache[cache_key]
        except Exception:
            # 连接可能已失效，从缓存中移除
            del _exchange_cache[cache_key]

    # 最多重试3次
    max_retries = 3
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # 根据交易所ID创建不同的交易所客户端
            if exchange_id.lower() == 'deribit':
                exchange_class = getattr(ccxt, 'deribit')
                exchange_config = {
                    'enableRateLimit': True,
                    'timeout': 30000,  # 增加超时时间
                    'rateLimit': 100   # 限制请求频率
                }

                if api_key and api_secret:
                    exchange_config['apiKey'] = api_key
                    exchange_config['secret'] = api_secret

                if test_mode:
                    exchange_config['urls'] = {
                        'api': 'https://test.deribit.com',
                    }

                exchange = exchange_class(exchange_config)

            elif exchange_id.lower() == 'binance':
                exchange_class = getattr(ccxt, 'binance')
                exchange_config = {
                    'enableRateLimit': True,
                    'timeout': 30000,  # 增加超时时间
                    'options': {
                        'defaultType': 'option',
                        'recvWindow': 60000  # 增加接收窗口
                    }
                }

                if api_key and api_secret:
                    exchange_config['apiKey'] = api_key
                    exchange_config['secret'] = api_secret

                if test_mode:
                    exchange_config['urls'] = {
                        'api': 'https://testnet.binance.vision',
                    }

                exchange = exchange_class(exchange_config)

            elif exchange_id.lower() == 'okx':
                exchange_class = getattr(ccxt, 'okx')
                exchange_config = {
                    'enableRateLimit': True,
                    'timeout': 30000,  # 增加超时时间
                    'options': {
                        'defaultType': 'option'
                    }
                }

                if api_key and api_secret:
                    exchange_config['apiKey'] = api_key
                    exchange_config['secret'] = api_secret

                if test_mode:
                    exchange_config['urls'] = {
                        'api': {
                            'public': 'https://www.okx.com',
                            'private': 'https://www.okx.com'
                        },
                        'test': {
                            'public': 'https://www.okx.com',
                            'private': 'https://www.okx.com'
                        }
                    }

                exchange = exchange_class(exchange_config)

            else:
                raise ValueError(f"Unsupported exchange: {exchange_id}")

            # 设置默认参数
            exchange.options['warnOnFetchOpenOrdersWithoutSymbol'] = False

            # 测试连接
            exchange.fetchStatus()

            # 存入缓存
            _exchange_cache[cache_key] = exchange

            return exchange
        except ccxt.NetworkError as e:
            # 网络错误可以重试
            retry_count += 1
            last_error = e
            logger.warning(f"Network error connecting to {exchange_id}, retry {retry_count}/{max_retries}: {str(e)}")
            time.sleep(1)  # 等待一秒再重试
        except Exception as e:
            # 其他错误直接失败
            logger.error(f"Error initializing exchange {exchange_id}: {str(e)}")
            return None

    # 所有重试都失败
    logger.error(f"Failed to initialize exchange {exchange_id} after {max_retries} retries. Last error: {str(last_error)}")
    return None

def get_underlying_price(symbol, exchange_id='deribit'):
    """
    获取标的资产当前价格

    参数:
    symbol - 交易对符号，如 'BTC', 'ETH'
    exchange_id - 交易所ID，默认为 'deribit'
    """
    global exchanges

    try:
        exchange_id = exchange_id.lower()

        # 检查交易所是否支持
        if exchange_id not in exchanges:
            logger.error(f"不支持的交易所: {exchange_id}")
            return None

        # 如果交易所实例未初始化，进行初始化
        if not exchanges[exchange_id]:
            logger.debug(f"{exchange_id}交易所实例未初始化，正在初始化...")
            exchanges[exchange_id] = initialize_exchange(exchange_id)

        # 再次检查是否初始化成功
        if not exchanges[exchange_id]:
            logger.error(f"{exchange_id}交易所实例初始化失败")
            return None

        # 确保符号格式正确
        symbol = symbol.upper()

        # 根据不同交易所获取价格
        if exchange_id == 'deribit':
            return _get_deribit_price(symbol, exchanges[exchange_id])
        elif exchange_id == 'binance':
            return _get_binance_price(symbol, exchanges[exchange_id])
        elif exchange_id == 'okx':
            return _get_okx_price(symbol, exchanges[exchange_id])
        else:
            logger.error(f"未实现{exchange_id}交易所的价格获取方法")
            return None
    except Exception as e:
        logger.error(f"获取{symbol}在{exchange_id}交易所的价格时发生错误: {str(e)}")
        return None

def _get_deribit_price(symbol, exchange):
    """获取Deribit交易所价格"""
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
        logger.debug(f"通过Deribit永续合约获取{symbol}价格失败: {str(e)}")

    # 尝试获取任何可用的期权来提取标的价格
    try:
        markets = [m for m in exchange.markets.keys() if m.startswith(f"{symbol}/")]
        if markets:
            ticker = exchange.fetch_ticker(markets[0])
            if ticker and 'info' in ticker and 'underlying_price' in ticker['info']:
                return float(ticker['info']['underlying_price'])
    except Exception as e:
        logger.debug(f"通过Deribit期权获取{symbol}价格失败: {str(e)}")

    logger.error(f"无法从Deribit获取{symbol}的价格")
    return None

def _get_binance_price(symbol, exchange):
    """获取Binance交易所价格"""
    try:
        # 币安现货市场
        spot_symbol = f"{symbol}/USDT"
        ticker = exchange.fetch_ticker(spot_symbol)
        if ticker and ticker.get('last'):
            return ticker['last']
    except Exception as e:
        logger.debug(f"通过Binance现货获取{symbol}价格失败: {str(e)}")

    # 尝试获取USDT永续合约价格
    try:
        # 币安永续合约
        futures_symbol = f"{symbol}/USDT:USDT"
        ticker = exchange.fetch_ticker(futures_symbol)
        if ticker and ticker.get('last'):
            return ticker['last']
    except Exception as e:
        logger.debug(f"通过Binance永续合约获取{symbol}价格失败: {str(e)}")

    logger.error(f"无法从Binance获取{symbol}的价格")
    return None

def _get_okx_price(symbol, exchange):
    """获取OKX交易所价格"""
    try:
        # OKX现货市场
        spot_symbol = f"{symbol}/USDT"
        ticker = exchange.fetch_ticker(spot_symbol)
        if ticker and ticker.get('last'):
            return ticker['last']
    except Exception as e:
        logger.debug(f"通过OKX现货获取{symbol}价格失败: {str(e)}")

    # 尝试获取USDT永续合约价格
    try:
        # OKX永续合约
        futures_symbol = f"{symbol}/USDT:USDT"
        ticker = exchange.fetch_ticker(futures_symbol)
        if ticker and ticker.get('markPrice'):
            return ticker['markPrice']
        elif ticker and ticker.get('last'):
            return ticker['last']
    except Exception as e:
        logger.debug(f"通过OKX永续合约获取{symbol}价格失败: {str(e)}")

    logger.error(f"无法从OKX获取{symbol}的价格")
    return None

def is_expiry_within_7_days(expiry_timestamp):
    """
    检查期权到期日是否在7天内

    参数:
    expiry_timestamp - 到期时间戳（毫秒）

    返回:
    bool - 是否在7天内到期
    """
    # 处理None值或0值
    if expiry_timestamp is None or expiry_timestamp == 0:
        return False

    try:
        # 确保expiry_timestamp是一个数字
        expiry_ts = float(expiry_timestamp)

        # 计算7天后的时间戳
        seven_days_later = datetime.utcnow() + timedelta(days=7)
        seven_days_later_ts = seven_days_later.timestamp() * 1000  # 转换为毫秒

        # 当前时间戳
        now_ts = datetime.utcnow().timestamp() * 1000  # 转换为毫秒

        # 检查到期时间是否在当前时间到7天后之间
        return now_ts <= expiry_ts <= seven_days_later_ts
    except (TypeError, ValueError) as e:
        logger.warning(f"处理到期时间戳时出错: {e}，值: {expiry_timestamp}")
        return False

def get_option_market_data(symbol, exchange_id='deribit'):
    """
    获取期权市场数据 - 多交易所支持版
    仅获取BTC和ETH的期权数据，且只获取执行价偏离市场价 ±10% 的期权合约
    现在只获取到期日在7天内的期权合约

    参数:
    symbol - 交易对符号，如 'BTC', 'ETH'
    exchange_id - 交易所ID，支持 'deribit', 'binance', 'okx'
    """
    global exchanges

    try:
        exchange_id = exchange_id.lower()

        # 检查交易所是否支持
        if exchange_id not in exchanges:
            logger.error(f"不支持的交易所: {exchange_id}")
            return []

        # 如果交易所实例未初始化，进行初始化
        if not exchanges[exchange_id]:
            logger.debug(f"{exchange_id}交易所实例未初始化，正在初始化...")
            exchanges[exchange_id] = initialize_exchange(exchange_id)

        # 再次检查是否初始化成功
        if not exchanges[exchange_id]:
            logger.error(f"{exchange_id}交易所实例初始化失败")
            return []

        # 验证符号 - 仅处理BTC和ETH
        symbol = symbol.upper()
        if symbol not in ["BTC", "ETH"]:
            logger.warning(f"不支持的符号: {symbol}，仅支持BTC和ETH")
            return []

        # 获取当前价格
        current_price = get_underlying_price(symbol, exchange_id)
        if not current_price:
            logger.error(f"未能获取{symbol}在{exchange_id}的当前价格")
            return []

        # 计算价格范围 - 仅保留±10%范围内的期权
        strike_min = current_price * 0.9
        strike_max = current_price * 1.1

        logger.info(f"[{exchange_id}] 获取{symbol}执行价范围{strike_min:.2f}-{strike_max:.2f}的期权数据，且只包含7天内到期的合约")

        # 根据不同交易所获取期权数据
        if exchange_id == 'deribit':
            return _get_deribit_options(symbol, current_price, strike_min, strike_max, exchanges[exchange_id])
        elif exchange_id == 'binance':
            return _get_binance_options(symbol, current_price, strike_min, strike_max, exchanges[exchange_id])
        elif exchange_id == 'okx':
            return _get_okx_options(symbol, current_price, strike_min, strike_max, exchanges[exchange_id])
        else:
            logger.error(f"未实现{exchange_id}交易所的期权数据获取方法")
            return []

    except Exception as e:
        logger.error(f"获取{symbol}在{exchange_id}的期权市场数据时发生错误: {str(e)}")
        return []

def _get_deribit_options(symbol, current_price, strike_min, strike_max, exchange):
    """获取Deribit交易所的期权数据"""
    try:
        # 获取所有期权合约
        markets = exchange.markets

        # 筛选特定条件的期权合约
        filtered_options = [
            market for market in markets.values() 
            if (market['base'] == symbol and 
                market['option'] and 
                market['active'] and
                market['strike'] and 
                strike_min <= market['strike'] <= strike_max and
                market['expiry'] and
                is_expiry_within_7_days(market['expiry']))  # 只获取7天内到期的期权
        ]

        if not filtered_options:
            logger.warning(f"未找到符合条件的{symbol}期权合约")
            return []

        logger.info(f"在Deribit找到{len(filtered_options)}个符合条件的{symbol}期权合约")

        # 按到期日排序
        filtered_options.sort(key=lambda x: x['expiry'])

        # 获取期权详细数据
        option_data = []
        batch_size = 10  # 每批处理的期权数量

        # 按到期日分组，减少API调用次数
        from itertools import groupby
        grouped_options = []
        for _, group in groupby(filtered_options, key=lambda x: x['expiry']):
            grouped_options.append(list(group))

        # 处理每组期权 - 减少处理数量以提高性能
        for group in grouped_options:
            # 降低处理数量到5个，以防止请求卡住
            for i in range(0, min(len(group), 5), batch_size):
                batch = group[i:i+batch_size]
                for option in batch:
                    try:
                        # 获取期权行情
                        ticker = exchange.fetch_ticker(option['symbol'])
                        if not ticker:
                            continue

                        # 基本信息处理
                        try:
                            # 确保expiry是数值类型
                            if isinstance(option['expiry'], str):
                                try:
                                    expiry_ts = float(option['expiry'])
                                except ValueError:
                                    logger.warning(f"Deribit期权{option['symbol']}的到期时间戳格式无效: {option['expiry']}")
                                    continue
                            else:
                                expiry_ts = option['expiry']

                            expiry_date = datetime.fromtimestamp(expiry_ts / 1000).date()
                            # 记录找到的近期期权合约
                            logger.debug(f"找到近期Deribit期权合约: {option['symbol']}, 到期日: {expiry_date}")
                        except (TypeError, ValueError) as e:
                            logger.warning(f"无法处理Deribit期权{option['symbol']}的到期日: {e}, 值: {option.get('expiry')}")
                            continue

                        option_type = option.get('optionType', '')  # 'call' 或 'put'
                        if not option_type or option_type not in ['call', 'put']:
                            logger.warning(f"Deribit期权{option['symbol']}的期权类型无效: {option_type}")
                            continue

                        strike_price = option.get('strike')
                        if not strike_price:
                            logger.warning(f"Deribit期权{option['symbol']}的执行价无效")
                            continue

                        # 确保strike_price是数值类型
                        if isinstance(strike_price, str):
                            try:
                                strike_price = float(strike_price)
                            except ValueError:
                                logger.warning(f"Deribit期权{option['symbol']}的执行价格式无效: {strike_price}")
                                continue

                        # 计算价格
                        option_price = None
                        if ticker.get('bid') and ticker.get('ask'):
                            option_price = (ticker['bid'] + ticker['ask']) / 2
                        elif ticker.get('markPrice'):
                            option_price = ticker['markPrice']
                        elif ticker.get('last'):
                            option_price = ticker['last']
                        else:
                            # 使用info里的mark_price字段作为最后尝试
                            option_price = ticker.get('info', {}).get('mark_price')

                        # 如果仍然没有价格，跳过
                        if not option_price:
                            logger.warning(f"无法获取Deribit期权{option['symbol']}的价格")
                            continue

                        try:
                            option_price = float(option_price)
                        except (TypeError, ValueError):
                            logger.warning(f"Deribit期权{option['symbol']}的价格转换失败: {option_price}")
                            continue

                        # 处理成交量，即使成交量为0也保留
                        # 先记录原始成交量数据结构，用于调试
                        volume_stats = {
                            'baseVolume': ticker.get('baseVolume'),
                            'info_volume': ticker.get('info', {}).get('volume'),
                            'info_volume_usd': ticker.get('info', {}).get('volume_usd'),
                            'stats_volume': ticker.get('info', {}).get('stats', {}).get('volume'),
                            'stats_volume_usd': ticker.get('info', {}).get('stats', {}).get('volume_usd')
                        }
                        logger.debug(f"Deribit期权{option['symbol']}成交量数据: {volume_stats}")

                        # 使用Deribit的stats.volume字段，这是更准确的成交量数据
                        # 如果不存在，则回退到baseVolume
                        volume_raw = ticker.get('info', {}).get('stats', {}).get('volume', 0) or ticker.get('baseVolume', 0) or 0
                        # 确保转换为浮点数，以支持数据服务中的类型转换
                        try:
                            volume = float(volume_raw)
                        except (ValueError, TypeError):
                            volume = 0

                        open_interest_raw = ticker.get('info', {}).get('open_interest', 0)
                        # 确保转换为浮点数，以支持数据服务中的类型转换
                        try:
                            open_interest = float(open_interest_raw)
                        except (ValueError, TypeError):
                            open_interest = 0

                        # Greeks处理
                        greeks = ticker.get('info', {}).get('greeks', {})

                        # 确保隐含波动率数据是数值类型
                        try:
                            mark_iv = ticker.get('info', {}).get('mark_iv', 0)
                            if isinstance(mark_iv, str):
                                mark_iv = float(mark_iv)
                            implied_volatility = mark_iv / 100  # 转换为小数
                        except (TypeError, ValueError):
                            implied_volatility = 0

                        # 确保Greeks数据为数值类型
                        try:
                            delta = greeks.get('delta')
                            if isinstance(delta, str):
                                delta = float(delta)
                        except (TypeError, ValueError):
                            delta = None

                        try:
                            gamma = greeks.get('gamma')
                            if isinstance(gamma, str):
                                gamma = float(gamma)
                        except (TypeError, ValueError):
                            gamma = None

                        try:
                            theta = greeks.get('theta') 
                            if isinstance(theta, str):
                                theta = float(theta)
                        except (TypeError, ValueError):
                            theta = None

                        try:
                            vega = greeks.get('vega')
                            if isinstance(vega, str):
                                vega = float(vega)
                        except (TypeError, ValueError):
                            vega = None

                        # 添加到结果集
                        option_data.append({
                            "symbol": symbol,
                            "exchange": "deribit",  # 添加交易所信息
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
                        logger.warning(f"处理Deribit期权{option['symbol']}时出错: {str(e)}")
                        continue

        logger.info(f"成功获取{len(option_data)}个{symbol}期权合约的详细数据")
        return option_data

    except Exception as e:
        logger.error(f"获取Deribit期权市场数据时发生错误: {str(e)}")
        return []

def _get_binance_options(symbol, current_price, strike_min, strike_max, exchange):
    """获取Binance交易所的期权数据"""
    try:
        # 币安期权市场处理
        markets = exchange.markets

        # 筛选期权市场 - 同时筛选执行价和到期日
        option_markets = [
            market for market in markets.values()
            if (market.get('type') == 'option' and 
                market.get('base') == symbol and
                market.get('active') and
                market.get('strike') and
                strike_min <= market.get('strike') <= strike_max and
                market.get('expiry') and
                is_expiry_within_7_days(market.get('expiry')))  # 只获取7天内到期的期权
        ]

        if not option_markets:
            logger.warning(f"未找到符合条件的Binance {symbol}期权合约")
            return []

        logger.info(f"在Binance找到{len(option_markets)}个符合条件的{symbol}期权合约")

        # 按到期日排序
        option_markets.sort(key=lambda x: x.get('expiry', 0))

        # 获取期权详细数据
        option_data = []

        # 由于Binance API限制，每次只处理一部分期权
        process_count = min(len(option_markets), 30)  # 限制处理数量

        for option in option_markets[:process_count]:
            try:
                # 获取期权行情
                ticker = exchange.fetch_ticker(option['symbol'])
                if not ticker:
                    continue

                # 提取基本信息
                try:
                    # 确保expiry是数值类型
                    expiry = option.get('expiry')
                    if expiry:
                        if isinstance(expiry, str):
                            try:
                                expiry_ts = float(expiry)
                            except ValueError:
                                logger.warning(f"Binance期权{option.get('symbol', '')}的到期时间戳格式无效: {expiry}")
                                continue
                        else:
                            expiry_ts = expiry

                        expiry_date = datetime.fromtimestamp(expiry_ts / 1000).date()
                        # 记录找到的近期期权合约
                        logger.debug(f"找到近期Binance期权合约: {option.get('symbol', '')}, 到期日: {expiry_date}")
                    else:
                        logger.warning(f"Binance期权{option.get('symbol', '')}没有有效的到期日")
                        continue
                except (TypeError, ValueError) as e:
                    logger.warning(f"无法处理Binance期权{option.get('symbol', '')}的到期日: {e}, 值: {option.get('expiry')}")
                    continue

                # 获取期权类型    
                option_type = option.get('info', {}).get('optionType', '').lower()  # 币安格式可能不同
                if not option_type or option_type not in ['call', 'put']:
                    # 尝试从符号中解析期权类型
                    symbol_str = option.get('symbol', '')
                    if 'CALL' in symbol_str.upper():
                        option_type = 'call'
                    elif 'PUT' in symbol_str.upper():
                        option_type = 'put'
                    else:
                        logger.warning(f"无法确定Binance期权{symbol_str}的类型")
                        continue

                # 获取执行价
                strike_price = option.get('strike')
                if not strike_price:
                    logger.warning(f"Binance期权{option.get('symbol', '')}没有有效的执行价")
                    continue

                try:
                    strike_price = float(strike_price)
                except (TypeError, ValueError):
                    logger.warning(f"Binance期权{option.get('symbol', '')}的执行价无效: {strike_price}")
                    continue

                # 计算价格
                option_price = ticker.get('last')
                if not option_price and ticker.get('bid') and ticker.get('ask'):
                    option_price = (ticker['bid'] + ticker['ask']) / 2
                elif not option_price:  # 如果还是没有价格，尝试其他字段
                    option_price = ticker.get('info', {}).get('markPrice')

                if not option_price:
                    logger.warning(f"无法获取Binance期权{option.get('symbol', '')}的价格")
                    continue

                try:
                    option_price = float(option_price)
                except (TypeError, ValueError):
                    logger.warning(f"Binance期权{option.get('symbol', '')}的价格无效: {option_price}")
                    continue

                # 成交量和持仓量 - 确保是数字类型
                # 先记录原始成交量数据结构，用于调试
                volume_stats = {
                    'baseVolume': ticker.get('baseVolume'),
                    'info_volume': ticker.get('info', {}).get('volume'),
                    'info_quoteVolume': ticker.get('info', {}).get('quoteVolume'),
                    'quoteVolume': ticker.get('quoteVolume')
                }
                logger.debug(f"Binance期权{option.get('symbol', '')}成交量数据: {volume_stats}")

                # 尝试从不同字段获取成交量数据，按优先级排序  
                volume_raw = (ticker.get('info', {}).get('volume') or 
                            ticker.get('baseVolume') or 
                            ticker.get('quoteVolume', 0) or 0)
                try:
                    volume = float(volume_raw)
                except (TypeError, ValueError):
                    volume = 0

                open_interest = ticker.get('info', {}).get('openInterest', 0) or 0
                try:
                    open_interest = float(open_interest)
                except (TypeError, ValueError):
                    open_interest = 0

                # 隐含波动率和Greeks (币安可能使用不同的字段)
                implied_volatility = ticker.get('info', {}).get('impliedVolatility', 0)

                # 添加到结果集
                option_data.append({
                    "symbol": symbol,
                    "exchange": "binance",  # 添加交易所信息
                    "expiration_date": expiry_date,
                    "strike_price": strike_price,
                    "option_type": option_type,
                    "underlying_price": current_price,
                    "option_price": option_price,
                    "volume": volume,
                    "open_interest": open_interest,
                    "implied_volatility": implied_volatility,
                    "delta": None,  # 币安可能不提供完整的Greeks数据
                    "gamma": None,
                    "theta": None,
                    "vega": None,
                    "timestamp": datetime.utcnow()
                })

            except Exception as e:
                logger.warning(f"处理Binance期权{option.get('symbol', '')}时出错: {str(e)}")
                continue

        logger.info(f"成功获取{len(option_data)}个Binance {symbol}期权合约的详细数据")
        return option_data

    except Exception as e:
        logger.error(f"获取Binance期权市场数据时发生错误: {str(e)}")
        return []

def _get_okx_options(symbol, current_price, strike_min, strike_max, exchange):
    """获取OKX交易所的期权数据"""
    try:
        # OKX期权市场处理
        markets = exchange.markets

        # 筛选期权市场 (OKX的期权格式可能不同) - 同时筛选执行价和到期日
        option_markets = [
            market for market in markets.values()
            if (market.get('type') == 'option' and 
                market.get('base') == symbol and
                market.get('active') and
                market.get('strike') and
                strike_min <= market.get('strike') <= strike_max and
                market.get('expiry') and
                is_expiry_within_7_days(market.get('expiry')))  # 只获取7天内到期的期权
        ]

        if not option_markets:
            logger.warning(f"未找到符合条件的OKX {symbol}期权合约")
            return []

        logger.info(f"在OKX找到{len(option_markets)}个符合条件的{symbol}期权合约")

        # 按到期日排序
        option_markets.sort(key=lambda x: x.get('expiry', 0))

        # 获取期权详细数据
        option_data = []

        # 由于API限制，每次只处理一部分期权
        process_count = min(len(option_markets), 15)  # 减少处理数量以提高性能

        for option in option_markets[:process_count]:
            try:
                # 获取期权行情
                ticker = exchange.fetch_ticker(option['symbol'])
                if not ticker:
                    continue

                # 提取基本信息
                try:
                    # 确保expiry是数值类型
                    expiry = option.get('expiry')
                    if expiry:
                        if isinstance(expiry, str):
                            try:
                                expiry_ts = float(expiry)
                            except ValueError:
                                logger.warning(f"OKX期权{option.get('symbol', '')}的到期时间戳格式无效: {expiry}")
                                continue
                        else:
                            expiry_ts = expiry

                        expiry_date = datetime.fromtimestamp(expiry_ts / 1000).date()
                        # 记录找到的近期期权合约
                        logger.debug(f"找到近期OKX期权合约: {option.get('symbol', '')}, 到期日: {expiry_date}")
                    else:
                        logger.warning(f"OKX期权{option.get('symbol', '')}没有有效的到期日")
                        continue
                except (TypeError, ValueError) as e:
                    logger.warning(f"无法处理OKX期权{option.get('symbol', '')}的到期日: {e}, 值: {option.get('expiry')}")
                    continue

                # OKX的期权类型可能在不同位置
                option_type = None
                if 'optionType' in option.get('info', {}):
                    option_type = option['info']['optionType'].lower()
                else:
                    # 尝试从符号中解析
                    symbol_parts = option.get('symbol', '').split('-')
                    if len(symbol_parts) > 2:
                        if 'C' in symbol_parts[-1]:
                            option_type = 'call'
                        elif 'P' in symbol_parts[-1]:
                            option_type = 'put'

                if option_type not in ['call', 'put']:
                    logger.warning(f"OKX期权{option.get('symbol```}')}的期权类型无效: {option_type}")
                    continue

                # 获取执行价
                strike_price = option.get('strike')
                if not strike_price:
                    logger.warning(f"OKX期权{option.get('symbol', '')}没有有效的执行价")
                    continue

                try:
                    strike_price = float(strike_price)
                except (TypeError, ValueError):
                    logger.warning(f"OKX期权{option.get('symbol', '')}的执行价无效: {strike_price}")
                    continue

                # 计算价格
                option_price = ticker.get('last')
                if not option_price and ticker.get('bid') and ticker.get('ask'):
                    option_price = (ticker['bid'] + ticker['ask']) / 2
                elif not option_price:  # 如果还是没有价格，尝试其他字段
                    option_price = ticker.get('info', {}).get('markPrice')

                if not option_price:
                    logger.warning(f"无法获取OKX期权{option.get('symbol', '')}的价格")
                    continue

                try:
                    option_price = float(option_price)
                except (TypeError, ValueError):
                    logger.warning(f"OKX期权{option.get('symbol', '')}的价格无效: {option_price}")
                    continue

                # 成交量和持仓量 - 确保是数字类型
                # 先记录原始成交量数据结构，用于调试
                volume_stats = {
                    'baseVolume': ticker.get('baseVolume'),
                    'info_volCcy24h': ticker.get('info', {}).get('volCcy24h'),
                    'info_vol24h': ticker.get('info', {}).get('vol24h'),
                    'quoteVolume': ticker.get('quoteVolume')
                }
                logger.debug(f"OKX期权{option.get('symbol', '')}成交量数据: {volume_stats}")

                # OKX的成交量一般在volCcy24h或vol24h字段中
                volume_raw = (ticker.get('info', {}).get('volCcy24h') or 
                             ticker.get('info', {}).get('vol24h') or
                             ticker.get('baseVolume') or 
                             ticker.get('quoteVolume', 0) or 0)
                try:
                    volume = float(volume_raw)
                except (TypeError, ValueError):
                    volume = 0

                open_interest = ticker.get('info', {}).get('openInterest', 0) or 0
                try:
                    open_interest = float(open_interest)
                except (TypeError, ValueError):
                    open_interest = 0

                # 隐含波动率 (OKX可能使用不同的字段)
                implied_volatility = ticker.get('info', {}).get('impliedVolatility', 0)

                # 添加到结果集
                option_data.append({
                    "symbol": symbol,
                    "exchange": "okx",  # 添加交易所信息
                    "expiration_date": expiry_date,
                    "strike_price": strike_price,
                    "option_type": option_type,
                    "underlying_price": current_price,
                    "option_price": option_price,
                    "volume": volume,
                    "open_interest": open_interest,
                    "implied_volatility": implied_volatility,
                    "delta": None,  # OKX可能不提供完整的Greeks数据
                    "gamma": None,
                    "theta": None,
                    "vega": None,
                    "timestamp": datetime.utcnow()
                })

            except Exception as e:
                logger.warning(f"处理OKX期权{option.get('symbol', '')}时出错: {str(e)}")
                continue

        logger.info(f"成功获取{len(option_data)}个OKX {symbol}期权合约的详细数据")
        return option_data

    except Exception as e:
        logger.error(f"获取OKX期权市场数据时发生错误: {str(e)}")
        return []

def set_api_credentials(api_key, api_secret, exchange_id='deribit', test_mode=False):
    """
    设置API凭证

    参数:
    api_key - API密钥
    api_secret - API密钥密文
    exchange_id - 交易所ID，支持 'deribit', 'binance', 'okx'
    test_mode - 是否使用测试网
    """
    try:
        return initialize_exchange(exchange_id, api_key, api_secret, test_mode)
    except Exception as e:
        logger.error(f"设置{exchange_id}交易所API凭证失败: {str(e)}")
        return False

def test_connection(exchange_id='deribit'):
    """
    测试交易所API连接

    参数:
    exchange_id - 交易所ID，支持 'deribit', 'binance', 'okx'
    """
    try:
        exchange_id = exchange_id.lower()

        # 检查交易所是否支持
        if exchange_id not in exchanges:
            return False, f"不支持的交易所: {exchange_id}"

        # 如果交易所实例未初始化，进行初始化
        if not exchanges[exchange_id]:
            logger.debug(f"{exchange_id}交易所实例未初始化，正在初始化...")
            exchanges[exchange_id] = initialize_exchange(exchange_id)

        # 尝试获取BTC价格
        btc_price = get_underlying_price('BTC', exchange_id)

        # 尝试获取ETH价格
        eth_price = get_underlying_price('ETH', exchange_id)

        if btc_price and eth_price:
            return True, f"{exchange_id.capitalize()}连接成功! BTC: ${btc_price:.2f}, ETH: ${eth_price:.2f}"
        elif btc_price:
            return True, f"{exchange_id.capitalize()}连接成功! BTC: ${btc_price:.2f}, 无法获取ETH价格"
        elif eth_price:
            return True, f"{exchange_id.capitalize()}连接成功! ETH: ${eth_price:.2f}, 无法获取BTC价格"
        else:
            return False, f"无法获取{exchange_id}的BTC和ETH价格"

    except Exception as e:
        logger.error(f"测试{exchange_id}连接时发生错误: {str(e)}")
        return False, f"连接{exchange_id}失败: {str(e)}"

def get_all_exchanges_data(symbol, combine=True):
    """
    从所有支持的交易所获取期权数据

    参数:
    symbol - 交易对符号，如 'BTC', 'ETH'
    combine - 是否合并所有交易所的数据

    返回:
    如果combine=True，返回合并后的期权数据列表
    如果combine=False，返回字典: {exchange_id: option_data_list}
    """
    result = {}

    # 初始化所有交易所
    for exchange_id in exchanges.keys():
        if not exchanges[exchange_id]:
            exchanges[exchange_id] = initialize_exchange(exchange_id)

    # 获取各交易所的数据
    for exchange_id in exchanges.keys():
        if exchanges[exchange_id]:
            try:
                exchange_data = get_option_market_data(symbol, exchange_id)
                result[exchange_id] = exchange_data
                logger.info(f"成功从{exchange_id}获取了{len(exchange_data)}条{symbol}期权数据")
            except Exception as e:
                logger.error(f"从{exchange_id}获取{symbol}期权数据失败: {str(e)}")
                result[exchange_id] = []

    # 根据需要合并或返回分开的数据
    if combine:
        combined_data = []
        for exchange_id, data_list in result.items():
            combined_data.extend(data_list)
        return combined_data
    else:
        return result

# 初始化所有交易所实例
for exchange_id in exchanges.keys():
    exchanges[exchange_id] = initialize_exchange(exchange_id)