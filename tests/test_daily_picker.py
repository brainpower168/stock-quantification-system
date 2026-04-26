"""
每日选股模块测试
"""
import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_system.daily_picker import DailyPicker


class TestDailyPicker:
    """测试DailyPicker类"""
    
    def test_init(self):
        """测试初始化"""
        picker = DailyPicker()
        assert picker is not None
        assert picker.config['top_n'] == 3
        assert picker.config['min_score'] == 60.0
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {
            'top_n': 5,
            'min_score': 70.0
        }
        picker = DailyPicker(config)
        assert picker.config['top_n'] == 5
        assert picker.config['min_score'] == 70.0
    
    def test_update_config(self):
        """测试更新配置"""
        picker = DailyPicker()
        new_config = {'top_n': 10}
        picker.update_config(new_config)
        assert picker.config['top_n'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])