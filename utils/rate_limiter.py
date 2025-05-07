
from functools import wraps
import time
import logging
from flask import request, jsonify, current_app
import threading

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    简单的速率限制器，用于控制API请求频率
    """
    def __init__(self, limit=60, period=60):
        """
        初始化速率限制器
        
        参数:
            limit (int): 在指定时间段内允许的最大请求数
            period (int): 时间段长度，单位为秒
        """
        self.limit = limit
        self.period = period
        self.tokens = {}  # 客户端令牌桶 {ip: [时间戳列表]}
        self.lock = threading.Lock()
    
    def _get_client_identifier(self):
        """
        获取客户端标识符，默认使用IP地址
        """
        return request.remote_addr or 'unknown'
    
    def _clean_old_tokens(self, client_id, current_time):
        """
        清理过期的令牌
        """
        if client_id in self.tokens:
            self.tokens[client_id] = [t for t in self.tokens[client_id] if current_time - t < self.period]
    
    def check(self):
        """
        检查客户端是否超过速率限制
        
        返回:
            tuple: (是否允许请求, 剩余可用请求数, 重置时间)
        """
        client_id = self._get_client_identifier()
        current_time = time.time()
        
        with self.lock:
            # 清理过期的令牌
            self._clean_old_tokens(client_id, current_time)
            
            # 获取当前令牌数
            current_tokens = len(self.tokens.get(client_id, []))
            
            # 检查是否超过限制
            if current_tokens >= self.limit:
                # 计算最早的令牌重置时间
                reset_time = 0
                if client_id in self.tokens and self.tokens[client_id]:
                    oldest_token = min(self.tokens[client_id])
                    reset_time = oldest_token + self.period - current_time
                
                return False, 0, reset_time
            
            # 添加新令牌
            if client_id not in self.tokens:
                self.tokens[client_id] = []
            
            self.tokens[client_id].append(current_time)
            
            # 计算剩余可用请求数
            remaining = self.limit - len(self.tokens[client_id])
            
            return True, remaining, self.period

def rate_limit(limit=60, period=60):
    """
    速率限制装饰器，用于限制API请求频率
    
    参数:
        limit (int): 在指定时间段内允许的最大请求数
        period (int): 时间段长度，单位为秒
    """
    limiter = RateLimiter(limit, period)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            allowed, remaining, reset = limiter.check()
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {request.remote_addr} at {request.path}")
                
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again in {int(reset)} seconds.'
                })
                
                # 添加速率限制相关的响应头
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(time.time() + reset))
                response.headers['Retry-After'] = str(int(reset))
                
                return response, 429
            
            # 继续处理请求
            response = func(*args, **kwargs)
            
            # 如果是标准flask响应对象，添加速率限制相关的响应头
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(time.time() + period))
            
            return response
        
        return wrapper
    
    return decorator
