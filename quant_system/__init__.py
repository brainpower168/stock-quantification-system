# -*- coding: utf-8 -*-
"""
量化交易系统核心包
All-in-One 量化交易工具箱

模块列表:
- ai_council: AI 多模型决策系统
- daily_picker: 每日选股脚本
- position_monitor: 持仓监控脚本
- sentiment_analyzer: 情绪分析脚本
- backtest_engine: 回测引擎
- risk_manager: 风控系统
- data_sources: 统一数据源
- logger: 日志系统
- exceptions: 异常处理
- cache: 缓存系统
- database: 数据库支持
- config_validator: 配置验证
- limit_up_strategy: 连板股策略
- smart_sell_strategy: 智能卖出策略

Author: 炒股大师量化系统
Version: 2.1.0
"""

__version__ = "2.1.0"
__author__ = "炒股大师"

# 核心模块
try:
    from .ai_council import TradingCouncil, TradingOrchestrator, TradingMemory
except ImportError:
    pass

try:
    from .daily_picker import DailyPicker
    from .position_monitor import PositionMonitor
    from .sentiment_analyzer import SentimentAnalyzer
    from .backtest_engine import BacktestEngine
    from .risk_manager import RiskManager
    from .data_sources import DataSource
except ImportError:
    pass

try:
    from .smart_sell_strategy import SmartSellStrategy, SellChecklist
    from .limit_up_strategy import LimitUpStrategy
except ImportError:
    pass

# 新增模块（v2.1.0）
try:
    from .logger import get_logger, default_logger
    from .exceptions import (
        QuantException,
        DataSourceException,
        APIException,
        ValidationException,
        ConfigException,
        TradeException,
        CacheException,
        handle_exceptions,
        retry,
        validate_not_none,
    )
except ImportError:
    pass

try:
    from .cache import CacheManager, MemoryCache, FileCache, cached, cache_manager
except ImportError:
    pass

try:
    from .database import (
        DatabaseManager,
        init_database,
        get_database,
    )
except ImportError:
    pass

try:
    from .config_validator import (
        ConfigValidator,
        validate_config,
        check_config_with_exit,
    )
except ImportError:
    pass

# 导出
__all__ = [
    # 核心模块
    "DailyPicker",
    "PositionMonitor",
    "SentimentAnalyzer",
    "BacktestEngine",
    "RiskManager",
    "DataSource",
    
    # AI Council
    "TradingCouncil",
    "TradingOrchestrator",
    "TradingMemory",
    
    # 策略模块
    "SmartSellStrategy",
    "SellChecklist",
    "LimitUpStrategy",
    
    # 工具模块（v2.1.0 新增）
    "get_logger",
    "default_logger",
    "QuantException",
    "DataSourceException",
    "APIException",
    "ValidationException",
    "ConfigException",
    "TradeException",
    "CacheException",
    "handle_exceptions",
    "retry",
    "validate_not_none",
    "CacheManager",
    "MemoryCache",
    "FileCache",
    "cached",
    "cache_manager",
    "DatabaseManager",
    "init_database",
    "get_database",
    "ConfigValidator",
    "validate_config",
    "check_config_with_exit",
]
