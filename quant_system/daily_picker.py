"""
每日选股模块 v2.0
整合舆情评分到选股流程
"""

import json
import subprocess
from typing import List, Dict, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from smart_selector import SmartStockSelector


class DailyPicker:
    """每日选股模块"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化选股器

        Args:
            config: 配置字典，包含权重、阈值等参数
        """
        self.config = config or {
            "top_n": 3,
            "min_score": 60.0,
            "weights": {
                "capital_flow": 0.25,
                "ddx": 0.25,
                "sentiment": 0.20,
                "technical": 0.15,
                "fundamental": 0.15,
            },
        }
        self.smart_selector = SmartStockSelector(config)

    def pick(self, top_n: int = 3, min_score: float = 60.0) -> List[Dict]:
        """
        执行选股，返回Top N推荐

        Args:
            top_n: 返回推荐数量
            min_score: 最低评分阈值

        Returns:
            推荐股票列表，每个元素包含股票代码、名称、评分、理由
        """
        try:
            # 使用智能选股引擎
            # 这里需要传入股票池列表
            # 暂时返回空列表，实际使用时需要从数据源获取股票池
            return []

        except Exception as e:
            print(f"选股失败: {e}")
            return []

    def analyze_stock(self, stock_code: str, stock_name: str = None) -> Dict:
        """
        分析单只股票

        Args:
            stock_code: 股票代码
            stock_name: 股票名称

        Returns:
            分析结果字典
        """
        return self.smart_selector.analyze_stock(stock_code, stock_name)

    def screen_stocks(self, stock_list: List[str], top_n: int = 10) -> tuple:
        """
        批量筛选股票

        Args:
            stock_list: 股票代码列表
            top_n: 返回数量

        Returns:
            (结果列表, 分级字典)
        """
        return self.smart_selector.screen_stocks(stock_list, top_n)

    @classmethod
    def from_config(cls, config_path: str) -> "DailyPicker":
        """
        从配置文件加载

        Args:
            config_path: 配置文件路径（JSON格式）

        Returns:
            DailyPicker实例
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return cls(config)

    def update_config(self, new_config: Dict):
        """
        更新配置

        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        self.smart_selector = SmartStockSelector(self.config)
