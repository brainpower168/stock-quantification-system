# -*- coding: utf-8 -*-
"""
统一异常处理模块 - Exception Handling
提供量化系统专用异常类和装饰器
"""

import functools
import traceback
from typing import Optional, Callable, Any
from .logger import get_logger

logger = get_logger('exceptions')


class QuantException(Exception):
    """量化系统基础异常类"""
    def __init__(self, message: str, code: str = "UNKNOWN", data: dict = None):
        self.message = message
        self.code = code
        self.data = data or {}
        self.stack_trace = traceback.format_exc()
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'error': self.code,
            'message': self.message,
            'data': self.data,
        }


class DataSourceException(QuantException):
    """数据源异常"""
    def __init__(self, message: str, source: str = None):
        super().__init__(
            message=message,
            code="DATA_SOURCE_ERROR",
            data={'source': source}
        )


class APIException(QuantException):
    """API 调用异常"""
    def __init__(self, message: str, api_name: str = None, status_code: int = None):
        super().__init__(
            message=message,
            code="API_ERROR",
            data={'api_name': api_name, 'status_code': status_code}
        )


class ValidationException(QuantException):
    """数据验证异常"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            data={'field': field, 'value': value}
        )


class ConfigException(QuantException):
    """配置异常"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            data={'config_key': config_key}
        )


class TradeException(QuantException):
    """交易异常"""
    def __init__(self, message: str, code: str = None, action: str = None):
        super().__init__(
            message=message,
            code="TRADE_ERROR",
            data={'stock_code': code, 'action': action}
        )


class CacheException(QuantException):
    """缓存异常"""
    def __init__(self, message: str, cache_key: str = None):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            data={'cache_key': cache_key}
        )


def handle_exceptions(default_return: Any = None, reraise: bool = False):
    """
    异常处理装饰器
    
    Args:
        default_return: 异常时的默认返回值
        reraise: 是否重新抛出异常
    
    Usage:
        @handle_exceptions(default_return=[])
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except QuantException as e:
                logger.error(f"{func.__name__} 抛出量化异常：{e.code} - {e.message}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                logger.error(f"{func.__name__} 抛出未知异常：{e}", exc_info=True)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time
            
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"{func.__name__} 重试{max_attempts}次后失败：{e}")
                        raise
                    
                    logger.warning(f"{func.__name__} 失败，{current_delay}秒后重试 ({attempts}/{max_attempts}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


def validate_not_none(*field_names: str):
    """
    验证参数不为 None 的装饰器
    
    Args:
        field_names: 需要验证的参数名
    
    Usage:
        @validate_not_none('code', 'price')
        def buy_stock(code, price, shares):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            for field in field_names:
                if field not in bound.arguments:
                    raise ValidationException(f"参数'{field}'不存在", field=field)
                if bound.arguments[field] is None:
                    raise ValidationException(f"参数'{field}'不能为 None", field=field)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
