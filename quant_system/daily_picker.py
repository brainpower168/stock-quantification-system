"""
每日选股模块
集成原有的 daily_pick.py 逻辑
"""
import json
import subprocess
from typing import List, Dict, Optional

class DailyPicker:
    """每日选股模块"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化选股器
        
        Args:
            config: 配置字典，包含权重、阈值等参数
        """
        self.config = config or {
            'top_n': 3,
            'min_score': 60.0,
            'weights': {
                'ddx': 0.30,
                'momentum': 0.20,
                'trend': 0.15,
                'fundamental': 0.15,
                'sentiment': 0.10,
                'event': 0.10
            }
        }
    
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
            # 调用原有的 daily_pick.py 脚本
            result = subprocess.run(
                ['python', '../quant_system/daily_pick.py',
                 '--top-n', str(top_n),
                 '--min-score', str(min_score)],
                capture_output=True,
                text=True,
                cwd='C:/Users/zhuyi/.qclaw/workspace-agent-e50de693'
            )
            
            if result.returncode != 0:
                raise Exception(f"选股脚本执行失败: {result.stderr}")
            
            picks = json.loads(result.stdout)
            return picks
            
        except Exception as e:
            print(f"选股失败: {e}")
            return []
    
    @classmethod
    def from_config(cls, config_path: str) -> 'DailyPicker':
        """
        从配置文件加载
        
        Args:
            config_path: 配置文件路径（JSON格式）
            
        Returns:
            DailyPicker实例
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return cls(config)
    
    def update_config(self, new_config: Dict):
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)