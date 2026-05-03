# -*- coding: utf-8 -*-
"""
统一日志系统 - Logging System
替代所有 print 调用，提供结构化日志记录
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class QuantLogger:
    """量化系统统一日志类"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        name: str = "quant_system",
        level: str = "INFO",
        log_file: Optional[str] = None,
        rotation: bool = True,
        rotation_size_mb: int = 100,
        backup_count: int = 5,
    ):
        """
        初始化日志系统
        
        Args:
            name: 日志名称
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            log_file: 日志文件路径，None 则只输出到控制台
            rotation: 是否启用日志轮转
            rotation_size_mb: 轮转大小 (MB)
            backup_count: 保留的备份数量
        """
        if QuantLogger._initialized:
            return
            
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 避免重复添加 handler
        if self.logger.handlers:
            return
        
        # 日志格式
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件 handler（可选）
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            if rotation:
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_path,
                    maxBytes=rotation_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            else:
                file_handler = logging.FileHandler(log_path, encoding='utf-8')
            
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        QuantLogger._initialized = True
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """获取 logger 实例"""
        if name:
            return logging.getLogger(f"quant_system.{name}")
        return self.logger
    
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, exc_info=True, **kwargs):
        self.logger.exception(msg, *args, exc_info=exc_info, **kwargs)


# 便捷函数
def get_logger(name: str = None) -> logging.Logger:
    """获取 logger 实例"""
    logger = QuantLogger(
        level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', None),
        rotation=os.getenv('LOG_ROTATION', 'true').lower() == 'true',
        rotation_size_mb=int(os.getenv('LOG_ROTATION_SIZE_MB', '100')),
        backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
    )
    return logger.get_logger(name)


# 初始化默认 logger
default_logger = get_logger()


def log_trade(action: str, code: str, price: float, shares: int, reason: str = ""):
    """记录交易日志"""
    logger = get_logger()
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': 'trade',
        'action': action,  # BUY/SELL
        'code': code,
        'price': price,
        'shares': shares,
        'reason': reason,
    }
    logger.info(f"TRADE | {json.dumps(log_entry, ensure_ascii=False)}")


def log_signal(signal_type: str, code: str, score: float, details: dict = None):
    """记录交易信号"""
    logger = get_logger()
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': 'signal',
        'signal_type': signal_type,  # BUY/SELL/WATCH
        'code': code,
        'score': score,
        'details': details or {},
    }
    logger.info(f"SIGNAL | {json.dumps(log_entry, ensure_ascii=False)}")


def log_risk(risk_type: str, code: str, message: str, level: str = "WARNING"):
    """记录风险预警"""
    logger = get_logger()
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': 'risk',
        'risk_type': risk_type,
        'code': code,
        'message': message,
    }
    getattr(logger, level.lower())(f"RISK | {json.dumps(log_entry, ensure_ascii=False)}")


def log_api_call(api_name: str, params: dict, result: str, latency_ms: int):
    """记录 API 调用"""
    logger = get_logger()
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': 'api_call',
        'api_name': api_name,
        'params': params,
        'result': result,  # success/failure
        'latency_ms': latency_ms,
    }
    logger.debug(f"API | {json.dumps(log_entry, ensure_ascii=False)}")
