"""
优化版选股器 - 减少AI调用次数

优化策略：
1. 先用规则筛选（不调用AI）
2. 只对筛选出的股票调用DeepSeek分析
3. 缓存AI分析结果（1小时有效）
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 添加路径
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from council_engine import AITradingCouncil


class OptimizedSelector:
    """优化版选股器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent / "config" / "council_config.json"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.council = AITradingCouncil()
        self.cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def rule_based_filter(self, stocks: List[Dict]) -> List[Dict]:
        """
        规则筛选（不调用AI）

        筛选条件：
        - DDX > 0
        - 主力流入 > 5000万
        - 涨幅 < 5%
        - ROE > 10%
        - PE < 50
        """
        filtered = []

        for stock in stocks:
            # 提取数据
            code = stock.get("code", "")
            name = stock.get("name", code)
            ddx_10d = stock.get("ddx_10d", 0)
            main_inflow = stock.get("main_inflow", 0)  # 亿元
            change_pct = stock.get("change_pct", 0)
            roe = stock.get("roe", 0)
            pe = stock.get("pe", 999)

            # 筛选条件
            reasons = []
            score = 0

            # DDX > 0
            if ddx_10d > 0:
                score += 25
                reasons.append(f"10日DDX={ddx_10d:.2f}")
            else:
                continue  # 不符合条件，跳过

            # 主力流入 > 5000万
            if main_inflow > 0.5:
                score += 25
                reasons.append(f"主力流入{main_inflow:.2f}亿")
            else:
                continue  # 不符合条件，跳过

            # 涨幅 < 5%
            if change_pct < 5:
                score += 20
                reasons.append(f"涨幅{change_pct:.2f}%")
            else:
                continue  # 不符合条件，跳过

            # ROE > 10%（加分项）
            if roe > 10:
                score += 15
                reasons.append(f"ROE={roe:.1f}%")

            # PE < 50（加分项）
            if pe < 50:
                score += 15
                reasons.append(f"PE={pe:.1f}")

            # 添加到筛选结果
            filtered.append(
                {
                    "code": code,
                    "name": name,
                    "score": score,
                    "reasons": reasons,
                    "data": stock,
                }
            )

        # 按得分排序
        filtered.sort(key=lambda x: x["score"], reverse=True)

        return filtered

    def get_cached_analysis(self, code: str) -> Optional[Dict]:
        """获取缓存的AI分析结果"""
        cache_file = self.cache_dir / f"{code}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # 检查缓存是否过期（1小时）
            cache_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cache_time < timedelta(hours=1):
                return cached
            else:
                return None
        except:
            return None

    def save_cached_analysis(self, code: str, analysis: Dict):
        """保存AI分析结果到缓存"""
        cache_file = self.cache_dir / f"{code}.json"

        analysis["timestamp"] = datetime.now().isoformat()

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

    def analyze_with_cache(self, stock: Dict, use_cache: bool = True) -> Dict:
        """带缓存的AI分析"""
        code = stock["code"]

        # 检查缓存
        if use_cache:
            cached = self.get_cached_analysis(code)
            if cached:
                print(f"  ✓ 使用缓存: {stock['name']}")
                return cached

        # 调用AI分析（只调用DeepSeek）
        print(f"  → AI分析: {stock['name']}")

        try:
            # 准备市场数据
            market_data = {
                "price": stock["data"].get("price", 0),
                "change_pct": stock["data"].get("change_pct", 0),
                "volume_ratio": stock["data"].get("volume_ratio", 0),
                "turnover_rate": stock["data"].get("turnover_rate", 0),
                "main_inflow": stock["data"].get("main_inflow", 0),
                "ddx_10d": stock["data"].get("ddx_10d", 0),
                "roe": stock["data"].get("roe", 0),
                "pe": stock["data"].get("pe", 0),
            }

            # 调用AI Council（只调用DeepSeek）
            result = self.council.analyze_stock(
                stock_code=code, stock_name=stock["name"], market_data=market_data
            )

            # 构建分析结果
            analysis = {
                "code": code,
                "name": stock["name"],
                "decision": result.final_decision,
                "confidence": result.confidence,
                "reasoning": result.votes[0].reasoning if result.votes else "",
                "risk_warnings": result.risk_warnings,
            }

            # 保存到缓存
            self.save_cached_analysis(code, analysis)

            return analysis

        except Exception as e:
            print(f"  ✗ AI分析失败: {e}")
            return {
                "code": code,
                "name": stock["name"],
                "decision": "ERROR",
                "confidence": 0,
                "reasoning": f"AI分析失败: {e}",
                "risk_warnings": [],
            }

    def run_optimized_selection(
        self, stocks: List[Dict], max_ai_calls: int = 20, use_cache: bool = True
    ) -> Dict:
        """
        运行优化版选股

        Args:
            stocks: 股票列表
            max_ai_calls: 最大AI调用次数
            use_cache: 是否使用缓存

        Returns:
            选股结果
        """
        print(f"\n=== 优化版选股 ===")
        print(f"输入股票数: {len(stocks)}")
        print(f"最大AI调用次数: {max_ai_calls}")
        print(f"使用缓存: {use_cache}")

        # Step 1: 规则筛选
        print(f"\n[Step 1] 规则筛选...")
        filtered = self.rule_based_filter(stocks)
        print(f"筛选结果: {len(filtered)}只股票符合条件")

        if not filtered:
            return {
                "total_input": len(stocks),
                "filtered_count": 0,
                "analyzed_count": 0,
                "recommendations": [],
            }

        # Step 2: AI分析（限制调用次数）
        print(f"\n[Step 2] AI分析（最多{max_ai_calls}只）...")
        analyzed = []

        for i, stock in enumerate(filtered[:max_ai_calls]):
            print(
                f"[{i + 1}/{min(len(filtered), max_ai_calls)}] {stock['name']} ({stock['code']})"
            )
            analysis = self.analyze_with_cache(stock, use_cache)
            analyzed.append({**stock, "analysis": analysis})

        # Step 3: 生成推荐
        print(f"\n[Step 3] 生成推荐...")
        recommendations = []

        for stock in analyzed:
            decision = stock["analysis"]["decision"]
            confidence = stock["analysis"]["confidence"]

            # 只推荐BUY和OVERWEIGHT
            if decision in ["BUY", "OVERWEIGHT"] and confidence > 0.5:
                recommendations.append(
                    {
                        "code": stock["code"],
                        "name": stock["name"],
                        "score": stock["score"],
                        "decision": decision,
                        "confidence": confidence,
                        "reasons": stock["reasons"],
                        "reasoning": stock["analysis"]["reasoning"][:200],
                        "risk_warnings": stock["analysis"]["risk_warnings"],
                    }
                )

        # 按得分排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        print(f"\n=== 选股结果 ===")
        print(f"输入股票: {len(stocks)}只")
        print(f"规则筛选: {len(filtered)}只")
        print(f"AI分析: {len(analyzed)}只")
        print(f"推荐股票: {len(recommendations)}只")

        return {
            "total_input": len(stocks),
            "filtered_count": len(filtered),
            "analyzed_count": len(analyzed),
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """测试优化版选股器"""

    # 模拟股票数据
    test_stocks = [
        {
            "code": "600519",
            "name": "贵州茅台",
            "price": 1850,
            "change_pct": 2.5,
            "ddx_10d": 3.5,
            "main_inflow": 5.2,
            "roe": 30,
            "pe": 35,
        },
        {
            "code": "300750",
            "name": "宁德时代",
            "price": 180,
            "change_pct": 3.2,
            "ddx_10d": 2.8,
            "main_inflow": 8.5,
            "roe": 15,
            "pe": 40,
        },
        {
            "code": "000001",
            "name": "平安银行",
            "price": 12,
            "change_pct": 1.5,
            "ddx_10d": 1.2,
            "main_inflow": 0.8,
            "roe": 12,
            "pe": 6,
        },
        {
            "code": "002475",
            "name": "立讯精密",
            "price": 35,
            "change_pct": 4.8,
            "ddx_10d": -0.5,
            "main_inflow": 1.2,
            "roe": 18,
            "pe": 25,
        },  # DDX负，不符合
        {
            "code": "002460",
            "name": "赣锋锂业",
            "price": 40,
            "change_pct": 6.2,
            "ddx_10d": 1.5,
            "main_inflow": 3.5,
            "roe": 8,
            "pe": 60,
        },  # 涨幅超5%，不符合
    ]

    # 创建选股器
    selector = OptimizedSelector()

    # 运行选股
    result = selector.run_optimized_selection(
        stocks=test_stocks,
        max_ai_calls=3,  # 最多分析3只
        use_cache=True,
    )

    # 输出结果
    print(f"\n=== 推荐股票 ===")
    for i, rec in enumerate(result["recommendations"], 1):
        print(f"\n{i}. {rec['name']} ({rec['code']})")
        print(f"   得分: {rec['score']}")
        print(f"   决策: {rec['decision']} (置信度{rec['confidence']:.0%})")
        print(f"   理由: {', '.join(rec['reasons'])}")
        print(f"   AI分析: {rec['reasoning']}")


if __name__ == "__main__":
    main()
