
import functools
import logging
import traceback
from flask import jsonify, request

logger = logging.getLogger(__name__)

def api_error_handler(f):
    """
    API错误处理装饰器，用于捕获API路由中的异常并返回统一格式的错误响应
    
    用法:
        @app.route('/api/data')
        @api_error_handler
        def get_data():
            # 函数代码...
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 记录异常详情
            error_traceback = traceback.format_exc()
            logger.error(f"API错误: {str(e)}\n路径: {request.path}\n参数: {request.args}\n{error_traceback}")
            
            # 返回友好的错误信息
            return jsonify({
                'success': False,
                'error': True,
                'message': str(e),
                'error_type': e.__class__.__name__
            }), 500
    return decorated_function

def service_error_handler(f):
    """
    服务层错误处理装饰器，用于捕获服务方法中的异常并进行日志记录
    
    用法:
        class MyService:
            @service_error_handler
            def process_data(self, data):
                # 函数代码...
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 记录异常详情
            error_traceback = traceback.format_exc()
            logger.error(f"服务错误: {str(e)}\n方法: {f.__name__}\n参数: {args}, {kwargs}\n{error_traceback}")
            
            # 重新抛出异常供上层捕获
            raise
    return decorated_function
