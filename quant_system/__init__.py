# -*- coding: utf-8 -*-
"""
量化交易系统核心包
All-in-One 量化交易工具箱

模块列表:
- DailyPicker: 每日选股
- PositionMonitor: 持仓监控
- SentimentAnalyzer: 情绪分析
- Backtester: 回测验证
- LimitUpTracker: 涨停板追踪
- AuctionSentiment: 竞价情绪分析
- SectorHotTracker: 题材热点追踪
- LhbTracker: 龙虎榜追踪
- EventScanner: 事件驱动扫描
- RiskManager: 智能风控
- NorthMoneyTracker: 北向资金追踪
- BacktestEngine: 增强版回测引擎

Author: 炒股大师量化系统
Version: 1.1.0
"""

__version__ = "1.1.0"
__author__ = "炒股大师"

# 核心选股模块
from .daily_picker import DailyPicker

# 持仓监控模块
from .position_monitor import PositionMonitor

# 情绪分析模块
from .sentiment_analyzer import SentimentAnalyzer

# 回测验证模块
from .backtester import Backtester

# === 新增模块 v1.1 ===

# 涨停板追踪模块
from .limit_up_tracker import LimitUpTracker

# 竞价情绪分析模块
from .auction_sentiment import AuctionSentiment

# 题材热点追踪模块
from .sector_hot_tracker import SectorHotTracker

# 龙虎榜追踪模块
from .lhb_tracker import LhbTracker

# 事件驱动扫描模块
from .event_scanner import EventScanner, EventType

# 智能风控模块
from .risk_manager import RiskManager

# 北向资金追踪模块
from .north_money_tracker import NorthMoneyTracker

# 增强版回测引擎
from .backtest_engine import BacktestEngine, BacktestResult, Trade, Position

# 导出
__all__ = [
    # 核心模块
    'DailyPicker',
    'PositionMonitor',
    'SentimentAnalyzer',
    'Backtester',
    
    # 涨停板模块
    'LimitUpTracker',
    'AuctionSentiment',
    'SectorHotTracker',
    'LhbTracker',
    
    # 事件驱动
    'EventScanner',
    'EventType',
    
    # 风控
    'RiskManager',
    
    # 资金追踪
    'NorthMoneyTracker',
    
    # 回测
    'BacktestEngine',
    'BacktestResult',
    'Trade',
    'Position',
]
