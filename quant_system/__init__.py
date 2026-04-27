# -*- coding: utf-8 -*-
"""
量化交易系统核心包
All-in-One 量化交易工具箱

模块列表:
- ai_council: AI多模型决策系统
- daily_picker: 每日选股脚本
- position_monitor: 持仓监控脚本
- sentiment_analyzer: 情绪分析脚本
- backtest_engine: 回测引擎
- risk_manager: 风控系统
- data_sources: 统一数据源

Author: 炒股大师量化系统
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "炒股大师"

# AI Council 模块（有类定义）
from .ai_council import TradingCouncil, TradingOrchestrator, TradingMemory

# 导出
__all__ = [
    # AI Council
    "TradingCouncil",
    "TradingOrchestrator",
    "TradingMemory",
]
