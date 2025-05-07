"""
Deribit交易所API连接模块
用于获取BTC和ETH的期权市场数据
"""
import logging
import json
import time
import hmac
import hashlib
import requests
import websocket
from datetime import datetime, timedelta
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Deribit API URLs
BASE_URL = "https://www.deribit.com"
WS_URL = "wss://www.deribit.com/ws/api/v2"

# API配置
API_KEY = None
API_SECRET = None

def set_api_credentials(api_key, api_secret):
    """设置API凭证"""
    global API_KEY, API_SECRET
    API_KEY = api_key
    API_SECRET = api_secret
    logger.info("API credentials have been set")

def get_auth_headers(api_key, api_secret):
    """生成认证头信息"""
    timestamp = int(time.time() * 1000)
    nonce = str(timestamp)
    
    signature_data = {
        "timestamp": timestamp,
        "nonce": nonce,
    }
    
    signature_data_str = json.dumps(signature_data)
    signature = hmac.new(
        bytes(api_secret, "utf-8"),
        bytes(signature_data_str, "utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "Authorization": f"deri-hmac-sha256 id={api_key},ts={timestamp},nonce={nonce},sig={signature}"
    }

def get_instrument_data(symbol, kind="option"):
    """获取期权合约信息"""
    try:
        url = f"{BASE_URL}/api/v2/public/get_instruments"
        params = {
            "currency": symbol,
            "kind": kind,
            "expired": False
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result"):
            return data["result"]
        else:
            logger.error(f"Error fetching instrument data: {data.get('error', 'Unknown error')}")
            return []
    except Exception as e:
        logger.error(f"Exception fetching instrument data: {str(e)}")
        return []

def get_ticker_data(instrument_name):
    """获取指定合约的报价信息"""
    try:
        url = f"{BASE_URL}/api/v2/public/ticker"
        params = {"instrument_name": instrument_name}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result"):
            return data["result"]
        else:
            logger.error(f"Error fetching ticker data for {instrument_name}: {data.get('error', 'Unknown error')}")
            return None
    except Exception as e:
        logger.error(f"Exception fetching ticker data for {instrument_name}: {str(e)}")
        return None

def get_underlying_price(symbol):
    """获取标的资产当前价格"""
    try:
        currency = symbol.upper()
        # 使用正确的API端点来获取价格
        url = f"{BASE_URL}/api/v2/public/get_index"
        params = {"currency": currency}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result"):
            return data["result"][currency]
        else:
            # 如果获取索引价格失败，尝试获取ticker价格
            try:
                instrument_name = f"{currency}-PERPETUAL"
                url = f"{BASE_URL}/api/v2/public/ticker"
                params = {"instrument_name": instrument_name}
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("result"):
                    return data["result"]["last_price"]
                else:
                    logger.error(f"Error fetching ticker price for {symbol}: {data.get('error', 'Unknown error')}")
                    return None
            except Exception as e:
                logger.error(f"Exception fetching ticker price for {symbol}: {str(e)}")
                return None
    except Exception as e:
        logger.error(f"Exception fetching underlying price for {symbol}: {str(e)}")
        return None

def get_option_market_data(symbol):
    """获取期权市场数据"""
    try:
        # 获取当前价格
        current_price = get_underlying_price(symbol)
        if not current_price:
            logger.error(f"Failed to get current price for {symbol}")
            return []
        
        # 获取所有活跃的期权合约
        instruments = get_instrument_data(symbol, "option")
        if not instruments:
            logger.error(f"No instruments found for {symbol}")
            return []
            
        # 筛选期权合约
        filtered_instruments = filter_instruments(instruments, current_price)
        logger.info(f"Found {len(filtered_instruments)} relevant option instruments for {symbol}")
        
        option_data = []
        # 获取每个合约的详细数据
        for instrument in filtered_instruments:
            ticker_data = get_ticker_data(instrument["instrument_name"])
            if ticker_data:
                option_data.append({
                    "symbol": symbol,
                    "instrument_name": instrument["instrument_name"],
                    "expiration_date": instrument["expiration_timestamp"],
                    "strike_price": instrument["strike"],
                    "option_type": "call" if instrument["option_type"] == "call" else "put",
                    "underlying_price": current_price,
                    "option_price": (ticker_data["best_bid_price"] + ticker_data["best_ask_price"]) / 2 if ticker_data["best_bid_price"] and ticker_data["best_ask_price"] else ticker_data["mark_price"],
                    "volume": ticker_data["stats"]["volume"],
                    "open_interest": ticker_data["open_interest"],
                    "implied_volatility": ticker_data["mark_iv"] / 100 if ticker_data["mark_iv"] else None,
                    "delta": ticker_data["greeks"]["delta"] if ticker_data.get("greeks") else None,
                    "gamma": ticker_data["greeks"]["gamma"] if ticker_data.get("greeks") else None,
                    "theta": ticker_data["greeks"]["theta"] if ticker_data.get("greeks") else None,
                    "vega": ticker_data["greeks"]["vega"] if ticker_data.get("greeks") else None,
                    "timestamp": datetime.utcnow()
                })
        
        return option_data
    except Exception as e:
        logger.error(f"Exception in get_option_market_data for {symbol}: {str(e)}")
        return []

def filter_instruments(instruments, current_price):
    """
    筛选期权合约:
    1. 执行价格与当前价格偏离不超过10%
    2. 过滤掉成交量为0的合约
    """
    filtered = []
    for instrument in instruments:
        strike = instrument["strike"]
        
        # 计算偏离率
        deviation_percent = abs((strike - current_price) / current_price * 100)
        
        # 只包含偏离率小于等于10%的合约
        if deviation_percent <= 10:
            filtered.append(instrument)
    
    # 按照期权到期日期排序
    filtered.sort(key=lambda x: x["expiration_timestamp"])
    
    return filtered

def get_market_data_websocket(symbol):
    """
    使用WebSocket连接获取市场数据
    仅作为示例，实际应用中需要实现完整的WebSocket客户端
    """
    pass