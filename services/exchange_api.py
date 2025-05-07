import ccxt
import logging
import datetime
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExchangeAPI:
    """加密货币交易所API接口类"""
    
    def __init__(self):
        self.exchanges = {}
        self.init_exchanges()
    
    def init_exchanges(self):
        """初始化所有支持的交易所"""
        try:
            # Deribit交易所初始化
            self.exchanges['deribit'] = ccxt.deribit({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'option'
                }
            })
            logger.info("Deribit交易所初始化成功")
            
            # OKX交易所初始化
            self.exchanges['okx'] = ccxt.okx({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'option'
                }
            })
            logger.info("OKX交易所初始化成功")
            
            # Binance交易所初始化 (由于地区限制可能无法访问)
            try:
                self.exchanges['binance'] = ccxt.binance({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'option'
                    }
                })
                logger.info("Binance交易所初始化成功")
            except Exception as e:
                logger.warning(f"Binance交易所初始化失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"交易所初始化错误: {str(e)}")
    
    def get_option_markets(self, exchange_id: str, symbol: str) -> List[Dict[str, Any]]:
        """获取特定交易所的期权市场数据"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                logger.error(f"交易所 {exchange_id} 不存在或未初始化")
                return []
            
            # 统一符号格式
            formatted_symbol = self._format_symbol(exchange_id, symbol)
            
            # 获取期权市场
            markets = exchange.load_markets()
            option_markets = []
            
            # 筛选符合条件的期权合约
            for symbol_id, market in markets.items():
                if market['type'] == 'option' and formatted_symbol in symbol_id:
                    option_markets.append(market)
            
            logger.info(f"从 {exchange_id} 获取到 {len(option_markets)} 个 {symbol} 期权合约")
            return option_markets
        
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的期权市场数据时出错: {str(e)}")
            return []
    
    def get_option_data(self, exchange_id: str, symbol: str, expiry_days_range: int = 7) -> List[Dict[str, Any]]:
        """获取期权数据，只包含特定到期日范围内的合约"""
        try:
            # 获取期权市场数据
            option_markets = self.get_option_markets(exchange_id, symbol)
            
            # 计算最大到期日 (当前日期 + 指定天数)
            today = datetime.datetime.now().date()
            max_expiry = today + datetime.timedelta(days=expiry_days_range)
            
            # 获取当前标的价格
            underlying_price = self.get_underlying_price(exchange_id, symbol)
            if not underlying_price:
                logger.error(f"无法获取 {symbol} 在 {exchange_id} 的标的价格")
                return []
            
            # 设置执行价格范围 (当前价格的 ±10%)
            min_strike = underlying_price * 0.9
            max_strike = underlying_price * 1.1
            
            filtered_options = []
            
            # 筛选近期到期的期权合约
            for market in option_markets:
                try:
                    # 检查是否含有必要信息
                    if not all(k in market for k in ['expiry', 'strike', 'option_type']):
                        continue
                    
                    # 解析到期日
                    expiry_date = None
                    if isinstance(market['expiry'], str):
                        try:
                            expiry_date = datetime.datetime.fromisoformat(market['expiry'].replace('Z', '+00:00')).date()
                        except ValueError:
                            # 尝试其他格式
                            try:
                                expiry_date = datetime.datetime.strptime(market['expiry'], '%Y%m%d').date()
                            except ValueError:
                                continue
                    
                    # 跳过到期日在范围外的合约
                    if not expiry_date or expiry_date > max_expiry:
                        continue
                    
                    # 只获取执行价范围内的合约
                    strike = float(market['strike'])
                    if not (min_strike <= strike <= max_strike):
                        continue
                    
                    # 获取期权价格和其他数据
                    ticker = self._get_option_ticker(exchange_id, market['symbol'])
                    if not ticker:
                        continue
                    
                    # 获取成交量数据
                    volume_data = self._get_volume_data(exchange_id, ticker, market)
                    
                    # 构建标准化的期权数据
                    option_data = {
                        'symbol': symbol,
                        'exchange': exchange_id,
                        'strike_price': strike,
                        'option_type': market['option_type'],
                        'expiration_date': expiry_date.isoformat(),
                        'underlying_price': underlying_price,
                        'option_price': self._get_option_price(ticker),
                        'volume': volume_data.get('volume', 0),
                        'open_interest': volume_data.get('open_interest', 0),
                        'implied_volatility': ticker.get('implied_volatility', None),
                        'delta': market.get('delta', None),
                        'gamma': market.get('gamma', None),
                        'theta': market.get('theta', None),
                        'vega': market.get('vega', None),
                        'original_data': market  # 保存原始数据以备需要
                    }
                    
                    filtered_options.append(option_data)
                
                except Exception as e:
                    logger.error(f"处理期权合约 {market.get('symbol', 'unknown')} 时出错: {str(e)}")
                    continue
            
            logger.info(f"从 {exchange_id} 筛选出 {len(filtered_options)} 个符合条件的 {symbol} 期权合约")
            return filtered_options
        
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的 {symbol} 期权数据时出错: {str(e)}")
            return []
    
    def get_underlying_price(self, exchange_id: str, symbol: str) -> Optional[float]:
        """获取特定交易所的标的资产价格"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                return None
            
            # 针对不同交易所使用不同的符号格式
            if exchange_id == 'deribit':
                ticker_symbol = f"{symbol}-PERPETUAL"
            elif exchange_id == 'okx':
                ticker_symbol = f"{symbol}-USDT"
            elif exchange_id == 'binance':
                ticker_symbol = f"{symbol}/USDT"
            else:
                ticker_symbol = f"{symbol}/USD"
            
            # 尝试获取行情
            ticker = exchange.fetch_ticker(ticker_symbol)
            if ticker and 'last' in ticker:
                price = float(ticker['last'])
                logger.info(f"{exchange_id} 的 {symbol} 当前价格: {price}")
                return price
        
        except Exception as e:
            logger.error(f"获取 {exchange_id} 的 {symbol} 标的价格时出错: {str(e)}")
        
        return None
    
    def _format_symbol(self, exchange_id: str, symbol: str) -> str:
        """根据交易所格式化交易对符号"""
        if exchange_id == 'deribit':
            return symbol
        elif exchange_id == 'okx':
            return f"{symbol}-USD"
        elif exchange_id == 'binance':
            return f"{symbol}"
        return symbol
    
    def _get_option_ticker(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """获取期权合约的行情数据"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                return {}
            
            ticker = exchange.fetch_ticker(symbol)
            return ticker
        
        except Exception as e:
            logger.debug(f"获取 {symbol} 行情时出错: {str(e)}")
            return {}
    
    def _get_option_price(self, ticker: Dict[str, Any]) -> float:
        """从行情数据中提取期权价格"""
        if not ticker:
            return 0.0
        
        # 尝试从不同字段获取价格
        for field in ['last', 'close', 'bid', 'ask', 'average']:
            if field in ticker and ticker[field] is not None:
                return float(ticker[field])
        
        return 0.0
    
    def _get_volume_data(self, exchange_id: str, ticker: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
        """从行情数据中提取成交量和持仓量信息"""
        volume_data = {
            'volume': 0,
            'open_interest': 0
        }
        
        try:
            # 根据不同交易所处理成交量数据
            if exchange_id == 'deribit':
                if 'baseVolume' in ticker:
                    volume_data['volume'] = int(ticker['baseVolume'] or 0)
                if 'info' in ticker and 'open_interest' in ticker['info']:
                    volume_data['open_interest'] = int(ticker['info']['open_interest'] or 0)
            
            elif exchange_id == 'okx':
                if 'info' in ticker:
                    if 'vol24h' in ticker['info']:
                        volume_data['volume'] = int(float(ticker['info']['vol24h'] or 0))
                    # OKX可能不直接提供持仓量
            
            elif exchange_id == 'binance':
                if 'baseVolume' in ticker:
                    volume_data['volume'] = int(ticker['baseVolume'] or 0)
                # Binance可能不直接提供持仓量
            
            # 提取其他可能的成交量相关字段
            if volume_data['volume'] == 0 and 'volume' in ticker:
                volume_data['volume'] = int(ticker['volume'] or 0)
            
            if volume_data['open_interest'] == 0 and 'openInterest' in market:
                volume_data['open_interest'] = int(market['openInterest'] or 0)
        
        except Exception as e:
            logger.warning(f"处理成交量数据时出错: {str(e)}")
        
        return volume_data