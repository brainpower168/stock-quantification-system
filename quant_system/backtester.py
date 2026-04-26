"""
回测验证模块
集成原有的 backtest_validate.py 逻辑
"""
import json
import subprocess
from typing import Dict, List, Optional

class Backtester:
    """回测验证模块"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化回测器
        
        Args:
            config: 配置字典，包含回测参数
        """
        self.config = config or {
            'start_date': '2020-01-01',
            'end_date': '2025-12-31',
            'initial_capital': 100000,
            'commission': 0.0003,
            'slippage': 0.001
        }
    
    def run(self, strategy: str, params: Optional[Dict] = None) -> Dict:
        """
        运行回测
        
        Args:
            strategy: 策略名称（如 'limit_up', 'ddx_strategy'）
            params: 策略参数
            
        Returns:
            回测结果字典，包含胜率、总盈亏、最大回撤等
        """
        try:
            # 调用原有的 backtest_validate.py 脚本
            cmd = [
                'python', '../quant_system/backtest_validate.py',
                '--strategy', strategy
            ]
            
            if params:
                cmd.extend(['--params', json.dumps(params)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd='C:/Users/zhuyi/.qclaw/workspace-agent-e50de693'
            )
            
            if result.returncode != 0:
                raise Exception(f"回测脚本执行失败: {result.stderr}")
            
            backtest_result = json.loads(result.stdout)
            return backtest_result
            
        except Exception as e:
            print(f"回测失败: {e}")
            return {}
    
    def validate_strategy(self, strategy: str, params: Optional[Dict] = None) -> Dict:
        """
        验证策略有效性
        
        Args:
            strategy: 策略名称
            params: 策略参数
            
        Returns:
            验证报告字典，包含是否通过、建议等
        """
        result = self.run(strategy, params)
        
        validation = {
            'strategy': strategy,
            'passed': False,
            'win_rate': result.get('win_rate', 0),
            'total_return': result.get('total_return', 0),
            'max_drawdown': result.get('max_drawdown', 0),
            'suggestion': ''
        }
        
        # 判断是否通过验证
        if (validation['win_rate'] >= 0.55 and 
            validation['total_return'] > 0 and 
            validation['max_drawdown'] < 0.2):
            validation['passed'] = True
            validation['suggestion'] = '策略有效，可以启用'
        else:
            validation['suggestion'] = '策略效果不佳，建议优化参数'
        
        return validation
    
    def update_config(self, new_config: Dict):
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)