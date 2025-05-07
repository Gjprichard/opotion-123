
import logging
import traceback
import sys
import time
from functools import wraps
from flask import jsonify, current_app

logger = logging.getLogger(__name__)

def api_error_handler(func):
    """
    装饰器，用于API路由的错误处理，返回JSON格式的错误响应
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录详细的错误信息
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 返回JSON格式的错误响应
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
    
    return wrapper

def retry(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    重试装饰器，用于可能失败的函数调用
    
    参数:
        max_retries (int): 最大重试次数
        delay (float): 初始延迟时间(秒)
        backoff (float): 每次重试的延迟倍数
        exceptions (tuple): 捕获并重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_retries, delay
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Retry function {func.__name__} due to {e}, retries left: {mtries-1}")
                    
                    # 最后一次重试失败时重新抛出异常
                    if mtries <= 1:
                        raise
                    
                    # 等待后重试
                    time.sleep(mdelay)
                    
                    # 增加延迟时间
                    mdelay *= backoff
                    
                    # 减少剩余重试次数
                    mtries -= 1
            
            return func(*args, **kwargs)  # 最终尝试
        return wrapper
    return decorator

def safe_db_operation(session_factory):
    """
    安全数据库操作装饰器，自动处理事务和回滚
    
    参数:
        session_factory: 获取数据库会话的工厂函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session = session_factory()
            try:
                result = func(*args, session=session, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"Database operation failed in {func.__name__}: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            finally:
                session.close()
        return wrapper
    return decorator

def log_execution_time(func):
    """
    记录函数执行时间的装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # 计算执行时间
        execution_time = end_time - start_time
        
        # 记录执行时间
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        
        # 如果执行时间过长，记录警告
        if execution_time > 1.0:
            logger.warning(f"Slow execution: {func.__name__} took {execution_time:.4f} seconds")
        
        return result
    return wrapper
