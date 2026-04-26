"""
市场情绪分析模块
集成原有的 sentiment_report.py 逻辑
"""
import json
import subprocess
from typing import Dict, Optional

class SentimentAnalyzer:
    """市场情绪分析模块"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化情绪分析器
        
        Args:
            config: 配置字典，包含情绪指标阈值
        """
        self.config = config or {
            'fear_greed_threshold': 70,  # 恐贪指数阈值
            'limit_up_threshold': 50,      # 涨停板数量阈值
            'north_bound_threshold': 100,   # 北向资金阈值（亿）
        }
    
    def analyze(self) -> Dict:
        """
        执行情绪分析，返回情绪报告
        
        Returns:
            情绪报告字典，包含恐贪指数、涨跌停比、北向资金、板块热度、操作建议
        """
        try:
            # 调用原有的 sentiment_report.py 脚本
            result = subprocess.run(
                ['python', '../quant_system/sentiment_report.py'],
                capture_output=True,
                text=True,
                cwd='C:/Users/zhuyi/.qclaw/workspace-agent-e50de693'
            )
            
            if result.returncode != 0:
                raise Exception(f"情绪分析脚本执行失败: {result.stderr}")
            
            report = json.loads(result.stdout)
            return report
            
        except Exception as e:
            print(f"情绪分析失败: {e}")
            return {}
    
    def get_trading_suggestion(self) -> str:
        """
        根据情绪分析给出操作建议
        
        Returns:
            操作建议字符串
        """
        report = self.analyze()
        
        fear_greed = report.get('fear_greed_index', 50)
        limit_up_count = report.get('limit_up_count', 0)
        north_bound = report.get('north_bound_flow', 0)
        
        suggestion = "持有观望"
        
        if fear_greed > self.config['fear_greed_threshold']:
            suggestion = "谨慎追高"
        elif fear_greed < 30:
            suggestion = "可以低吸"
        
        if limit_up_count > self.config['limit_up_threshold']:
            suggestion += "，涨停板数量多，情绪亢奋"
        
        if north_bound > self.config['north_bound_threshold']:
            suggestion += "，北向资金大幅流入"
        elif north_bound < -self.config['north_bound_threshold']:
            suggestion += "，北向资金大幅流出，注意风险"
        
        return suggestion
    
    def update_config(self, new_config: Dict):
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)