"""
持仓监控模块测试
"""
import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_system.position_monitor import PositionMonitor


class TestPositionMonitor:
    """测试PositionMonitor类"""
    
    def test_init(self):
        """测试初始化"""
        monitor = PositionMonitor()
        assert monitor is not None
        assert monitor.config['stop_loss'] == -3.0
        assert monitor.config['stop_profit'] == 10.0
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {
            'stop_loss': -5.0,
            'stop_profit': 15.0
        }
        monitor = PositionMonitor(config)
        assert monitor.config['stop_loss'] == -5.0
        assert monitor.config['stop_profit'] == 15.0
    
    def test_update_config(self):
        """测试更新配置"""
        monitor = PositionMonitor()
        new_config = {'stop_loss': -4.0}
        monitor.update_config(new_config)
        assert monitor.config['stop_loss'] == -4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])