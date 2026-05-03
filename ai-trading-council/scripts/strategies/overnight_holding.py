#!/usr/bin/env python3
"""
一夜持股法检测器
================
杨永兴战法：16个月从100万做到1亿

核心逻辑：尾盘买、次日卖，把T+1做成准T+0效果

六步选股法：
1. 涨幅3%-5%
2. 量比>1（最佳1-2.5）
3. 换手率5%-10%
4. 流通市值50-200亿
5. 20天内有涨停
6. 分时图全天在均价线上

买卖纪律：
- 买入：下午2:50-3:00
- 卖出：次日9:30-10:00
- 三不原则：不恋战、不补仓、不隔夜

使用方法：
    python overnight_holding.py --stock 002460
    python overnight_holding.py --screen
    python overnight_holding.py --watch
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OvernightHolding:
    """一夜持股法检测器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 用户自选股
        self.watchlist = [
            "601138",  # 工业富联
            "002475",  # 立讯精密
            "002460",  # 赣锋锂业
            "002281",  # 光迅科技
            "002463",  # 沪电股份
            "300750",  # 宁德时代
            "300476",  # 胜宏科技
            "000988",  # 华工科技
        ]

    def get_stock_data(self, stock_code: str) -> Dict:
        """获取股票实时数据"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 查询实时行情
        query = f"{stock_code} 今日涨幅 量比 换手率 流通市值 近20日涨停次数 最新价 今开 最高 最低 成交量"

        payload = {"query": query, "page": "1", "limit": "10", "is_cache": "0"}

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") != 0:
                return {"code": stock_code, "error": result.get("status_msg")}

            datas = result.get("datas", [])
            if not datas:
                return {"code": stock_code, "error": "无数据"}

            # 解析数据
            item = datas[0]
            data = {
                "code": stock_code,
                "name": item.get("股票简称", ""),
                "price": 0,
                "open": 0,
                "high": 0,
                "low": 0,
                "volume": 0,
                "change_pct": 0,
                "volume_ratio": 0,
                "turnover_rate": 0,
                "float_mv": 0,
                "limit_up_count": 0,
            }

            for key, value in item.items():
                if "最新价" in key:
                    data["price"] = value
                elif "今开" in key:
                    data["open"] = value
                elif "最高" in key:
                    data["high"] = value
                elif "最低" in key:
                    data["low"] = value
                elif "成交量" in key:
                    data["volume"] = value
                elif "涨幅" in key:
                    data["change_pct"] = value
                elif "量比" in key:
                    data["volume_ratio"] = value
                elif "换手率" in key:
                    data["turnover_rate"] = value
                elif "流通市值" in key or "流通值" in key:
                    data["float_mv"] = value
                elif "涨停" in key:
                    data["limit_up_count"] = value

            return data

        except Exception as e:
            return {"code": stock_code, "error": str(e)}

    def check_six_steps(self, data: Dict) -> Dict:
        """
        六步选股法检查

        返回：
            passed: 是否通过
            score: 得分（0-6）
            details: 详细检查结果
        """
        details = []
        score = 0

        # 第一步：涨幅3%-5%
        change_pct = data.get("change_pct", 0)
        if 3 <= change_pct <= 5:
            details.append(f"✅ 涨幅{change_pct:.2f}%，符合3%-5%标准")
            score += 1
        elif change_pct < 3:
            details.append(f"❌ 涨幅{change_pct:.2f}%，低于3%，冲劲不足")
        else:
            details.append(f"❌ 涨幅{change_pct:.2f}%，超过5%，可能强弩之末")

        # 第二步：量比>1
        volume_ratio = data.get("volume_ratio", 0)
        if volume_ratio >= 1:
            if 1 <= volume_ratio <= 2.5:
                details.append(f"✅ 量比{volume_ratio:.2f}，最佳区间")
                score += 1
            else:
                details.append(f"⚠️ 量比{volume_ratio:.2f}，偏高但可接受")
                score += 0.5
        else:
            details.append(f"❌ 量比{volume_ratio:.2f}，低于1，无资金关注")

        # 第三步：换手率5%-10%
        turnover_rate = data.get("turnover_rate", 0)
        if 5 <= turnover_rate <= 10:
            details.append(f"✅ 换手率{turnover_rate:.2f}%，活跃度适中")
            score += 1
        elif turnover_rate < 5:
            details.append(f"❌ 换手率{turnover_rate:.2f}%，太低无人气")
        else:
            details.append(f"⚠️ 换手率{turnover_rate:.2f}%，太高可能主力出货")

        # 第四步：流通市值50-200亿
        float_mv = data.get("float_mv", 0)
        if 50 <= float_mv <= 200:
            details.append(f"✅ 流通市值{float_mv:.0f}亿，中盘股弹性好")
            score += 1
        elif float_mv < 50:
            details.append(f"⚠️ 流通市值{float_mv:.0f}亿，小盘股波动大")
            score += 0.5
        else:
            details.append(f"❌ 流通市值{float_mv:.0f}亿，大盘股难拉升")

        # 第五步：20天内有涨停
        limit_up_count = data.get("limit_up_count", 0)
        if limit_up_count > 0:
            details.append(f"✅ 近20日{limit_up_count}次涨停，有涨停基因")
            score += 1
        else:
            details.append(f"❌ 近20日无涨停，股性不活跃")

        # 第六步：分时图在均价线上（简化判断：当前价>开盘价）
        price = data.get("price", 0)
        open_price = data.get("open", 0)
        if price > open_price and open_price > 0:
            details.append(f"✅ 当前价{price:.2f}>开盘价{open_price:.2f}，走势稳健")
            score += 1
        else:
            details.append(f"❌ 当前价{price:.2f}<=开盘价{open_price:.2f}，走势偏弱")

        passed = score >= 4  # 至少4项通过

        return {
            "passed": passed,
            "score": score,
            "details": details,
        }

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        data = self.get_stock_data(stock_code)

        if "error" in data:
            return {"code": stock_code, "error": data["error"]}

        # 六步检查
        check_result = self.check_six_steps(data)

        return {
            "code": stock_code,
            "name": data["name"],
            "price": data["price"],
            "change_pct": data["change_pct"],
            "volume_ratio": data["volume_ratio"],
            "turnover_rate": data["turnover_rate"],
            "float_mv": data["float_mv"],
            "limit_up_count": data.get("limit_up_count", 0),
            "check": check_result,
        }

    def screen_stocks(self) -> List[Dict]:
        """筛选符合一夜持股法的股票"""
        results = []

        print(f"\n{'=' * 70}")
        print(f"一夜持股法选股")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        for stock_code in self.watchlist:
            print(f"分析 {stock_code}...", end=" ")
            result = self.analyze_stock(stock_code)

            if "error" in result:
                print(f"失败: {result['error']}")
                continue

            check = result["check"]
            print(
                f"完成 - 得分{check['score']:.1f}/6 {'✅通过' if check['passed'] else '❌不通过'}"
            )

            if check["passed"]:
                results.append(result)

        # 按得分排序
        results.sort(key=lambda x: x["check"]["score"], reverse=True)

        return results

    def generate_report(self, results: List[Dict]) -> str:
        """生成报告"""
        report = []
        report.append(f"\n{'=' * 70}")
        report.append(f"一夜持股法选股报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'=' * 70}\n")

        if not results:
            report.append("无符合条件的股票")
            return "\n".join(report)

        report.append(f"【符合条件股票】共{len(results)}只")
        report.append("-" * 70)

        for r in results:
            report.append(f"\n{r['name']} ({r['code']})")
            report.append(f"  价格: {r['price']:.2f} | 涨幅: {r['change_pct']:+.2f}%")
            report.append(
                f"  量比: {r['volume_ratio']:.2f} | 换手率: {r['turnover_rate']:.2f}%"
            )
            report.append(
                f"  流通市值: {r['float_mv']:.0f}亿 | 近20日涨停: {r['limit_up_count']}次"
            )
            report.append(f"  得分: {r['check']['score']:.1f}/6")
            report.append(f"  检查详情:")
            for detail in r["check"]["details"]:
                report.append(f"    {detail}")

        # 操作纪律提醒
        report.append(f"\n{'=' * 70}")
        report.append(f"【操作纪律】")
        report.append("-" * 70)
        report.append("买入时间: 下午2:50-3:00")
        report.append("卖出时间: 次日9:30-10:00")
        report.append("")
        report.append("三不原则:")
        report.append("  1. 不恋战 - 到点就卖，不幻想反弹")
        report.append("  2. 不补仓 - 亏损不加仓，止损走人")
        report.append("  3. 不隔夜 - 只持一夜，不拖到第三天")
        report.append("")
        report.append("仓位控制:")
        report.append("  单股仓位: 10%-20%")
        report.append("  每月交易: 15-20次")
        report.append("")
        report.append("目标收益: 每笔1%-3%，不贪多")
        report.append("核心逻辑: 高胜率+小盈利+快复利")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="一夜持股法检测器")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--screen", action="store_true", help="筛选股票")
    parser.add_argument("--watch", action="store_true", help="监控自选股")

    args = parser.parse_args()

    detector = OvernightHolding()

    if args.stock:
        # 分析单只股票
        result = detector.analyze_stock(args.stock)
        if "error" in result:
            print(f"分析失败: {result['error']}")
            return

        print(f"\n{'=' * 70}")
        print(f"{result['name']} ({result['code']}) 一夜持股法分析")
        print(f"{'=' * 70}\n")

        print(f"价格: {result['price']:.2f}")
        print(f"涨幅: {result['change_pct']:+.2f}%")
        print(f"量比: {result['volume_ratio']:.2f}")
        print(f"换手率: {result['turnover_rate']:.2f}%")
        print(f"流通市值: {result['float_mv']:.0f}亿")
        print(f"近20日涨停: {result['limit_up_count']}次")

        check = result["check"]
        print(
            f"\n六步检查: 得分{check['score']:.1f}/6 {'✅通过' if check['passed'] else '❌不通过'}"
        )
        print(f"\n检查详情:")
        for detail in check["details"]:
            print(f"  {detail}")

    else:
        # 筛选股票
        results = detector.screen_stocks()
        report = detector.generate_report(results)
        print(report)

        # 保存报告
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            f"overnight_holding_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
