# -*- coding: utf-8 -*-
"""
统一数据源层 - Unified Data Source
自动切换可用数据源：妙想 → 问财 → 国信 → 腾讯 → 新浪

优先级依据 MEMORY.md：
1. 妙想(mx)：DDX、资金流向、选股（无限制，数据最完整）
2. 问财(hithink)：DDX、资金流向、选股（每日有限）
3. 国信(gs)：实时行情、财务数据、宏观（无限制）
4. 腾讯：仅用于实时价格（最后备用）
"""

import os
import time
import json
import urllib.request
import ssl
from typing import Dict, Optional, List, Any
from datetime import datetime

try:
    from .logger import get_logger

    logger = get_logger("data_sources")
except ImportError:
    import logging

    logger = logging.getLogger("data_sources")


class DataSource:
    """统一数据源 - 按优先级自动切换"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # SSL配置（部分API证书有问题，生产环境可开启验证）
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        # API Keys（从环境变量读取，必须配置）
        self.mx_apikey = os.environ.get("MX_APIKEY", "")
        self.iwencai_key = os.environ.get("IWENCAI_API_KEY", "")
        self.gs_api_key = os.environ.get("GS_API_KEY", "")

        # 检查API Key配置
        self._check_api_keys()

        # 数据源状态
        self.source_status = {
            "miaoxiang": {"ok": False, "latency": 0, "priority": 1},
            "iwencai": {"ok": False, "latency": 0, "priority": 2},
            "guosen": {"ok": False, "latency": 0, "priority": 3},
            "tencent": {"ok": False, "latency": 0, "priority": 4},
            "sina": {"ok": False, "latency": 0, "priority": 5},
        }

        # 探测可用数据源
        self._probe_sources()

    def _check_api_keys(self):
        """检查API Key配置状态"""
        missing = []
        if not self.mx_apikey:
            missing.append("MX_APIKEY（妙想，首选）")
        if not self.iwencai_key:
            missing.append("IWENCAI_API_KEY（问财，备用）")
        if not self.gs_api_key:
            missing.append("GS_API_KEY（国信，补充）")

        if missing:
            logger.warning(f"以下API Key未配置，部分功能受限：{', '.join(missing)}")
            logger.warning("请参考 .env.example 配置环境变量")

    def _probe_sources(self):
        """探测各数据源可用性"""
        logger.info("探测数据源可用性...")

        # 妙想探测
        if self.mx_apikey:
            try:
                t0 = time.time()
                url = "https://api.miaoxiang.com/v1/stock/realtime"
                headers = {"Authorization": f"Bearer {self.mx_apikey}"}
                req = urllib.request.Request(url, headers=headers)
                resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
                result = json.loads(resp.read())
                if result.get("code") == 0:
                    self.source_status["miaoxiang"]["ok"] = True
                    self.source_status["miaoxiang"]["latency"] = round(
                        (time.time() - t0) * 1000
                    )
            except Exception as e:
                logger.debug(f"妙想探测失败: {e}")

        # 问财探测
        if self.iwencai_key:
            try:
                t0 = time.time()
                url = "https://openapi.iwencai.com/v1/query2data"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.iwencai_key}",
                }
                body = json.dumps(
                    {"query": "上证指数", "token": self.iwencai_key}
                ).encode()
                req = urllib.request.Request(
                    url, data=body, headers=headers, method="POST"
                )
                resp = urllib.request.urlopen(req, context=self.ctx, timeout=8)
                result = json.loads(resp.read())
                if result.get("status_code") == 0 or result.get("code") == 0:
                    self.source_status["iwencai"]["ok"] = True
                    self.source_status["iwencai"]["latency"] = round(
                        (time.time() - t0) * 1000
                    )
            except Exception as e:
                logger.debug(f"问财探测失败: {e}")

        # 国信探测
        if self.gs_api_key:
            try:
                t0 = time.time()
                url = f"https://api.guosen.com/v1/market/quote?code=000001&key={self.gs_api_key}"
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
                result = json.loads(resp.read())
                if result.get("code") == 0:
                    self.source_status["guosen"]["ok"] = True
                    self.source_status["guosen"]["latency"] = round(
                        (time.time() - t0) * 1000
                    )
            except Exception as e:
                logger.debug(f"国信探测失败: {e}")

        # 腾讯探测（无需API Key）
        try:
            t0 = time.time()
            url = "https://qt.gtimg.cn/q=sh000001"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
            if len(resp.read()) > 100:
                self.source_status["tencent"]["ok"] = True
                self.source_status["tencent"]["latency"] = round(
                    (time.time() - t0) * 1000
                )
        except Exception as e:
            logger.debug(f"腾讯探测失败: {e}")

        # 新浪探测（无需API Key）
        try:
            t0 = time.time()
            url = "https://hq.sinajs.cn/list=sh000001"
            headers = {"Referer": "https://finance.sina.com.cn"}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
            if len(resp.read()) > 50:
                self.source_status["sina"]["ok"] = True
                self.source_status["sina"]["latency"] = round((time.time() - t0) * 1000)
        except Exception as e:
            logger.debug(f"新浪探测失败: {e}")

        # 打印结果
        self._print_source_status()

    def _print_source_status(self):
        """打印数据源状态"""
        logger.info("=" * 50)
        logger.info("数据源状态:")

        # 按优先级排序
        sorted_sources = sorted(
            self.source_status.items(), key=lambda x: x[1]["priority"]
        )

        for name, status in sorted_sources:
            ok = "✅" if status["ok"] else "❌"
            latency = f"{status['latency']}ms" if status["ok"] else "N/A"
            priority = f"P{status['priority']}"
            logger.info(f"  {ok} {name.upper():12} | {priority} | {latency}")

        # 找最优可用
        available = [(n, s) for n, s in sorted_sources if s["ok"]]
        if available:
            best = available[0][0]
            logger.info(f"  🎯 当前使用: {best.upper()}")
        else:
            logger.error("  ⚠️ 所有数据源均不可用!")

        logger.info("=" * 50)

    def get_best_source(self) -> str:
        """获取当前最优数据源"""
        available = [(n, s) for n, s in self.source_status.items() if s["ok"]]
        if available:
            available.sort(key=lambda x: x[1]["priority"])
            return available[0][0]
        return "tencent"  # 默认回退

    # ==================== 妙想API（首选） ====================

    def get_ddx_miaoxiang(self, code: str, days: int = 10) -> Dict:
        """
        获取DDX数据（妙想API）

        Args:
            code: 股票代码
            days: 天数

        Returns:
            DDX数据
        """
        if not self.source_status["miaoxiang"]["ok"]:
            return {}

        try:
            url = f"https://api.miaoxiang.com/v1/stock/ddx?code={code}&days={days}"
            headers = {"Authorization": f"Bearer {self.mx_apikey}"}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=10)
            result = json.loads(resp.read())

            if result.get("code") == 0:
                return {
                    "success": True,
                    "data": result.get("data", {}),
                    "source": "miaoxiang",
                }
        except Exception as e:
            logger.error(f"妙想获取DDX失败: {e}")

        return {"success": False}

    def get_main_flow_miaoxiang(self, code: str) -> Dict:
        """
        获取主力资金流向（妙想API）

        Args:
            code: 股票代码

        Returns:
            资金流向数据（包含超大单、大单拆分）
        """
        if not self.source_status["miaoxiang"]["ok"]:
            return {}

        try:
            url = f"https://api.miaoxiang.com/v1/stock/flow?code={code}"
            headers = {"Authorization": f"Bearer {self.mx_apikey}"}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=10)
            result = json.loads(resp.read())

            if result.get("code") == 0:
                data = result.get("data", {})
                return {
                    "success": True,
                    "code": code,
                    "main_net_inflow": data.get("main_net_inflow", 0),
                    "super_large_inflow": data.get("super_large_inflow", 0),
                    "large_inflow": data.get("large_inflow", 0),
                    "medium_inflow": data.get("medium_inflow", 0),
                    "small_inflow": data.get("small_inflow", 0),
                    "source": "miaoxiang",
                }
        except Exception as e:
            logger.error(f"妙想获取资金流向失败: {e}")

        return {"success": False}

    # ==================== 问财API（备用） ====================

    def query_iwencai(self, query: str, count: int = 10) -> Dict:
        """
        查询同花顺问财

        Args:
            query: 查询语句，如 "今日涨停股" "主力资金流入"
            count: 返回条数

        Returns:
            问财查询结果
        """
        if not self.source_status["iwencai"]["ok"]:
            return {"success": False, "message": "问财不可用"}

        try:
            url = "https://openapi.iwencai.com/v1/query2data"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.iwencai_key}",
            }
            body = json.dumps(
                {"query": query, "token": self.iwencai_key, "count": count}
            ).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=15)
            result = json.loads(resp.read())

            if result.get("status_code") == 0 or result.get("code") == 0:
                return {
                    "success": True,
                    "data": result,
                    "query": query,
                    "source": "iwencai",
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "未知错误"),
                    "query": query,
                }
        except Exception as e:
            logger.error(f"问财查询失败: {e}")
            return {"success": False, "message": str(e), "query": query}

    # ==================== 国信API（补充） ====================

    def get_realtime_quote_guosen(self, code: str) -> Dict:
        """
        获取实时行情（国信API）

        Args:
            code: 股票代码

        Returns:
            行情数据
        """
        if not self.source_status["guosen"]["ok"]:
            return {}

        try:
            set_code = "1" if code.startswith("6") else "0"
            url = f"https://api.guosen.com/v1/market/quote?code={code}&set_code={set_code}&key={self.gs_api_key}"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=10)
            result = json.loads(resp.read())

            if result.get("code") == 0:
                data = result.get("data", {})
                return {
                    "success": True,
                    "code": code,
                    "name": data.get("name", ""),
                    "price": data.get("price", 0),
                    "open": data.get("open", 0),
                    "high": data.get("high", 0),
                    "low": data.get("low", 0),
                    "volume": data.get("volume", 0),
                    "change": data.get("change", 0),
                    "change_pct": data.get("change_pct", 0),
                    "source": "guosen",
                }
        except Exception as e:
            logger.error(f"国信获取行情失败: {e}")

        return {"success": False}

    # ==================== 腾讯API（最后备用） ====================

    def get_realtime_quote(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情（腾讯财经，最后备用）

        Args:
            codes: 股票代码列表，如 ['sh000001', 'sz000858', 'sh600519']

        Returns:
            行情数据字典 {code: {name, price, change, change_pct, volume, ...}}
        """
        results = {}

        if not self.source_status["tencent"]["ok"]:
            return results

        try:
            codes_str = ",".join(codes)
            url = f"https://qt.gtimg.cn/q={codes_str}"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=10)
            raw = resp.read().decode("gbk")

            for line in raw.strip().split("\n"):
                if '="' not in line:
                    continue

                parts = line.split('="')[1].split('"')[0].split("~")
                if len(parts) < 35:
                    continue

                raw_code = line.split('="')[0].split("q=")[-1].strip()
                code = raw_code.replace("v_", "").strip()

                try:
                    price = float(parts[3]) if parts[3] else 0
                    yesterday_close = float(parts[4]) if parts[4] else price
                    change = price - yesterday_close
                    change_pct = (
                        (change / yesterday_close * 100) if yesterday_close else 0
                    )

                    results[code] = {
                        "name": parts[1] if len(parts) > 1 else "",
                        "code": code,
                        "price": price,
                        "open": float(parts[5]) if parts[5] else 0,
                        "volume": int(parts[6]) if parts[6] else 0,
                        "yesterday_close": yesterday_close,
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "high": float(parts[33]) if parts[33] else 0,
                        "low": float(parts[34]) if parts[34] else 0,
                        "turnover": float(parts[37]) if parts[37] else 0,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source": "tencent",
                    }
                except (ValueError, IndexError):
                    continue

        except Exception as e:
            logger.error(f"腾讯获取实时行情失败: {e}")

        return results

    # ==================== 统一接口 ====================

    def get_main_flow(self, code: str) -> Dict:
        """
        获取主力资金流向（按优先级自动选择数据源）

        Args:
            code: 股票代码

        Returns:
            资金流向数据
        """
        # 1. 优先妙想
        result = self.get_main_flow_miaoxiang(code)
        if result.get("success"):
            return result

        # 2. 问财备用
        result = self.query_iwencai(f"{code} 主力资金流向", count=5)
        if result.get("success"):
            try:
                data = result["data"]
                columns = data.get("columns", [])
                rows = data.get("data", [])
                if rows:
                    row = rows[0]
                    stock = dict(zip(columns, row))
                    return {
                        "success": True,
                        "code": code,
                        "main_net_inflow": stock.get("主力净流入", 0),
                        "source": "iwencai",
                    }
            except Exception as e:
                logger.error(f"解析问财资金流向失败: {e}")

        return {"success": False, "message": "所有数据源均不可用"}

    def get_limit_up_stocks(self) -> List[Dict]:
        """
        获取今日涨停股列表

        Returns:
            涨停股列表
        """
        result = self.query_iwencai("今日涨停股", count=50)

        if not result["success"]:
            return []

        stocks = []
        try:
            data = result["data"]
            columns = data.get("columns", [])
            rows = data.get("data", [])

            for row in rows:
                stock = dict(zip(columns, row))
                stocks.append(
                    {
                        "code": stock.get("代码", ""),
                        "name": stock.get("名称", ""),
                        "price": stock.get("现价", 0),
                        "change_pct": stock.get("涨跌幅", 0),
                        "reason": stock.get("涨停原因类别", ""),
                    }
                )
        except Exception as e:
            logger.error(f"解析涨停股数据失败: {e}")

        return stocks

    def get_market_sentiment(self) -> Dict:
        """
        获取市场情绪指标

        Returns:
            情绪数据字典
        """
        sentiment = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "index": {},
            "limit_up_count": 0,
            "sentiment_level": "UNKNOWN",
        }

        # 获取主要指数
        try:
            quotes = self.get_realtime_quote(
                ["sh000001", "sz399001", "sz399006", "sh000300"]
            )
            sentiment["index"] = quotes

            # 计算整体情绪
            changes = [q["change_pct"] for q in quotes.values() if q.get("change_pct")]
            avg_change = sum(changes) / len(changes) if changes else 0

            if avg_change > 2:
                sentiment["sentiment_level"] = "EXTREME_GREED"
            elif avg_change > 0.5:
                sentiment["sentiment_level"] = "GREED"
            elif avg_change > -0.5:
                sentiment["sentiment_level"] = "NEUTRAL"
            elif avg_change > -2:
                sentiment["sentiment_level"] = "FEAR"
            else:
                sentiment["sentiment_level"] = "EXTREME_FEAR"
        except Exception as e:
            logger.error(f"获取市场情绪失败: {e}")

        # 涨停股数量
        try:
            limit_ups = self.get_limit_up_stocks()
            sentiment["limit_up_count"] = len(limit_ups)
        except Exception:
            pass

        return sentiment

    def print_sentiment_report(self, sentiment: Dict):
        """打印情绪报告"""
        index = sentiment.get("index", {})

        logger.info("=" * 60)
        logger.info(f"市场情绪报告 - {sentiment.get('date')} {sentiment.get('time')}")
        logger.info("=" * 60)

        # 指数
        logger.info("主要指数:")
        for code, data in index.items():
            change = data.get("change_pct", 0)
            emoji = "🔴" if change > 0 else "🟢" if change < 0 else "⚪"
            logger.info(
                f"  {emoji} {data.get('name', '未知')}: {data.get('price', 0):.2f} ({change:+.2f}%)"
            )

        # 情绪
        level = sentiment.get("sentiment_level", "UNKNOWN")
        level_map = {
            "EXTREME_GREED": "😱 极度贪婪",
            "GREED": "😊 贪婪",
            "NEUTRAL": "😐 中性",
            "FEAR": "😰 恐惧",
            "EXTREME_FEAR": "😱 极度恐惧",
        }
        logger.info(f"市场情绪: {level_map.get(level, level)}")
        logger.info(f"涨停股数量: {sentiment.get('limit_up_count', 0)}家")
        logger.info("=" * 60)


def main():
    """测试数据源"""
    ds = DataSource()

    # 获取市场情绪
    sentiment = ds.get_market_sentiment()
    ds.print_sentiment_report(sentiment)

    # 测试获取单股行情
    logger.info("个股行情测试:")
    quotes = ds.get_realtime_quote(["sh600519", "sz000858", "sh000001"])
    for code, data in quotes.items():
        logger.info(
            f"  {data.get('name')}({code}): {data.get('price')} ({data.get('change_pct'):+.2f}%)"
        )


if __name__ == "__main__":
    main()
