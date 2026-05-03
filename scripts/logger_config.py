# -*- coding: utf-8 -*-
"""
统一日志配置 - 统一导入入口
"""

import os
import sys
from pathlib import Path

# 添加quant_system到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "quant_system"))

try:
    from quant_system.logger import (
        get_logger,
        log_trade,
        log_signal,
        log_risk,
        log_api_call,
    )
except ImportError:
    # 如果quant_system不可用，使用标准logging
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    def get_logger(name=None):
        return logging.getLogger(name or "ai_trading")

    def log_trade(action, code, price, shares, reason=""):
        logger = get_logger("trade")
        logger.info(f"TRADE | {action} | {code} | {price} | {shares} | {reason}")

    def log_signal(signal_type, code, score, details=None):
        logger = get_logger("signal")
        logger.info(f"SIGNAL | {signal_type} | {code} | {score} | {details or {}}")

    def log_risk(risk_type, code, message, level="WARNING"):
        logger = get_logger("risk")
        getattr(logger, level.lower())(f"RISK | {risk_type} | {code} | {message}")

    def log_api_call(api_name, params, result, latency_ms):
        logger = get_logger("api")
        logger.debug(f"API | {api_name} | {result} | {latency_ms}ms")


# 模块级logger
logger = get_logger("ai_trading")
