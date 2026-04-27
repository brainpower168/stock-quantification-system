#!/usr/bin/env python3
"""
推荐追踪验证系统
记录AI推荐，定期验证准确率
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class RecommendationTracker:
    """推荐追踪器"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.tracking_file = self.data_dir / "recommendation_tracking.jsonl"

    def record_recommendation(
        self,
        stock_code: str,
        stock_name: str,
        decision: str,
        confidence: float,
        price: float,
        reasons: List[str] = None,
        models: Dict = None,
    ):
        """记录推荐"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
            "stock_name": stock_name,
            "decision": decision,
            "confidence": confidence,
            "price": price,
            "reasons": reasons or [],
            "models": models or {},
            "verified": False,
            "verify_time": None,
            "verify_price": None,
            "verify_change_pct": None,
            "result": None,  # success, fail, neutral
        }

        with open(self.tracking_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(
            f"已记录推荐: {stock_name}({stock_code}) {decision} 置信度{confidence:.0%}"
        )
        return record

    def get_unverified(self, days: int = 3) -> List[Dict]:
        """获取未验证的推荐（超过指定天数）"""
        if not self.tracking_file.exists():
            return []

        unverified = []
        cutoff = datetime.now() - timedelta(days=days)

        with open(self.tracking_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if not record.get("verified"):
                        record_time = datetime.fromisoformat(record["timestamp"])
                        if record_time < cutoff:
                            unverified.append(record)
                except:
                    continue

        return unverified

    def verify_recommendation(
        self, stock_code: str, current_price: float
    ) -> Optional[Dict]:
        """验证推荐结果"""
        if not self.tracking_file.exists():
            return None

        records = []
        verified_record = None

        with open(self.tracking_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record["stock_code"] == stock_code and not record.get(
                        "verified"
                    ):
                        # 计算涨跌幅
                        original_price = record["price"]
                        change_pct = (
                            (current_price - original_price) / original_price * 100
                        )

                        # 判断结果
                        decision = record["decision"]
                        if decision in ["STRONG_BUY", "BUY"]:
                            if change_pct > 5:
                                result = "success"
                            elif change_pct > 0:
                                result = "neutral"
                            else:
                                result = "fail"
                        elif decision in ["STRONG_SELL", "SELL"]:
                            if change_pct < -5:
                                result = "success"
                            elif change_pct < 0:
                                result = "neutral"
                            else:
                                result = "fail"
                        else:
                            result = "neutral"

                        # 更新记录
                        record["verified"] = True
                        record["verify_time"] = datetime.now().isoformat()
                        record["verify_price"] = current_price
                        record["verify_change_pct"] = change_pct
                        record["result"] = result
                        verified_record = record

                        print(
                            f"验证结果: {record['stock_name']} {decision} -> {result}"
                        )
                        print(
                            f"  原价: {original_price}, 现价: {current_price}, 涨跌: {change_pct:+.2f}%"
                        )
                    records.append(record)
                except:
                    continue

        # 重写文件
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return verified_record

    def get_accuracy_stats(self, days: int = 30) -> Dict:
        """获取准确率统计"""
        if not self.tracking_file.exists():
            return {"total": 0, "success": 0, "fail": 0, "accuracy": 0}

        cutoff = datetime.now() - timedelta(days=days)
        stats = {"total": 0, "success": 0, "fail": 0, "neutral": 0}

        with open(self.tracking_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("verified"):
                        record_time = datetime.fromisoformat(record["timestamp"])
                        if record_time > cutoff:
                            stats["total"] += 1
                            result = record.get("result", "neutral")
                            stats[result] = stats.get(result, 0) + 1
                except:
                    continue

        if stats["total"] > 0:
            stats["accuracy"] = stats["success"] / stats["total"] * 100
        else:
            stats["accuracy"] = 0

        return stats

    def print_stats(self):
        """打印统计"""
        stats = self.get_accuracy_stats()

        print(f"\n{'=' * 50}")
        print(f"AI推荐准确率统计（近30天）")
        print(f"{'=' * 50}")
        print(f"总推荐数: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失败: {stats['fail']}")
        print(f"中性: {stats['neutral']}")
        print(f"准确率: {stats['accuracy']:.1f}%")
        print(f"{'=' * 50}\n")


# 便捷函数
_tracker = None


def get_tracker() -> RecommendationTracker:
    """获取追踪器单例"""
    global _tracker
    if _tracker is None:
        _tracker = RecommendationTracker()
    return _tracker


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="推荐追踪验证系统")
    parser.add_argument("--stats", action="store_true", help="显示准确率统计")
    parser.add_argument("--unverified", action="store_true", help="显示未验证的推荐")
    parser.add_argument("--verify", type=str, help="验证指定股票代码")
    parser.add_argument("--price", type=float, help="验证时的价格")

    args = parser.parse_args()

    tracker = get_tracker()

    if args.stats:
        tracker.print_stats()
    elif args.unverified:
        unverified = tracker.get_unverified()
        print(f"\n待验证推荐 ({len(unverified)}条):")
        for r in unverified:
            print(
                f"  {r['stock_name']}({r['stock_code']}): {r['decision']} @ {r['price']}"
            )
    elif args.verify and args.price:
        tracker.verify_recommendation(args.verify, args.price)
    else:
        parser.print_help()
