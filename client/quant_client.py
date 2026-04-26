"""
量化系统Python客户端库
方便其他Python机器人调用量化系统API
"""
import requests
from typing import List, Dict, Optional

class QuantClient:
    """
    量化系统客户端
    用于调用量化系统API服务
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            base_url: API服务的基础URL
        """
        self.base_url = base_url.rstrip('/')
    
    def get_daily_picks(self, top_n: int = 3, min_score: float = 60.0) -> Dict:
        """
        获取每日选股推荐
        
        Args:
            top_n: 返回推荐数量
            min_score: 最低评分阈值
            
        Returns:
            API响应字典，包含status、data字段
        """
        url = f"{self.base_url}/api/daily-pick"
        payload = {
            "top_n": top_n,
            "min_score": min_score
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def check_positions(self, positions: List[Dict]) -> Dict:
        """
        批量检查持仓风险
        
        Args:
            positions: 持仓列表，每个元素包含symbol, cost, shares, current_price
            
        Returns:
            API响应字典，包含status、data字段
        """
        url = f"{self.base_url}/api/check-positions"
        payload = {"positions": positions}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_sentiment(self) -> Dict:
        """
        获取市场情绪分析
        
        Returns:
            API响应字典，包含status、data、suggestion字段
        """
        url = f"{self.base_url}/api/sentiment"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def run_backtest(self, strategy: str, params: Optional[Dict] = None) -> Dict:
        """
        运行策略回测
        
        Args:
            strategy: 策略名称
            params: 策略参数字典（可选）
            
        Returns:
            API响应字典，包含status、result、validation字段
        """
        url = f"{self.base_url}/api/backtest"
        payload = {
            "strategy": strategy,
            "params": params or {}
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def health_check(self) -> Dict:
        """
        健康检查
        
        Returns:
            API响应字典
        """
        url = f"{self.base_url}/api/health"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": str(e)
            }


# 使用示例
if __name__ == "__main__":
    # 创建客户端
    client = QuantClient(base_url="http://localhost:8000")
    
    # 健康检查
    health = client.health_check()
    print(f"健康检查: {health}")
    
    # 获取每日选股
    picks = client.get_daily_picks(top_n=3)
    print(f"每日选股: {picks}")
    
    # 检查持仓
    positions = [
        {"symbol": "603931", "cost": 32.00, "shares": 1000, "current_price": 31.50},
        {"symbol": "002001", "cost": 36.60, "shares": 500, "current_price": 35.80}
    ]
    alerts = client.check_positions(positions)
    print(f"持仓预警: {alerts}")
    
    # 获取市场情绪
    sentiment = client.get_sentiment()
    print(f"市场情绪: {sentiment}")
    
    # 运行回测
    backtest = client.run_backtest(strategy="limit_up", params={"holding_period": 5})
    print(f"回测结果: {backtest}")