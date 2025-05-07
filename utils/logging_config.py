
"""
日志配置模块
统一配置项目中所有的日志格式和处理器
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def configure_logging(log_to_file=True, log_level=logging.INFO):
    """
    配置全局日志设置
    
    参数:
    log_to_file - 是否将日志写入文件
    log_level - 日志级别，默认为INFO
    """
    # 创建日志目录
    if log_to_file and not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除之前的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 定义格式化器 - 包含时间、日志级别、模块名和消息
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_to_file:
        file_handler = RotatingFileHandler(
            'logs/application.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('ccxt.base.exchange').setLevel(logging.WARNING)
    
    # 返回配置好的根日志记录器
    return root_logger

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    参数:
    name - 日志记录器名称，通常为模块名
    
    返回:
    配置好的日志记录器
    """
    return logging.getLogger(name)
