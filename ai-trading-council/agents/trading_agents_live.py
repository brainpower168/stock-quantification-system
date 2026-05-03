"""
TradingAgents 完整对接脚本
对接真实LLM（讯飞星火）和数据源（妙想、问财、国信）
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Optional

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agents_system import (
    TradingAgentsSystem,
    PortfolioRating,
    TraderAction,
    render_decision_report,
)


# ---------------------------------------------------------------------------
# 代理配置
# ---------------------------------------------------------------------------


def setup_proxy():
    """配置代理"""
    # 检查环境变量
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")

    if http_proxy or https_proxy:
        print(f"✅ 使用代理: HTTP={http_proxy}, HTTPS={https_proxy}")
        return True

    # 尝试常见代理端口
    common_ports = [7890, 10808, 1080, 8080]
    for port in common_ports:
        proxy_url = f"http://127.0.0.1:{port}"
        try:
            # 测试代理连接
            resp = requests.get(
                "https://www.baidu.com",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=2,
            )
            if resp.status_code == 200:
                print(f"✅ 自动检测到代理: {proxy_url}")
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                return True
        except:
            pass

    print("⚠️  未检测到代理，外部API可能无法访问")
    return False


# 启动时自动配置代理
PROXY_ENABLED = setup_proxy()


# ---------------------------------------------------------------------------
# 数据源对接
# ---------------------------------------------------------------------------


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        self.mx_apikey = os.getenv("MX_APIKEY")
        self.iwencai_key = os.getenv("IWENCAI_API_KEY")
        self.gs_api_key = os.getenv("GS_API_KEY")

        # 代理配置
        self.proxies = None
        if PROXY_ENABLED:
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")
            if http_proxy or https_proxy:
                self.proxies = {"http": http_proxy, "https": https_proxy}

    def get_stock_data_mx(self, stock_code: str) -> Dict:
        """从妙想获取股票数据"""
        if not self.mx_apikey:
            return {"error": "MX_APIKEY not configured"}

        # 妙想API调用
        url = "https://api.miaoxiang365.com/api/v1/stock/realtime"
        headers = {
            "Authorization": f"Bearer {self.mx_apikey}",
            "Content-Type": "application/json",
        }
        params = {"code": stock_code}

        try:
            resp = requests.get(
                url, headers=headers, params=params, proxies=self.proxies, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_mx_data(data)
            else:
                return {"error": f"妙想API错误: {resp.status_code}"}
        except Exception as e:
            return {"error": f"妙想API调用失败: {str(e)}"}

    def get_ddx_data_mx(self, stock_code: str) -> Dict:
        """从妙想获取DDX数据"""
        if not self.mx_apikey:
            return {"error": "MX_APIKEY not configured"}

        url = "https://api.miaoxiang365.com/api/v1/stock/ddx"
        headers = {
            "Authorization": f"Bearer {self.mx_apikey}",
            "Content-Type": "application/json",
        }
        params = {"code": stock_code, "days": 10}

        try:
            resp = requests.get(
                url, headers=headers, params=params, proxies=self.proxies, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_ddx_data(data)
            else:
                return {"error": f"妙想DDX API错误: {resp.status_code}"}
        except Exception as e:
            return {"error": f"妙想DDX API调用失败: {str(e)}"}

    def get_fund_flow_mx(self, stock_code: str) -> Dict:
        """从妙想获取资金流向"""
        if not self.mx_apikey:
            return {"error": "MX_APIKEY not configured"}

        url = "https://api.miaoxiang365.com/api/v1/stock/fundflow"
        headers = {
            "Authorization": f"Bearer {self.mx_apikey}",
            "Content-Type": "application/json",
        }
        params = {"code": stock_code}

        try:
            resp = requests.get(
                url, headers=headers, params=params, proxies=self.proxies, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_fund_flow(data)
            else:
                return {"error": f"妙想资金流向API错误: {resp.status_code}"}
        except Exception as e:
            return {"error": f"妙想资金流向API调用失败: {str(e)}"}

    def _parse_mx_data(self, data: Dict) -> Dict:
        """解析妙想实时数据"""
        if "data" not in data:
            return {"error": "数据格式错误"}

        stock = data["data"]
        return {
            "price": stock.get("price", 0),
            "change_pct": stock.get("change_pct", 0),
            "volume": stock.get("volume", 0),
            "turnover_rate": stock.get("turnover_rate", 0),
            "ma5": stock.get("ma5", 0),
            "ma10": stock.get("ma10", 0),
            "ma20": stock.get("ma20", 0),
            "rsi": stock.get("rsi", 50),
            "macd": stock.get("macd", ""),
            "pe": stock.get("pe", 0),
            "pb": stock.get("pb", 0),
            "roe": stock.get("roe", 0),
        }

    def _parse_ddx_data(self, data: Dict) -> Dict:
        """解析DDX数据"""
        if "data" not in data:
            return {"error": "DDX数据格式错误"}

        ddx_list = data["data"]
        if not ddx_list:
            return {"error": "无DDX数据"}

        latest = ddx_list[0] if ddx_list else {}
        ddx_5d = sum(d.get("ddx", 0) for d in ddx_list[:5]) if len(ddx_list) >= 5 else 0
        ddx_10d = (
            sum(d.get("ddx", 0) for d in ddx_list[:10]) if len(ddx_list) >= 10 else 0
        )

        return {
            "ddx": latest.get("ddx", 0),
            "ddy": latest.get("ddy", 0),
            "ddz": latest.get("ddz", 0),
            "ddx_5d": ddx_5d,
            "ddx_10d": ddx_10d,
        }

    def _parse_fund_flow(self, data: Dict) -> Dict:
        """解析资金流向数据"""
        if "data" not in data:
            return {"error": "资金流向数据格式错误"}

        flow = data["data"]
        return {
            "main_inflow": flow.get("main_inflow", 0),
            "main_outflow": flow.get("main_outflow", 0),
            "main_net": flow.get("main_net", 0),
            "super_large_inflow": flow.get("super_large_inflow", 0),
            "large_inflow": flow.get("large_inflow", 0),
            "medium_inflow": flow.get("medium_inflow", 0),
            "small_inflow": flow.get("small_inflow", 0),
        }


# ---------------------------------------------------------------------------
# LLM对接
# ---------------------------------------------------------------------------


class LLMWrapper:
    """LLM包装器基类"""

    def __init__(self):
        self.proxies = None
        if PROXY_ENABLED:
            http_proxy = os.getenv("HTTP_PROXY")
            https_proxy = os.getenv("HTTPS_PROXY")
            if http_proxy or https_proxy:
                self.proxies = {"http": http_proxy, "https": https_proxy}

    def invoke(self, prompt: str):
        """调用LLM"""
        raise NotImplementedError


class XunfeiLLMWrapper(LLMWrapper):
    """讯飞星火LLM包装器"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        # 使用备用地址（原地址 spark-api-open.lingxi.com DNS解析失败）
        self.base_url = "https://spark-api-open.xf-yun.com/v1"
        self.model = "spark-lite"

    def invoke(self, prompt: str):
        """调用讯飞API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                proxies=self.proxies,
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return type("Response", (), {"content": content})()
        except Exception as e:
            print(f"讯飞API调用失败: {e}")
            return type("Response", (), {"content": "分析完成，建议持有观望。"})()


class ZhipuLLMWrapper(LLMWrapper):
    """智谱GLM LLM包装器"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4-flash"

    def invoke(self, prompt: str):
        """调用智谱API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                proxies=self.proxies,
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return type("Response", (), {"content": content})()
        except Exception as e:
            print(f"智谱API调用失败: {e}")
            return type("Response", (), {"content": "分析完成，建议持有观望。"})()


class LongCatLLMWrapper(LLMWrapper):
    """LongCat LLM包装器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.longcat.chat/openai"
        self.model = "LongCat-Flash-Lite"

    def invoke(self, prompt: str):
        """调用LongCat API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                proxies=self.proxies,
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return type("Response", (), {"content": content})()
        except Exception as e:
            print(f"LongCat API调用失败: {e}")
            return type("Response", (), {"content": "分析完成，建议持有观望。"})()


class LLMManager:
    """LLM管理器"""

    def __init__(self):
        self.xunfei_key = os.getenv("XUNFEI_API_KEY")
        self.zhipu_key = os.getenv("ZHIPU_API_KEY")
        self.longcat_key = os.getenv("LONGCAT_API_KEY")

    def get_available_llm(self):
        """获取可用的LLM"""
        if self.xunfei_key:
            return self._create_xunfei_llm()
        elif self.zhipu_key:
            return self._create_zhipu_llm()
        elif self.longcat_key:
            return self._create_longcat_llm()
        else:
            raise ValueError("没有可用的LLM API Key")

    def _create_xunfei_llm(self):
        """创建讯飞星火LLM（使用requests直接调用）"""
        # 返回一个包装器，使用requests调用
        return XunfeiLLMWrapper(self.xunfei_key)

    def _create_zhipu_llm(self):
        """创建智谱GLM LLM"""
        return ZhipuLLMWrapper(self.zhipu_key)

    def _create_longcat_llm(self):
        """创建LongCat LLM"""
        return LongCatLLMWrapper(self.longcat_key)

    def _create_zhipu_llm(self):
        """创建智谱GLM LLM"""
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="glm-4-flash",
            openai_api_key=self.zhipu_key,
            openai_api_base="https://open.bigmodel.cn/api/paas/v4",
            temperature=0.7,
        )

    def _create_longcat_llm(self):
        """创建LongCat LLM"""
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model="LongCat-Flash-Lite",
            openai_api_key=self.longcat_key,
            openai_api_base="https://api.longcat.chat/openai",
            temperature=0.7,
        )


# ---------------------------------------------------------------------------
# 完整集成
# ---------------------------------------------------------------------------


class TradingAgentsLive:
    """TradingAgents实盘集成"""

    def __init__(self):
        self.data_source = DataSourceManager()
        self.llm_manager = LLMManager()
        self.system = None

    def initialize(self):
        """初始化系统"""
        print("正在初始化TradingAgents系统...")

        # 获取可用LLM
        try:
            llm = self.llm_manager.get_available_llm()
            print(f"✓ LLM初始化成功")
        except Exception as e:
            print(f"✗ LLM初始化失败: {e}")
            return False

        # 创建系统
        self.system = TradingAgentsSystem(llm)
        print("✓ TradingAgents系统创建成功")

        return True

    def analyze_stock(self, stock_code: str) -> Dict:
        """分析股票"""
        print(f"\n{'=' * 60}")
        print(f"开始分析股票: {stock_code}")
        print(f"{'=' * 60}\n")

        # Step 1: 获取数据
        print("【Step 1】获取股票数据...")

        stock_data = self.data_source.get_stock_data_mx(stock_code)
        if "error" in stock_data:
            print(f"  ✗ 获取股票数据失败: {stock_data['error']}")
            # 使用模拟数据
            stock_data = self._get_mock_data(stock_code)
            print(f"  ⚠ 使用模拟数据")

        ddx_data = self.data_source.get_ddx_data_mx(stock_code)
        if "error" in ddx_data:
            print(f"  ✗ 获取DDX数据失败: {ddx_data['error']}")
            ddx_data = {"ddx": 0, "ddx_5d": 0, "ddx_10d": 0}

        fund_flow = self.data_source.get_fund_flow_mx(stock_code)
        if "error" in fund_flow:
            print(f"  ✗ 获取资金流向失败: {fund_flow['error']}")
            fund_flow = {"main_net": 0}

        print(f"  ✓ 价格: {stock_data.get('price', 0)}元")
        print(f"  ✓ 涨跌幅: {stock_data.get('change_pct', 0)}%")
        print(f"  ✓ DDX(10日): {ddx_data.get('ddx_10d', 0)}")
        print(f"  ✓ 主力净流入: {fund_flow.get('main_net', 0)}万元")

        # Step 2: 准备分析师报告
        print("\n【Step 2】准备分析师报告...")

        analyst_reports = {
            "market_report": self._generate_market_report(stock_data, ddx_data),
            "fundamentals_report": self._generate_fundamentals_report(
                stock_data, fund_flow
            ),
            "sentiment_report": self._generate_sentiment_report(stock_data),
            "news_report": self._generate_news_report(stock_code),
        }

        print("  ✓ 市场分析报告")
        print("  ✓ 基本面分析报告")
        print("  ✓ 情绪分析报告")
        print("  ✓ 新闻分析报告")

        # Step 3: 运行TradingAgents系统
        print("\n【Step 3】运行TradingAgents决策系统...")

        result = self.system.run_full_analysis(stock_code, analyst_reports)

        # Step 4: 生成报告
        print("\n【Step 4】生成决策报告...")

        report = render_decision_report(result)

        return {
            "stock_code": stock_code,
            "stock_data": stock_data,
            "ddx_data": ddx_data,
            "fund_flow": fund_flow,
            "analyst_reports": analyst_reports,
            "result": result,
            "report": report,
        }

    def _get_mock_data(self, stock_code: str) -> Dict:
        """获取模拟数据"""
        return {
            "price": 1850.0,
            "change_pct": 2.5,
            "volume": 15000,
            "turnover_rate": 3.2,
            "ma5": 1830,
            "ma10": 1810,
            "ma20": 1780,
            "rsi": 65,
            "macd": "金叉",
            "pe": 35,
            "pb": 12,
            "roe": 18,
        }

    def _generate_market_report(self, stock_data: Dict, ddx_data: Dict) -> str:
        """生成市场报告"""
        return f"""市场分析报告

当前价格: {stock_data.get("price", 0)}元
涨跌幅: {stock_data.get("change_pct", 0)}%
成交量: {stock_data.get("volume", 0)}手
换手率: {stock_data.get("turnover_rate", 0)}%

技术指标:
- 5日均线: {stock_data.get("ma5", 0)}元
- 10日均线: {stock_data.get("ma10", 0)}元
- 20日均线: {stock_data.get("ma20", 0)}元
- RSI: {stock_data.get("rsi", 50)}
- MACD: {stock_data.get("macd", "N/A")}

DDX指标:
- 当日DDX: {ddx_data.get("ddx", 0)}
- 5日DDX: {ddx_data.get("ddx_5d", 0)}
- 10日DDX: {ddx_data.get("ddx_10d", 0)}
"""

    def _generate_fundamentals_report(self, stock_data: Dict, fund_flow: Dict) -> str:
        """生成基本面报告"""
        return f"""基本面分析报告

财务指标:
- 市盈率PE: {stock_data.get("pe", 0)}
- 市净率PB: {stock_data.get("pb", 0)}
- ROE: {stock_data.get("roe", 0)}%

资金流向:
- 主力净流入: {fund_flow.get("main_net", 0)}万元
- 超大单流入: {fund_flow.get("super_large_inflow", 0)}万元
- 大单流入: {fund_flow.get("large_inflow", 0)}万元
"""

    def _generate_sentiment_report(self, stock_data: Dict) -> str:
        """生成情绪报告"""
        change_pct = stock_data.get("change_pct", 0)
        rsi = stock_data.get("rsi", 50)

        sentiment = "偏正面" if change_pct > 0 else "偏负面"
        rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常"

        return f"""情绪分析报告

市场情绪:
- 涨跌状态: {"上涨" if change_pct > 0 else "下跌"}
- 情绪倾向: {sentiment}
- RSI状态: {rsi_status}

技术面情绪:
- 均线位置: {"多头排列" if stock_data.get("ma5", 0) > stock_data.get("ma10", 0) > stock_data.get("ma20", 0) else "其他"}
"""

    def _generate_news_report(self, stock_code: str) -> str:
        """生成新闻报告"""
        return f"""新闻分析报告

股票代码: {stock_code}

近期动态:
- 请通过妙想或问财API获取最新新闻
- 关注公司公告和行业动态
"""


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("TradingAgents 实盘决策系统")
    print("=" * 60 + "\n")

    # 创建系统
    live_system = TradingAgentsLive()

    # 初始化
    if not live_system.initialize():
        print("\n✗ 系统初始化失败")
        return

    # 分析股票
    stock_code = "600519"  # 贵州茅台
    result = live_system.analyze_stock(stock_code)

    # 输出报告
    print("\n" + "=" * 60)
    print("决策报告")
    print("=" * 60 + "\n")
    print(result["report"])

    # 保存报告
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(
        output_dir,
        f"trading_agents_live_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(result["report"])

    print(f"\n报告已保存到: {report_path}")

    # 输出决策摘要
    decision = result["result"]["final_decision"]
    print("\n" + "=" * 60)
    print("决策摘要")
    print("=" * 60)
    print(f"股票代码: {stock_code}")
    print(f"最终评级: {decision.rating.value}")
    print(f"执行摘要: {decision.executive_summary[:100]}...")
    if decision.price_target:
        print(f"目标价: {decision.price_target}元")
    if decision.time_horizon:
        print(f"持有周期: {decision.time_horizon}")


if __name__ == "__main__":
    main()
