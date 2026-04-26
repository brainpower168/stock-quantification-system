"""
量化系统HTTP API服务
基于FastAPI封装所有量化模块
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# 添加父目录到路径，以便导入quant_system包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_system import DailyPicker, PositionMonitor, SentimentAnalyzer, Backtester

app = FastAPI(
    title="炒股大师量化系统API",
    description="多因子选股、持仓监控、情绪分析、回测验证",
    version="1.0.0"
)

# 请求模型
class PickRequest(BaseModel):
    top_n: int = 3
    min_score: float = 60.0

class Position(BaseModel):
    symbol: str
    cost: float
    shares: int
    current_price: Optional[float] = None

class PositionsRequest(BaseModel):
    positions: List[Position]

class BacktestRequest(BaseModel):
    strategy: str
    params: Optional[dict] = None

# API端点
@app.get("/")
async def root():
    return {
        "service": "quant-system",
        "version": "1.0.0",
        "endpoints": [
            "/api/daily-pick",
            "/api/check-positions",
            "/api/sentiment",
            "/api/backtest"
        ]
    }

@app.post("/api/daily-pick")
async def daily_pick(req: PickRequest):
    """
    每日选股API
    """
    try:
        picker = DailyPicker()
        picks = picker.pick(top_n=req.top_n, min_score=req.min_score)
        return {"status": "success", "data": picks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/check-positions")
async def check_positions(req: PositionsRequest):
    """
    批量检查持仓API
    """
    try:
        monitor = PositionMonitor()
        positions = [p.dict() for p in req.positions]
        alerts = monitor.check(positions)
        return {"status": "success", "data": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sentiment")
async def get_sentiment():
    """
    市场情绪分析API
    """
    try:
        analyzer = SentimentAnalyzer()
        report = analyzer.analyze()
        suggestion = analyzer.get_trading_suggestion()
        return {
            "status": "success",
            "data": report,
            "suggestion": suggestion
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    """
    策略回测API
    """
    try:
        backtester = Backtester()
        result = backtester.run(strategy=req.strategy, params=req.params)
        validation = backtester.validate_strategy(strategy=req.strategy, params=req.params)
        return {
            "status": "success",
            "result": result,
            "validation": validation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)