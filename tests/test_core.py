# -*- coding: utf-8 -*-
"""
单元测试 - 测试核心功能
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLogger:
    """测试日志系统"""

    def test_logger_creation(self):
        """测试 logger 创建"""
        from quant_system.logger import get_logger

        logger = get_logger("test")
        assert logger is not None

    def test_logger_log_levels(self):
        """测试日志级别"""
        from quant_system.logger import get_logger

        logger = get_logger("test")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")


class TestExceptions:
    """测试异常处理"""

    def test_quant_exception(self):
        """测试基础异常"""
        from quant_system.exceptions import QuantException

        exc = QuantException("Test error", code="TEST", data={"key": "value"})
        assert exc.message == "Test error"
        assert exc.code == "TEST"
        assert exc.data == {"key": "value"}

    def test_handle_exceptions_decorator(self):
        """测试异常处理装饰器"""
        from quant_system.exceptions import handle_exceptions

        @handle_exceptions(default_return=[])
        def failing_function():
            raise ValueError("Error")

        result = failing_function()
        assert result == []

    def test_validate_not_none(self):
        """测试参数验证"""
        from quant_system.exceptions import validate_not_none, ValidationException

        @validate_not_none("code", "price")
        def buy_stock(code, price, shares=100):
            return True

        assert buy_stock(code="600519", price=100) is True

        with pytest.raises(ValidationException):
            buy_stock(code=None, price=100)


class TestDataSource:
    """测试数据源"""

    def test_data_source_initialization(self):
        """测试数据源初始化"""
        from quant_system.data_sources import DataSource

        ds = DataSource()
        assert ds is not None
        assert "tencent" in ds.source_status
        assert "iwencai" in ds.source_status

    def test_realtime_quote(self):
        """测试实时行情"""
        from quant_system.data_sources import DataSource

        ds = DataSource()
        if ds.source_status["tencent"]["ok"]:
            quotes = ds.get_realtime_quote(["sh600519"])
            assert len(quotes) > 0
            assert "sh600519" in quotes or "600519" in quotes


class TestFactorLibrary:
    """测试因子库"""

    def test_factor_extraction(self):
        """测试因子提取"""
        import pandas as pd
        import numpy as np
        from quant_system.factor_library import FactorEngine

        data = pd.DataFrame(
            {
                "close": np.random.rand(100) * 100,
                "high": np.random.rand(100) * 100,
                "low": np.random.rand(100) * 100,
                "open": np.random.rand(100) * 100,
                "volume": np.random.rand(100) * 1000000,
            }
        )

        engine = FactorEngine()
        factor_vector, factor_dict = engine.process(data)

        assert len(factor_dict) > 0
        assert "return_1d" in factor_dict or len(factor_dict) > 0


class TestSmartSell:
    """测试智能卖出策略"""

    def test_sell_analysis(self):
        """测试卖出分析"""
        import pandas as pd
        import numpy as np
        from quant_system.smart_sell_strategy import SmartSellStrategy

        strategy = SmartSellStrategy()

        position = {
            "code": "600519",
            "name": "贵州茅台",
            "entry_price": 1800.0,
            "current_price": 1900.0,
            "shares": 100,
        }

        market_data = pd.DataFrame(
            {
                "close": np.random.rand(30) * 2000 + 1800,
                "high": np.random.rand(30) * 2000 + 1800,
                "low": np.random.rand(30) * 1800,
                "volume": np.random.rand(30) * 1000000,
            }
        )

        fund_data = pd.DataFrame(
            {
                "main_flow": np.random.randn(30) * 1000,
                "ddx": np.random.randn(30),
            }
        )

        result = strategy.analyze_sell_opportunity(position, market_data, fund_data)

        assert "should_sell" in result
        assert "sell_ratio" in result
        assert "sell_reason" in result


class TestPositionMonitor:
    """测试持仓监控"""

    def test_position_check(self):
        """测试持仓检查"""
        from quant_system.position_monitor import load_positions, check_position_v2

        # 测试加载持仓（可能返回None，因为测试环境没有positions.json）
        positions = load_positions()
        # 只要函数能正常执行就算通过
        assert positions is None or isinstance(positions, dict)


class TestBacktestEngine:
    """测试回测引擎"""

    def test_backtest_initialization(self):
        """测试回测引擎初始化"""
        from quant_system.backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_capital=1000000)
        assert engine is not None
        assert engine.initial_capital == 1000000


class TestConfigValidation:
    """测试配置校验"""

    def test_env_loading(self):
        """测试环境变量加载"""
        import os
        from pathlib import Path

        env_file = Path(__file__).parent.parent / ".env.example"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()

            assert "IWENCAI_API_KEY" in content
            assert "LONGCAT_API_KEY" in content
            assert "LOG_LEVEL" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
