"""
持仓监控模块
集成原有的 position_monitor.py 逻辑
"""
import json
import subprocess
from typing import List, Dict, Optional

class PositionMonitor:
    """持仓监控模块"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化持仓监控器
        
        Args:
            config: 配置字典，包含止损/止盈参数
        """
        self.config = config or {
            'stop_loss': -3.0,      # 止损线 -3%
            'stop_profit': 10.0,    # 止盈线 +10%
            'trailing_stop': 2.0,   # 移动止损 2%
            'ddx_exit_threshold': -2.0  # DDX退出阈值
        }
    
    def check(self, positions: List[Dict]) -> List[Dict]:
        """
        批量检查持仓，返回预警信息
        
        Args:
            positions: 持仓列表，每个元素包含symbol, cost, shares, current_price
            
        Returns:
            预警列表，每个元素包含symbol, action, reason, urgency
        """
        try:
            # 写入临时文件
            temp_file = 'temp_positions.json'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, ensure_ascii=False)
            
            # 调用原有的 position_monitor.py 脚本
            result = subprocess.run(
                ['python', '../quant_system/position_monitor.py',
                 '--batch', '--input', temp_file],
                capture_output=True,
                text=True,
                cwd='C:/Users/zhuyi/.qclaw/workspace-agent-e50de693'
            )
            
            # 清理临时文件
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            if result.returncode != 0:
                raise Exception(f"持仓监控脚本执行失败: {result.stderr}")
            
            alerts = json.loads(result.stdout)
            return alerts
            
        except Exception as e:
            print(f"持仓监控失败: {e}")
            return []
    
    def check_single(self, position: Dict) -> Optional[Dict]:
        """
        检查单个持仓
        
        Args:
            position: 持仓信息字典
            
        Returns:
            预警信息，如果没有预警返回None
        """
        alerts = self.check([position])
        return alerts[0] if alerts else None
    
    def update_config(self, new_config: Dict):
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)