import ccxt
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class ExchangeAPI:
    """加密货币交易所API接口类"""
    
    def __init__(self):
        """初始化所有支持的交易所"""
        self.exchanges = {}
        self.init_exchanges()
    
    def init_exchanges(self):
        """初始化所有支持的交易所"""
        try:
            # 初始化Deribit
            self.exchanges['deribit'] = ccxt.deribit({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'option'
                }
            })
            logger.info("Deribit交易所初始化成功")
            
            # 初始化OKX
            self.exchanges['okx'] = ccxt.okx({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'option'
                }
            })
            logger.info("OKX交易所初始化成功")
            
            # 初始化Binance
            self.exchanges['binance'] = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'option'
                }
            })
            logger.info("Binance交易所初始化成功")
            
        except Exception as e:
            logger.error(f"初始化交易所时出错: {str(e)}")
    
    def get_option_markets(self, exchange_id: str, symbol: str) -> List[Dict[str, Any]]:
        """获取特定交易所的期权市场数据"""
        try:
            if exchange_id not in self.exchanges:
                logger.warning(f"不支持的交易所: {exchange_id}")
                return []
            
            exchange = self.exchanges[exchange_id]
            formatted_symbol = self._format_symbol(exchange_id, symbol)
            
            # 获取所有期权市场
            markets = exchange.load_markets()
            
            # 筛选出指定资产的期权市场
            option_markets = []
            
            for market_id, market in markets.items():
                # 检查是否为期权合约且为指定资产
                if market['type'] == 'option' and market['base'] == formatted_symbol:
                    option_markets.append(market)
            
            logger.info(f"从 {exchange_id} 获取到 {len(option_markets)} 个 {symbol} 期权合约")
            
            return option_markets
            
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的期权市场数据时出错: {str(e)}")
            return []
    
    def get_option_data(self, exchange_id: str, symbol: str, expiry_days_range: int = 7) -> List[Dict[str, Any]]:
        """获取期权数据，只包含特定到期日范围内的合约"""
        try:
            # 获取市场数据
            markets = self.get_option_markets(exchange_id, symbol)
            
            if not markets:
                return []
            
            # 获取标的资产价格
            underlying_price = self.get_underlying_price(exchange_id, symbol)
            
            if not underlying_price:
                logger.error(f"无法获取 {symbol} 在 {exchange_id} 的标的价格")
                return []
            
            logger.info(f"{exchange_id} 的 {symbol} 当前价格: {underlying_price}")
            
            # 计算执行价格范围 (当前价格的 ±10%)
            strike_min = underlying_price * 0.9
            strike_max = underlying_price * 1.1
            
            # 计算到期日范围
            max_expiry = datetime.utcnow() + timedelta(days=expiry_days_range)
            
            # 筛选符合条件的期权合约
            filtered_markets = []
            
            for market in markets:
                # 提取执行价格和到期日
                strike_price = None
                expiry_date = None
                
                if 'strike' in market and market['strike']:
                    strike_price = float(market['strike'])
                
                if 'expiryDate' in market and market['expiryDate']:
                    expiry_date = datetime.strptime(market['expiryDate'], '%Y-%m-%d')
                elif 'expiry' in market and market['expiry']:
                    # 不同交易所可能使用不同格式的到期日
                    try:
                        expiry_date = datetime.fromtimestamp(market['expiry'] / 1000)
                    except:
                        try:
                            expiry_date = datetime.strptime(market['expiry'], '%Y-%m-%d')
                        except:
                            continue
                
                # 检查是否在执行价格范围内
                if strike_price and strike_min <= strike_price <= strike_max:
                    # 检查是否在到期日范围内
                    if expiry_date and expiry_date <= max_expiry:
                        filtered_markets.append(market)
            
            logger.info(f"从 {exchange_id} 筛选出 {len(filtered_markets)} 个符合条件的 {symbol} 期权合约")
            
            # 获取期权数据
            option_data = []
            
            for market in filtered_markets:
                try:
                    # 获取行情数据
                    ticker = self._get_option_ticker(exchange_id, market['symbol'])
                    
                    if not ticker:
                        continue
                    
                    # 提取期权价格
                    option_price = self._get_option_price(ticker)
                    
                    if not option_price:
                        continue
                    
                    # 获取成交量和持仓量数据
                    volume_data = self._get_volume_data(exchange_id, ticker, market)
                    
                    # 构建期权数据
                    data = {
                        'symbol': symbol,
                        'exchange': exchange_id,
                        'timestamp': datetime.utcnow(),
                        'expiration_date': datetime.strptime(market['expiryDate'], '%Y-%m-%d').date() if 'expiryDate' in market else None,
                        'strike_price': float(market['strike']) if 'strike' in market else None,
                        'option_type': market['option'].lower() if 'option' in market else None,  # 'call' 或 'put'
                        'underlying_price': underlying_price,
                        'option_price': option_price,
                        'volume': volume_data.get('volume', 0),
                        'open_interest': volume_data.get('open_interest', 0),
                        'implied_volatility': ticker.get('info', {}).get('impliedVolatility', None),
                        'delta': ticker.get('info', {}).get('delta', None),
                        'gamma': ticker.get('info', {}).get('gamma', None),
                        'theta': ticker.get('info', {}).get('theta', None),
                        'vega': ticker.get('info', {}).get('vega', None)
                    }
                    
                    option_data.append(data)
                    
                except Exception as e:
                    logger.warning(f"处理 {market['symbol']} 的期权数据时出错: {str(e)}")
                    continue
            
            return option_data
            
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的 {symbol} 期权数据时出错: {str(e)}")
            return []
    
    def get_underlying_price(self, exchange_id: str, symbol: str, timeframe: str = None) -> Optional[float]:
        """
        获取特定交易所的标的资产价格
        
        Args:
            exchange_id: 交易所ID
            symbol: 交易对符号
            timeframe: 时间段，例如 '1d' 表示获取1天前的收盘价
            
        Returns:
            标的资产价格
        """
        try:
            if exchange_id not in self.exchanges:
                logger.warning(f"不支持的交易所: {exchange_id}")
                return None
            
            exchange = self.exchanges[exchange_id]
            
            # 如果指定了timeframe，获取历史K线数据
            if timeframe:
                # 转换timeframe为CCXT支持的格式
                limit = 2  # 获取2条数据确保有足够数据
                
                # 根据交易所格式化交易对
                if exchange_id == 'deribit':
                    # Deribit使用BTC-PERPETUAL或ETH-PERPETUAL格式
                    if symbol == 'BTC' or symbol == 'BTC-USD':
                        market_symbol = "BTC-PERPETUAL"
                    elif symbol == 'ETH' or symbol == 'ETH-USD':
                        market_symbol = "ETH-PERPETUAL"
                    else:
                        return None
                elif exchange_id == 'okx':
                    # OKX使用BTC-USDT-SWAP格式
                    if symbol.startswith('BTC'):
                        market_symbol = "BTC-USDT-SWAP"
                    elif symbol.startswith('ETH'):
                        market_symbol = "ETH-USDT-SWAP"
                    else:
                        market_symbol = f"{symbol}-USDT-SWAP"
                elif exchange_id == 'binance':
                    # Binance使用BTC/USDT格式
                    if symbol.startswith('BTC'):
                        market_symbol = "BTC/USDT"
                    elif symbol.startswith('ETH'):
                        market_symbol = "ETH/USDT"
                    else:
                        market_symbol = f"{symbol}/USDT"
                else:
                    return None
                
                # 计算时间段
                now = datetime.utcnow()
                if timeframe == '1d':
                    since = int((now - timedelta(days=1)).timestamp() * 1000)
                    ccxt_timeframe = '1d'
                elif timeframe == '1h':
                    since = int((now - timedelta(hours=1)).timestamp() * 1000)
                    ccxt_timeframe = '1h'
                else:
                    since = int((now - timedelta(days=1)).timestamp() * 1000)
                    ccxt_timeframe = '1d'
                
                # 获取历史K线数据
                try:
                    ohlcv = exchange.fetch_ohlcv(market_symbol, ccxt_timeframe, since, limit)
                    if ohlcv and len(ohlcv) > 0:
                        # 返回第一条记录的收盘价 (OHLCV中第4个元素是收盘价)
                        return float(ohlcv[0][4])
                except Exception as e:
                    logger.warning(f"获取 {exchange_id} 的 {symbol} 历史价格时出错: {str(e)}")
                    # 回退到获取当前价格
                    pass
            
            # 获取当前价格
            # 根据交易所格式化交易对
            if exchange_id == 'deribit':
                # Deribit使用BTC-PERPETUAL或ETH-PERPETUAL格式
                if symbol == 'BTC' or symbol == 'BTC-USD':
                    ticker = exchange.fetch_ticker("BTC-PERPETUAL")
                elif symbol == 'ETH' or symbol == 'ETH-USD':
                    ticker = exchange.fetch_ticker("ETH-PERPETUAL")
                else:
                    return None
                return float(ticker['last'])
                
            elif exchange_id == 'okx':
                # OKX使用BTC-USDT-SWAP格式
                if symbol.startswith('BTC'):
                    ticker = exchange.fetch_ticker("BTC-USDT-SWAP")
                elif symbol.startswith('ETH'):
                    ticker = exchange.fetch_ticker("ETH-USDT-SWAP")
                else:
                    ticker = exchange.fetch_ticker(f"{symbol}-USDT-SWAP")
                return float(ticker['last'])
                
            elif exchange_id == 'binance':
                # Binance使用BTC/USDT格式
                if symbol.startswith('BTC'):
                    ticker = exchange.fetch_ticker("BTC/USDT")
                elif symbol.startswith('ETH'):
                    ticker = exchange.fetch_ticker("ETH/USDT")
                else:
                    ticker = exchange.fetch_ticker(f"{symbol}/USDT")
                return float(ticker['last'])
            
            return None
            
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的 {symbol} 标的价格时出错: {str(e)}")
            return None
    
    def _format_symbol(self, exchange_id: str, symbol: str) -> str:
        """根据交易所格式化交易对符号"""
        if exchange_id == 'deribit':
            return symbol
        elif exchange_id == 'okx':
            return symbol
        elif exchange_id == 'binance':
            return symbol
        return symbol
    
    def _get_option_ticker(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取期权合约的行情数据"""
        try:
            if exchange_id not in self.exchanges:
                return {}
            
            exchange = self.exchanges[exchange_id]
            ticker = exchange.fetch_ticker(symbol)
            
            return ticker
            
        except Exception as e:
            logger.warning(f"获取 {symbol} 的行情数据时出错: {str(e)}")
            return {}
    
    def _get_option_price(self, ticker: Dict[str, Any]) -> Optional[float]:
        """从行情数据中提取期权价格"""
        try:
            if 'last' in ticker and ticker['last']:
                return float(ticker['last'])
            
            if 'close' in ticker and ticker['close']:
                return float(ticker['close'])
            
            if 'bid' in ticker and ticker['bid'] and 'ask' in ticker and ticker['ask']:
                return (float(ticker['bid']) + float(ticker['ask'])) / 2
            
            return None
            
        except Exception as e:
            logger.warning(f"提取期权价格时出错: {str(e)}")
            return None
    
    def _get_volume_data(self, exchange_id: str, ticker: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
        """从行情数据中提取成交量和持仓量信息"""
        volume = 0
        open_interest = 0
        
        try:
            # 提取成交量
            if 'volume' in ticker and ticker['volume']:
                volume = float(ticker['volume'])
            
            # 提取持仓量
            if 'info' in ticker and 'openInterest' in ticker['info']:
                open_interest = float(ticker['info']['openInterest'])
            
            # Deribit特定处理
            if exchange_id == 'deribit' and 'info' in ticker:
                if 'volume' in ticker['info']:
                    volume = float(ticker['info']['volume'])
                if 'openInterest' in ticker['info']:
                    open_interest = float(ticker['info']['openInterest'])
            
            # OKX特定处理
            if exchange_id == 'okx' and 'info' in ticker:
                if 'volCcy24h' in ticker['info']:
                    volume = float(ticker['info']['volCcy24h'])
                if 'openInterest' in ticker['info']:
                    open_interest = float(ticker['info']['openInterest'])
            
            return {
                'volume': volume,
                'open_interest': open_interest
            }
            
        except Exception as e:
            logger.warning(f"提取成交量和持仓量数据时出错: {str(e)}")
            return {
                'volume': 0,
                'open_interest': 0
            }