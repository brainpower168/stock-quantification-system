#!/usr/bin/env python3
"""
2560战法检测器
==============
华尔街交易冠军安德烈·布殊的战法
1987年4个月创造4537.8%收益记录

核心逻辑：
- 25日均线必须向上
- 5日均量线必须在60日均量线之上
- 股价回踩25日均线时缩量买入

三种信号：
1. 冲量：5均量刚上穿60均量 → 短线机会，形态未稳
2. 做量：5均量曾蹭过60均量但没死叉 → 波段机会，形态已成
3. 缩量：5均量长期在60均量之上，突然缩出地量 → 牛股黑马

使用方法：
    python strategy_2560.py --stock 002460
    python strategy_2560.py --screen
    python strategy_2560.py --watch
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


class Strategy2560:
    """2560战法检测器"""

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

    def get_stock_data(self, stock_code: str, days: int = 100) -> pd.DataFrame:
        """获取股票历史数据"""
        import urllib.request

        url = "https://openapi.iwencai.com/v1/query2data"
        api_key = os.environ.get("IWENCAI_API_KEY", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 查询历史行情
        query = f"{stock_code} 近{days}日收盘价 成交量 5日均线 25日均线"

        payload = {"query": query, "page": "1", "limit": str(days), "is_cache": "0"}

        try:
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url, data=data, headers=headers, method="POST"
            )
            response = urllib.request.urlopen(request, timeout=30)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("status_code") != 0:
                return pd.DataFrame()

            datas = result.get("datas", [])
            if not datas:
                return pd.DataFrame()

            # 解析数据
            records = []
            for item in datas:
                record = {
                    "date": item.get("日期", ""),
                    "close": 0,
                    "volume": 0,
                    "ma5": 0,
                    "ma25": 0,
                }
                for key, value in item.items():
                    if "收盘价" in key:
                        record["close"] = value
                    elif "成交量" in key:
                        record["volume"] = value
                    elif "5日均线" in key or "5日线" in key:
                        record["ma5"] = value
                    elif "25日均线" in key or "25日线" in key:
                        record["ma25"] = value
                records.append(record)

            df = pd.DataFrame(records)
            df = df.sort_values("date").reset_index(drop=True)

            # 计算均量线
            df["vol_ma5"] = df["volume"].rolling(5).mean()
            df["vol_ma60"] = df["volume"].rolling(60).mean()

            return df

        except Exception as e:
            print(f"获取数据失败: {e}")
            return pd.DataFrame()

    def detect_signal(self, df: pd.DataFrame) -> Dict:
        """
        检测2560战法信号

        返回：
            signal_type: 信号类型（冲量/做量/缩量/无信号）
            signal_strength: 信号强度（1-5）
            action: 操作建议
            details: 详细信息
        """
        if len(df) < 60:
            return {
                "signal_type": "数据不足",
                "signal_strength": 0,
                "action": "观望",
                "details": "需要至少60天数据",
            }

        # 最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = latest["close"]
        ma5 = latest["ma5"]
        ma25 = latest["ma25"]
        volume = latest["volume"]
        vol_ma5 = latest["vol_ma5"]
        vol_ma60 = latest["vol_ma60"]

        prev_close = prev["close"]
        prev_ma25 = prev["ma25"]
        prev_vol_ma5 = prev["vol_ma5"]
        prev_vol_ma60 = prev["vol_ma60"]

        # 计算关键指标
        ma25_trend = (ma25 - prev_ma25) / prev_ma25 * 100 if prev_ma25 > 0 else 0
        price_vs_ma25 = (close - ma25) / ma25 * 100 if ma25 > 0 else 0
        vol_ma5_vs_ma60 = vol_ma5 / vol_ma60 if vol_ma60 > 0 else 0

        # 检查两条铁律
        rule1_pass = ma25_trend >= 0  # 25日均线向上或走平
        rule2_pass = vol_ma5 >= vol_ma60  # 5均量在60均量之上

        # 判断信号类型
        signal_type = "无信号"
        signal_strength = 0
        action = "观望"
        details = []

        # 铁律检查
        if not rule1_pass:
            details.append("❌ 25日均线向下，不符合条件")
        else:
            details.append("✅ 25日均线向上或走平")

        if not rule2_pass:
            details.append("❌ 5均量在60均量之下，诱多信号")
            return {
                "signal_type": "诱多",
                "signal_strength": 0,
                "action": "坚决放弃",
                "details": details,
                "rule1_pass": rule1_pass,
                "rule2_pass": rule2_pass,
            }
        else:
            details.append("✅ 5均量在60均量之上")

        # 检测三种信号

        # 1. 冲量信号：5均量刚上穿60均量
        if prev_vol_ma5 < prev_vol_ma60 and vol_ma5 >= vol_ma60:
            signal_type = "冲量"
            signal_strength = 3
            action = "短线机会，形态未稳"
            details.append("📊 5均量刚上穿60均量（冲量信号）")

        # 2. 做量信号：5均量曾蹭过60均量但没死叉
        elif self._check_zuo_liang(df):
            signal_type = "做量"
            signal_strength = 4
            action = "波段机会，形态已成"
            details.append("📊 5均量蹭过60均量未死叉（做量信号）")

        # 3. 缩量信号：5均量长期在60均量之上，突然缩出地量
        elif self._check_suo_liang(df):
            signal_type = "缩量"
            signal_strength = 5
            action = "牛股黑马机会"
            details.append("📊 缩出地量（缩量信号）")

        # 检查回踩情况
        if abs(price_vs_ma25) < 3:  # 股价在25日均线附近
            details.append(f"📍 股价在25日均线附近（偏离{price_vs_ma25:.2f}%）")

            # 检查是否缩量
            recent_vol = df["volume"].iloc[-5:].mean()
            avg_vol = df["volume"].iloc[-20:].mean()
            if recent_vol < avg_vol * 0.7:
                details.append("📉 近5日成交量萎缩")
                signal_strength = min(5, signal_strength + 1)

            # 检查止跌信号
            if self._check_stop_fall(df):
                details.append("✨ 出现止跌小星线")
                signal_strength = min(5, signal_strength + 1)

        elif price_vs_ma25 < -3:
            details.append(f"⚠️ 股价跌破25日均线{abs(price_vs_ma25):.2f}%")
            signal_strength = max(0, signal_strength - 1)

        elif price_vs_ma25 > 5:
            details.append(f"⚠️ 股价远离25日均线{price_vs_ma25:.2f}%，等待回踩")
            signal_strength = max(0, signal_strength - 1)

        return {
            "signal_type": signal_type,
            "signal_strength": signal_strength,
            "action": action,
            "details": details,
            "rule1_pass": rule1_pass,
            "rule2_pass": rule2_pass,
            "ma25_trend": round(ma25_trend, 2),
            "price_vs_ma25": round(price_vs_ma25, 2),
            "vol_ma5_vs_ma60": round(vol_ma5_vs_ma60, 2),
        }

    def _check_zuo_liang(self, df: pd.DataFrame) -> bool:
        """检查做量信号：5均量曾蹭过60均量但没死叉"""
        if len(df) < 10:
            return False

        recent = df.iloc[-10:]
        vol_ma5 = recent["vol_ma5"].values
        vol_ma60 = recent["vol_ma60"].values

        # 检查是否有蹭过但没死叉
        for i in range(len(vol_ma5) - 1):
            # 蹭过：5均量接近60均量（差距小于5%）
            if abs(vol_ma5[i] - vol_ma60[i]) / vol_ma60[i] < 0.05:
                # 没死叉：之后5均量又向上
                if vol_ma5[i + 1] > vol_ma5[i]:
                    return True

        return False

    def _check_suo_liang(self, df: pd.DataFrame) -> bool:
        """检查缩量信号：5均量长期在60均量之上，突然缩出地量"""
        if len(df) < 20:
            return False

        recent = df.iloc[-20:]
        vol_ma5 = recent["vol_ma5"].values
        vol_ma60 = recent["vol_ma60"].values
        volume = recent["volume"].values

        # 5均量长期在60均量之上
        if not all(vol_ma5[-10:] >= vol_ma60[-10:] * 0.95):
            return False

        # 突然缩出地量
        latest_vol = volume[-1]
        avg_vol = volume[-20:-1].mean()
        min_vol = volume[-20:-1].min()

        # 当日成交量是近20日最低或接近最低
        if latest_vol <= min_vol * 1.1:
            return True

        return False

    def _check_stop_fall(self, df: pd.DataFrame) -> bool:
        """检查止跌信号：小星线"""
        if len(df) < 3:
            return False

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 小星线：实体小，波动小
        body = abs(latest["close"] - prev["close"]) / prev["close"] * 100
        high_low = (
            (df.iloc[-3:]["close"].max() - df.iloc[-3:]["close"].min())
            / df.iloc[-3:]["close"].min()
            * 100
        )

        # 实体小于1%，近3日波动小于3%
        if body < 1 and high_low < 3:
            return True

        return False

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析单只股票"""
        df = self.get_stock_data(stock_code)

        if df.empty:
            return {"code": stock_code, "error": "获取数据失败"}

        signal = self.detect_signal(df)

        latest = df.iloc[-1]

        return {
            "code": stock_code,
            "close": latest["close"],
            "ma5": latest["ma5"],
            "ma25": latest["ma25"],
            "volume": latest["volume"],
            "vol_ma5": latest["vol_ma5"],
            "vol_ma60": latest["vol_ma60"],
            "signal": signal,
        }

    def screen_stocks(self) -> List[Dict]:
        """筛选符合2560战法的股票"""
        results = []

        print(f"\n{'=' * 70}")
        print(f"2560战法选股")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        for stock_code in self.watchlist:
            print(f"分析 {stock_code}...", end=" ")
            result = self.analyze_stock(stock_code)

            if "error" in result:
                print(f"失败: {result['error']}")
                continue

            signal = result["signal"]
            print(f"完成 - {signal['signal_type']} [{signal['action']}]")

            # 只保留有信号的股票
            if signal["signal_strength"] >= 3:
                results.append(result)

        # 按信号强度排序
        results.sort(key=lambda x: x["signal"]["signal_strength"], reverse=True)

        return results

    def generate_report(self, results: List[Dict]) -> str:
        """生成报告"""
        report = []
        report.append(f"\n{'=' * 70}")
        report.append(f"2560战法选股报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"{'=' * 70}\n")

        if not results:
            report.append("无符合条件的股票")
            return "\n".join(report)

        # 按信号类型分组
        signals = {
            "缩量": [],
            "做量": [],
            "冲量": [],
        }

        for r in results:
            sig_type = r["signal"]["signal_type"]
            if sig_type in signals:
                signals[sig_type].append(r)

        # 缩量信号（牛股黑马）
        if signals["缩量"]:
            report.append(f"\n【缩量信号 - 牛股黑马机会】")
            report.append("-" * 70)
            for r in signals["缩量"]:
                report.append(f"  {r['code']}")
                report.append(
                    f"    收盘价: {r['close']:.2f} | 25日均线: {r['ma25']:.2f}"
                )
                report.append(f"    偏离度: {r['signal']['price_vs_ma25']:+.2f}%")
                report.append(f"    量比: {r['signal']['vol_ma5_vs_ma60']:.2f}")
                for detail in r["signal"]["details"]:
                    report.append(f"    {detail}")
                report.append("")

        # 做量信号（波段机会）
        if signals["做量"]:
            report.append(f"\n【做量信号 - 波段机会】")
            report.append("-" * 70)
            for r in signals["做量"]:
                report.append(f"  {r['code']}")
                report.append(
                    f"    收盘价: {r['close']:.2f} | 25日均线: {r['ma25']:.2f}"
                )
                report.append(f"    偏离度: {r['signal']['price_vs_ma25']:+.2f}%")
                for detail in r["signal"]["details"]:
                    report.append(f"    {detail}")
                report.append("")

        # 冲量信号（短线机会）
        if signals["冲量"]:
            report.append(f"\n【冲量信号 - 短线机会】")
            report.append("-" * 70)
            for r in signals["冲量"]:
                report.append(f"  {r['code']}")
                report.append(
                    f"    收盘价: {r['close']:.2f} | 25日均线: {r['ma25']:.2f}"
                )
                report.append(f"    偏离度: {r['signal']['price_vs_ma25']:+.2f}%")
                for detail in r["signal"]["details"]:
                    report.append(f"    {detail}")
                report.append("")

        # 2560战法说明
        report.append(f"\n【2560战法说明】")
        report.append("-" * 70)
        report.append("两条铁律：")
        report.append("  1. 25日均线必须向上（起码走平）")
        report.append("  2. 5日均量线必须在60日均量线之上")
        report.append("")
        report.append("三种信号：")
        report.append("  冲量：5均量刚上穿60均量 → 短线机会，形态未稳")
        report.append("  做量：5均量蹭过60均量未死叉 → 波段机会，形态已成")
        report.append("  缩量：5均量长期在60均量之上，突然缩出地量 → 牛股黑马")
        report.append("")
        report.append("买入条件：")
        report.append("  - 股价回踩25日均线")
        report.append("  - 成交量缩量（最好缩到60日均量线下）")
        report.append("  - 出现止跌小星线")
        report.append("  - 止损设在25日线下方3%")
        report.append("")
        report.append("核心原则：")
        report.append("  每次把握5%-10%的机会，一次5%，14次翻倍")
        report.append("  每周5%，一年翻10倍，复利是第九大奇迹")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="2560战法检测器")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--screen", action="store_true", help="筛选股票")
    parser.add_argument("--watch", action="store_true", help="监控自选股")

    args = parser.parse_args()

    detector = Strategy2560()

    if args.stock:
        # 分析单只股票
        result = detector.analyze_stock(args.stock)
        if "error" in result:
            print(f"分析失败: {result['error']}")
            return

        print(f"\n{'=' * 70}")
        print(f"{args.stock} 2560战法分析")
        print(f"{'=' * 70}\n")

        print(f"收盘价: {result['close']:.2f}")
        print(f"5日均线: {result['ma5']:.2f}")
        print(f"25日均线: {result['ma25']:.2f}")
        print(f"成交量: {result['volume']:.0f}")
        print(f"5日均量: {result['vol_ma5']:.0f}")
        print(f"60日均量: {result['vol_ma60']:.0f}")

        signal = result["signal"]
        print(f"\n信号类型: {signal['signal_type']}")
        print(f"信号强度: {'⭐' * signal['signal_strength']}")
        print(f"操作建议: {signal['action']}")
        print(f"\n详细信息:")
        for detail in signal["details"]:
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
            f"strategy_2560_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
