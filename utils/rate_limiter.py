
import time
from functools import wraps
from flask import request, jsonify, g

class RateLimiter:
    """
    API请求速率限制器
    
    用于限制API请求的频率，防止过度使用和滥用API
    """
    
    def __init__(self):
        self.limits = {}  # 存储每个IP的请求记录
        self.cleanup_interval = 3600  # 清理间隔(秒)
        self.last_cleanup = time.time()
        
    def clean_old_requests(self):
        """清理过期的请求记录"""
        current_time = time.time()
        # 每小时清理一次
        if current_time - self.last_cleanup >= self.cleanup_interval:
            to_delete = []
            for ip, requests in self.limits.items():
                # 保留最近1小时内的请求
                self.limits[ip] = [req for req in requests if current_time - req <= 3600]
                if not self.limits[ip]:
                    to_delete.append(ip)
                    
            # 删除空记录
            for ip in to_delete:
                del self.limits[ip]
                
            self.last_cleanup = current_time
        
    def limit(self, max_requests=100, period=60):
        """
        速率限制装饰器
        
        参数:
            max_requests: 在period时间内允许的最大请求数
            period: 时间周期(秒)
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 清理旧请求
                self.clean_old_requests()
                
                # 获取客户端IP
                client_ip = request.remote_addr
                
                # 初始化请求记录
                if client_ip not in self.limits:
                    self.limits[client_ip] = []
                
                # 获取当前时间
                current_time = time.time()
                
                # 计算时间窗口内的请求数
                recent_requests = [req for req in self.limits[client_ip] if current_time - req <= period]
                
                # 如果超出限制，返回429错误
                if len(recent_requests) >= max_requests:
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded',
                        'message': f'请求频率超过限制，请等待后重试'
                    }), 429
                
                # 记录本次请求时间
                self.limits[client_ip].append(current_time)
                
                # 继续处理请求
                return f(*args, **kwargs)
            return decorated_function
        return decorator

# 创建全局实例
rate_limiter = RateLimiter()
