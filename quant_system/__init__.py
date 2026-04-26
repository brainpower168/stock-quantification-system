"""炒股大师量化交易系统"""
from .daily_picker import DailyPicker
from .position_monitor import PositionMonitor
from .sentiment_analyzer import SentimentAnalyzer
from .backtester import Backtester

__version__ = "1.0.0"
__author__ = "炒股大师"
__license__ = "MIT"

__all__ = [
    'DailyPicker',
    'PositionMonitor',
    'SentimentAnalyzer',
    'Backtester'
]