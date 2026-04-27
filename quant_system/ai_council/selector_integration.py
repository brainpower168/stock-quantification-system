#!/usr/bin/env python3
"""
选股 + AI Council 集成脚本
将妙想选股结果送入 AI Trading Council 进行分析
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from council_engine import TradingCouncil
    from recommendation_tracker import RecommendationTracker
except ImportError:
    print("Error: council_engine.py not found")
    sys.exit(1)


class StockDataFetcher:
    """股票数据获取器 - 支持多数据源"""

    def __init__(self):
        self.mx_apikey = os.environ.get("MX_APIKEY", "")
        self.iwencai_apikey = os.environ.get("IWENCAI_API_KEY", "")
        self.data_source = "unknown"

    def _fetch_from_mx(self, stock_code: str) -> Optional[Dict]:
        """从妙想 API 获取数据"""
        if not self.mx_apikey:
            return None

        try:
            import requests

            url = "https://mkapi2.dfcfs.com/api/stock/quote"
            headers = {"Authorization": f"Bearer {self.mx_apikey}"}
            params = {"code": stock_code}
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("data"):
                    quote = result["data"]
                    # 检查数据是否有效（价格不为0）
                    if quote.get("price", 0) > 0:
                        self.data_source = "妙想"
                        return {
                            "name": quote.get("name", stock_code),
                            "price": quote.get("price", 0),
                            "change_pct": quote.get("change_pct", 0),
                            "volume": quote.get("volume", 0),
                        }
        except Exception as e:
            print(f"  [妙想] 获取 {stock_code} 失败: {e}")

        return None

    def _fetch_from_iwencai(self, stock_code: str) -> Optional[Dict]:
        """从问财 API 获取数据"""
        if not self.iwencai_apikey:
            return None

        try:
            import urllib.request
            import json

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_apikey}",
                "Content-Type": "application/json",
            }

            # 转换股票代码格式 (601138 -> 601138.SH, 002475 -> 002475.SZ)
            if stock_code.startswith("6"):
                full_code = f"{stock_code}.SH"
            else:
                full_code = f"{stock_code}.SZ"

            payload = {
                "query": f"{full_code}最新价、涨跌幅、成交量、成交额、换手率",
                "page": "1",
                "limit": "1",
                "is_cache": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            datas = result.get("datas", [])
            if datas:
                item = datas[0]
                # 解析问财返回的数据（支持多种字段名格式）
                # 优先使用 "最新价"，否则查找 "收盘价[日期]" 格式的字段
                price = self._parse_value(item.get("最新价", 0))
                if price == 0:
                    # 查找 "收盘价[日期]" 格式的字段
                    for key in item.keys():
                        if key.startswith("收盘价"):
                            price = self._parse_value(item[key])
                            break

                change_pct = self._parse_value(item.get("最新涨跌幅", 0))
                if change_pct == 0:
                    # 查找 "涨跌幅[日期]" 格式的字段
                    for key in item.keys():
                        if key.startswith("涨跌幅"):
                            change_pct = self._parse_value(item[key])
                            break

                if price > 0:
                    self.data_source = "问财"
                    return {
                        "name": item.get("股票简称", stock_code),
                        "price": price,
                        "change_pct": change_pct,
                        "volume": self._parse_value(item.get("成交量", 0)),
                        "amount": self._parse_value(item.get("成交额", 0)),
                        "turnover_rate": self._parse_value(item.get("换手率", 0)),
                    }
        except Exception as e:
            print(f"  [问财] 获取 {stock_code} 失败: {e}")

        return None

    def _parse_value(self, value) -> float:
        """解析数值（处理字符串格式如 '1.5亿', '5000万'）"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip().replace("%", "").replace(",", "")
            try:
                if "亿" in value:
                    return float(value.replace("亿", "")) * 100000000
                elif "万" in value:
                    return float(value.replace("万", "")) * 10000
                else:
                    return float(value)
            except ValueError:
                return 0
        return 0

    def fetch_stock_data(self, stock_code: str) -> Dict:
        """获取股票详细数据 - 多数据源自动切换"""
        # 基础数据结构
        data = {
            "code": stock_code,
            "name": stock_code,
            "price": 0,
            "change_pct": 0,
            "volume": 0,
            "amount": 0,
            "turnover_rate": 0,
            "capital_flow": 0,  # 主力资金流向
            "pe": 0,
            "pb": 0,
            "roe": 0,
            "profit_growth": 0,
            "ma5": 0,
            "ma10": 0,
            "ma20": 0,
            "rsi": 50,
            "kdj": 50,
            "macd": 0,
            "change_5d": 0,  # 近5日涨跌幅
            "financial": {},
            "data_source": "unknown",
        }

        # 优先使用问财 API（获取更全面的数据）
        iwencai_data = self._fetch_from_iwencai(stock_code)
        if iwencai_data:
            data.update(iwencai_data)
            data["data_source"] = "问财"
            # 获取资金流向
            capital_flow = self._fetch_capital_flow(stock_code)
            if capital_flow:
                data["capital_flow"] = capital_flow
            # 获取财务指标
            financial = self._fetch_financial(stock_code)
            if financial:
                data.update(financial)
            # 获取技术指标
            technical = self._fetch_technical(stock_code)
            if technical:
                data.update(technical)
            return data

        # 问财失败，切换到妙想
        mx_data = self._fetch_from_mx(stock_code)
        if mx_data:
            data.update(mx_data)
            data["data_source"] = "妙想"
            return data

        # 两个数据源都失败
        print(f"  Warning: 所有数据源都无法获取 {stock_code} 的数据")
        data["data_source"] = "failed"

        return data

    def _fetch_capital_flow(self, stock_code: str) -> Optional[float]:
        """获取主力资金流向"""
        if not self.iwencai_apikey:
            return None

        try:
            import urllib.request
            import json

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_apikey}",
                "Content-Type": "application/json",
            }

            if stock_code.startswith("6"):
                full_code = f"{stock_code}.SH"
            else:
                full_code = f"{stock_code}.SZ"

            payload = {
                "query": f"{full_code}主力资金流向",
                "page": "1",
                "limit": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            datas = result.get("datas", [])
            if datas:
                item = datas[0]
                # 查找主力资金流向字段
                for key in item:
                    if "主力资金流向" in key or "主力净流入" in key:
                        value = item[key]
                        if isinstance(value, (int, float)):
                            return value / 1e8  # 转换为亿
        except Exception as e:
            pass

        return None

    def _fetch_financial(self, stock_code: str) -> Optional[Dict]:
        """获取财务指标"""
        if not self.iwencai_apikey:
            return None

        try:
            import urllib.request
            import json

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_apikey}",
                "Content-Type": "application/json",
            }

            if stock_code.startswith("6"):
                full_code = f"{stock_code}.SH"
            else:
                full_code = f"{stock_code}.SZ"

            payload = {
                "query": f"{full_code}市盈率、市净率、ROE、净利润增长率",
                "page": "1",
                "limit": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            datas = result.get("datas", [])
            if datas:
                item = datas[0]
                financial = {}

                # 解析财务指标
                for key in item:
                    if "市盈率" in key:
                        financial["pe"] = self._parse_value(item[key])
                    elif "市净率" in key:
                        financial["pb"] = self._parse_value(item[key])
                    elif "ROE" in key or "净资产收益率" in key:
                        financial["roe"] = self._parse_value(item[key])
                    elif "净利润增长" in key:
                        financial["profit_growth"] = self._parse_value(item[key])

                return financial
        except Exception as e:
            pass

        return None

    def _fetch_technical(self, stock_code: str) -> Optional[Dict]:
        """获取技术指标（KDJ、RSI、MACD、近5日涨跌幅）"""
        if not self.iwencai_apikey:
            return None

        try:
            import urllib.request
            import json

            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Authorization": f"Bearer {self.iwencai_apikey}",
                "Content-Type": "application/json",
            }

            if stock_code.startswith("6"):
                full_code = f"{stock_code}.SH"
            else:
                full_code = f"{stock_code}.SZ"

            payload = {
                "query": f"{full_code} KDJ RSI MACD 近5日涨跌幅",
                "page": "1",
                "limit": "1",
            }

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            datas = result.get("datas", [])
            if datas:
                item = datas[0]
                technical = {}

                # 解析技术指标
                for key in item:
                    key_lower = key.lower()
                    if "kdj" in key_lower:
                        technical["kdj"] = self._parse_value(item[key])
                    elif "rsi" in key_lower:
                        technical["rsi"] = self._parse_value(item[key])
                    elif "macd" in key_lower:
                        technical["macd"] = self._parse_value(item[key])
                    elif "涨跌幅" in key and "5日" in key:
                        technical["change_5d"] = self._parse_value(item[key])

                return technical
        except Exception as e:
            pass

        return None


class SelectorCouncilIntegration:
    """选股 + AI Council 集成"""

    def __init__(self):
        self.council = TradingCouncil()
        self.fetcher = StockDataFetcher()
        self.tracker = RecommendationTracker()
        self.output_dir = Path(__file__).parent.parent / "data"
        self.output_dir.mkdir(exist_ok=True)

    def analyze_selected_stocks(
        self,
        stock_list: List[str],
        stock_names: Optional[Dict[str, str]] = None,
        parallel: bool = True,
    ) -> List[Dict]:
        """分析选股结果"""
        results = []

        print(f"\n{'=' * 60}")
        print(f"AI Trading Council 分析")
        print(f"股票数量: {len(stock_list)}")
        print(f"{'=' * 60}\n")

        for i, stock_code in enumerate(stock_list, 1):
            print(f"[{i}/{len(stock_list)}] 分析 {stock_code}...")

            # 获取股票数据
            stock_data = self.fetcher.fetch_stock_data(stock_code)
            if stock_names and stock_code in stock_names:
                stock_data["name"] = stock_names[stock_code]

            # 运行 AI Council 分析
            result = self.council.run_council_analysis(stock_code, stock_data)
            results.append(result)

            # 记录推荐（用于后续验证）
            if result["consensus"] in ["STRONG_BUY", "BUY", "SELL", "STRONG_SELL"]:
                self.tracker.record_recommendation(
                    stock_code=stock_code,
                    stock_name=stock_data.get("name", stock_code),
                    decision=result["consensus"],
                    confidence=result["confidence"],
                    price=stock_data.get("price", 0),
                    reasons=result.get("key_points", []),
                    models=result.get("council_votes", {}),
                )

            # 打印简要结果
            print(f"  决策: {result['consensus']} (置信度: {result['confidence']:.2f})")
            print(f"  资金流向: {stock_data.get('capital_flow', 0):.2f}亿")
            print()

        return results

    def generate_report(self, results: List[Dict], query: str = "") -> str:
        """生成分析报告"""
        report_lines = [
            f"# AI Trading Council 分析报告",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**选股条件**: {query if query else '自定义股票列表'}",
            f"**分析股票数**: {len(results)}",
            f"",
            f"---",
            f"",
            f"## 决策汇总",
            f"",
        ]

        # 按决策分组
        by_decision = {
            "STRONG_BUY": [],
            "BUY": [],
            "HOLD": [],
            "SELL": [],
            "STRONG_SELL": [],
        }
        for r in results:
            decision = r.get("consensus", "HOLD")
            if decision in by_decision:
                by_decision[decision].append(r)

        # 决策统计
        report_lines.append("| 决策 | 数量 | 股票 |")
        report_lines.append("|------|------|------|")
        for decision in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            stocks = by_decision[decision]
            if stocks:
                stock_str = ", ".join(
                    [
                        f"{s['stock_code']}({s.get('stock_name', s['stock_code'])})"
                        for s in stocks[:5]
                    ]
                )
                if len(stocks) > 5:
                    stock_str += f" 等{len(stocks)}只"
                report_lines.append(f"| {decision} | {len(stocks)} | {stock_str} |")

        report_lines.extend(
            [
                "",
                "---",
                "",
                "## 详细分析",
                "",
            ]
        )

        # 详细分析
        for r in results:
            data_source = r.get("data_source", "unknown")
            report_lines.extend(
                [
                    f"### {r['stock_code']} ({r.get('stock_name', r['stock_code'])})",
                    "",
                    f"- **决策**: {r['consensus']}",
                    f"- **置信度**: {r['confidence']:.2f}",
                    f"- **数据来源**: {data_source}",
                    "",
                    "**分析要点**:",
                    "",
                ]
            )
            for point in r.get("key_points", []):
                report_lines.append(f"- {point}")

            if r.get("risk_warnings"):
                report_lines.extend(
                    [
                        "",
                        "**风险警告**:",
                        "",
                    ]
                )
                for warning in r["risk_warnings"]:
                    report_lines.append(f"- ⚠️ {warning}")

            report_lines.append("")

        # 保存报告
        report_content = "\n".join(report_lines)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"council_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"\n报告已保存: {report_file}")

        return report_content

    def save_results(self, results: List[Dict]) -> str:
        """保存结果 JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"council_results_{timestamp}.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return str(json_file)


def main():
    parser = argparse.ArgumentParser(description="选股 + AI Council 集成分析")
    parser.add_argument(
        "--stocks", type=str, help="股票代码列表，逗号分隔 (如: 600519,000001,300750)"
    )
    parser.add_argument("--file", type=str, help="股票列表文件 (CSV/JSON)")
    parser.add_argument("--query", type=str, default="", help="选股条件描述")
    parser.add_argument("--top", type=int, default=10, help="只分析前 N 只股票")
    parser.add_argument("--report", action="store_true", default=True, help="生成报告")

    args = parser.parse_args()

    # 获取股票列表
    stock_list = []
    stock_names = {}

    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(",")]
    elif args.file:
        file_path = Path(args.file)
        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            code = (
                                item.get("code")
                                or item.get("股票代码")
                                or item.get("stock_code")
                            )
                            name = (
                                item.get("name")
                                or item.get("股票名称")
                                or item.get("stock_name")
                            )
                            if code:
                                stock_list.append(code)
                                if name:
                                    stock_names[code] = name
                        elif isinstance(item, str):
                            stock_list.append(item)
        elif file_path.suffix == ".csv":
            import csv

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = (
                        row.get("code") or row.get("股票代码") or row.get("stock_code")
                    )
                    name = (
                        row.get("name") or row.get("股票名称") or row.get("stock_name")
                    )
                    if code:
                        stock_list.append(code)
                        if name:
                            stock_names[code] = name
    else:
        # 默认使用用户自选股
        stock_list = [
            "601138",
            "002475",
            "002460",
            "002281",
            "002463",
            "300750",
            "300476",
            "000988",
        ]
        stock_names = {
            "601138": "工业富联",
            "002475": "立讯精密",
            "002460": "赣锋锂业",
            "002281": "光迅科技",
            "002463": "沪电股份",
            "300750": "宁德时代",
            "300476": "胜宏科技",
            "000988": "华工科技",
        }
        print("使用默认自选股列表")

    # 限制数量
    if args.top and len(stock_list) > args.top:
        stock_list = stock_list[: args.top]
        print(f"只分析前 {args.top} 只股票")

    if not stock_list:
        print("Error: 没有股票需要分析")
        sys.exit(1)

    # 运行分析
    integration = SelectorCouncilIntegration()
    results = integration.analyze_selected_stocks(stock_list, stock_names)

    # 生成报告
    if args.report:
        integration.generate_report(results, args.query)

    # 保存结果
    json_file = integration.save_results(results)

    # 打印汇总
    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)

    buy_stocks = [r for r in results if r["consensus"] in ["STRONG_BUY", "BUY"]]
    if buy_stocks:
        print("\n建议买入:")
        for r in buy_stocks:
            print(
                f"  {r['stock_code']} ({r.get('stock_name', r['stock_code'])}): {r['consensus']} (置信度: {r['confidence']:.2f})"
            )

    print(f"\n结果已保存: {json_file}")


if __name__ == "__main__":
    main()
