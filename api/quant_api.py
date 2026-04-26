# -*- coding: utf-8 -*-
"""
量化系统HTTP API服务 v1.1
集成统一数据源，连接真实行情

Author: 炒股大师量化系统
"""
import sys
import os

# 设置UTF-8编码（Windows兼容）
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import traceback

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_system import (
    DailyPicker, PositionMonitor, SentimentAnalyzer, Backtester,
    LimitUpTracker, AuctionSentiment, SectorHotTracker, LhbTracker,
    EventScanner, RiskManager, NorthMoneyTracker, BacktestEngine
)
from quant_system.data_sources import DataSource

# 初始化FastAPI
app = FastAPI(
    title="炒股大师量化系统API",
    description="多因子选股 | 实时行情 | 涨停追踪 | 智能风控 | 回测验证",
    version="1.1.0"
)

# CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据源实例（启动时初始化）
_ds: Optional[DataSource] = None

@app.on_event("startup")
async def startup():
    global _ds
    _ds = DataSource()
    print("数据源初始化完成")

# ============ 请求模型 ============

class PickRequest(BaseModel):
    top_n: int = 3
    min_score: float = 60.0

class Position(BaseModel):
    code: str
    name: str
    shares: int
    cost: float
    current_price: Optional[float] = None

class PositionsRequest(BaseModel):
    positions: List[Position]

class BacktestRequest(BaseModel):
    strategy: str
    params: Optional[Dict] = None

class QuoteRequest(BaseModel):
    codes: List[str]  # 如 ["sh000001", "sh600519", "sz000858"]

class StockAnalyzeRequest(BaseModel):
    code: str  # 如 "000001" 或 "sh000001"

class KellyRequest(BaseModel):
    win_rate: float  # 胜率 0-1
    avg_win: float   # 平均盈利比例 如0.08表示+8%
    avg_loss: float  # 平均亏损比例 如0.03表示-3%

# ============ 核心API ============

@app.get("/")
async def root():
    """API首页"""
    return {
        "service": "炒股大师量化系统",
        "version": "1.1.0",
        "status": "running",
        "data_sources": {
            "tencent": "✅",
            "iwencai": "✅",
            "sina": "✅"
        }
    }

@app.get("/api/v1/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "version": "1.1.0"}

@app.get("/api/v1/sources")
async def source_status():
    """数据源状态"""
    if _ds is None:
        return {"error": "数据源未初始化"}
    return _ds.source_status

@app.get("/api/v1/market/sentiment")
async def market_sentiment():
    """市场情绪"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        sentiment = _ds.get_market_sentiment()
        return {"status": "success", "data": sentiment}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/quote/realtime")
async def realtime_quote(req: QuoteRequest):
    """实时行情"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        # 补全代码前缀
        codes = []
        for c in req.codes:
            c = c.strip()
            if not c.startswith(('sh', 'sz', 'bj')):
                # 尝试自动判断
                if c.startswith('6'):
                    codes.append(f'sh{c}')
                elif c.startswith(('0', '3')):
                    codes.append(f'sz{c}')
                else:
                    codes.append(f'sh{c}')
            else:
                codes.append(c)
        
        quotes = _ds.get_realtime_quote(codes)
        return {"status": "success", "count": len(quotes), "data": quotes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/limit-up")
async def limit_up_stocks():
    """今日涨停股"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        stocks = _ds.get_limit_up_stocks()
        return {"status": "success", "count": len(stocks), "data": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/active")
async def active_stocks(limit: int = 20):
    """今日活跃股"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        stocks = _ds.get_active_stocks(limit=limit)
        return {"status": "success", "count": len(stocks), "data": stocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/main-flow/{code}")
async def main_flow(code: str):
    """主力资金流向"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        flow = _ds.get_main_flow(code)
        return {"status": "success", "data": flow}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/stock/analyze")
async def analyze_stock(req: StockAnalyzeRequest):
    """股票综合分析"""
    if _ds is None:
        raise HTTPException(status_code=503, detail="数据源未初始化")
    try:
        code = req.code.strip()
        if not code.startswith(('sh', 'sz')):
            code = f'sz{code}' if code.startswith(('0', '3')) else f'sh{code}'
        
        # 获取行情
        quotes = _ds.get_realtime_quote([code])
        quote = quotes.get(code, {})
        
        # 获取资金流向
        flow = _ds.get_main_flow(code)
        
        # 生成分析报告
        price = quote.get('price', 0)
        change_pct = quote.get('change_pct', 0)
        
        # 简单评分
        score = 50
        if change_pct > 0:
            score += min(change_pct * 3, 25)
        else:
            score += max(change_pct * 3, -25)
        
        # 资金面加成
        main_net = flow.get('main_net_inflow', 0)
        if isinstance(main_net, (int, float)) and main_net > 0:
            score += min(main_net / 100000000 * 10, 20)
        elif isinstance(main_net, (int, float)) and main_net < 0:
            score += max(main_net / 100000000 * 10, -20)
        
        score = max(0, min(100, score))
        
        # 操作建议
        if score >= 80:
            action = "强力买入"
        elif score >= 65:
            action = "建议买入"
        elif score >= 45:
            action = "观望"
        elif score >= 30:
            action = "谨慎"
        else:
            action = "建议卖出"
        
        return {
            "status": "success",
            "data": {
                "code": code,
                "name": quote.get('name', ''),
                "price": price,
                "change_pct": change_pct,
                "volume": quote.get('volume', 0),
                "turnover": quote.get('turnover', 0),
                "high": quote.get('high', 0),
                "low": quote.get('low', 0),
                "main_net_inflow": main_net,
                "score": score,
                "action": action,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ 量化模块API ============

@app.post("/api/v1/daily-pick")
async def daily_pick(req: PickRequest):
    """每日选股"""
    try:
        picker = DailyPicker()
        picks = picker.pick(top_n=req.top_n, min_score=req.min_score)
        return {"status": "success", "data": picks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/check-positions")
async def check_positions(req: PositionsRequest):
    """检查持仓"""
    try:
        monitor = PositionMonitor()
        positions = [p.dict() for p in req.positions]
        alerts = monitor.check(positions)
        return {"status": "success", "data": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sentiment")
async def sentiment():
    """情绪分析"""
    try:
        analyzer = SentimentAnalyzer()
        report = analyzer.analyze()
        suggestion = analyzer.get_trading_suggestion()
        return {"status": "success", "data": report, "suggestion": suggestion}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/backtest")
async def backtest(req: BacktestRequest):
    """策略回测"""
    try:
        backtester = Backtester()
        result = backtester.run(strategy=req.strategy, params=req.params)
        validation = backtester.validate_strategy(strategy=req.strategy, params=req.params)
        return {"status": "success", "result": result, "validation": validation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/risk/kelly")
async def kelly_position(req: KellyRequest):
    """凯利公式计算仓位"""
    try:
        risk_mgr = RiskManager()
        position = risk_mgr.calculate_kelly_position(
            win_rate=req.win_rate,
            avg_win=req.avg_win,
            avg_loss=req.avg_loss
        )
        # 半凯利（保守）
        half_kelly = position * 0.5
        
        return {
            "status": "success",
            "data": {
                "kelly_full": round(position * 100, 2),
                "kelly_half": round(half_kelly * 100, 2),
                "recommendation": f"建议仓位 {half_kelly*100:.1f}%（半凯利保守）",
                "input": {
                    "win_rate": req.win_rate,
                    "avg_win": req.avg_win,
                    "avg_loss": req.avg_loss
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/risk/position-size")
async def position_size(win_rate: float, avg_loss: float, account_equity: float, stock_price: float):
    """计算买入股数"""
    try:
        risk_mgr = RiskManager()
        # 假设每笔最大亏损2%
        shares, ratio = risk_mgr.calculate_position_size(
            account_equity=account_equity,
            stock_price=stock_price,
            stop_loss_pct=avg_loss,
            max_loss_pct=0.02
        )
        return {
            "status": "success",
            "data": {
                "shares": shares,
                "position_ratio": round(ratio * 100, 2),
                "cost": shares * stock_price,
                "max_loss": account_equity * 0.02
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/limit-up-tracker")
async def limit_up_tracker():
    """涨停板追踪"""
    try:
        tracker = LimitUpTracker()
        report = tracker.generate_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/auction-sentiment")
async def auction_sentiment():
    """竞价情绪分析"""
    try:
        analyzer = AuctionSentiment()
        return {"status": "success", "data": {"message": "竞价分析需要9:15-9:25运行"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sector-hot")
async def sector_hot():
    """题材热点"""
    try:
        tracker = SectorHotTracker()
        report = tracker.generate_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/lhb")
async def lhb_tracker():
    """龙虎榜"""
    try:
        tracker = LhbTracker()
        report = tracker.generate_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/north-money")
async def north_money():
    """北向资金"""
    try:
        tracker = NorthMoneyTracker()
        report = tracker.generate_north_money_report()
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
