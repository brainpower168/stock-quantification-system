#!/usr/bin/env python3
"""
AI Trading Council Dashboard - Web 仪表盘
Streamlit 可视化界面
"""

import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from council_engine import AITradingCouncil, CouncilDecision
from position_monitor import PositionMonitor

# 配置
CONFIG_PATH = Path(__file__).parent.parent / "config" / "council_config.json"
DATA_DIR = Path(__file__).parent.parent / "data"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="AI Trading Council", page_icon="🤖", layout="wide")

    # 标题
    st.title("🤖 AI Trading Council Dashboard")
    st.markdown("---")

    # 加载配置
    config = load_config()

    # 侧边栏
    st.sidebar.header("功能导航")
    page = st.sidebar.radio(
        "选择功能", ["📊 概览", "📈 持仓监控", "🧠 AI 决策", "⚙️ 设置"]
    )

    if page == "📊 概览":
        show_overview(config)
    elif page == "📈 持仓监控":
        show_positions(config)
    elif page == "🧠 AI 决策":
        show_ai_decision(config)
    elif page == "⚙️ 设置":
        show_settings(config)


def show_overview(config):
    """概览页面"""
    st.header("📊 系统概览")

    # 核心指标
    col1, col2, col3, col4 = st.columns(4)

    positions = config.get("user_positions", {})

    with col1:
        st.metric("持仓数量", len(positions))

    with col2:
        # 模拟总市值
        total_value = sum(
            pos.get("shares", 0) * pos.get("cost", 0) for pos in positions.values()
        )
        st.metric("总市值", f"¥{total_value:,.0f}")

    with col3:
        st.metric("AI 模型", len(config.get("models", {})))

    with col4:
        st.metric("系统状态", "运行中 ✅")

    st.markdown("---")

    # 持仓列表
    st.subheader("当前持仓")

    if positions:
        data = []
        for code, pos in positions.items():
            data.append(
                {
                    "代码": code,
                    "名称": pos.get("name", code),
                    "持仓": pos.get("shares", 0),
                    "成本": pos.get("cost", 0),
                    "市值": pos.get("shares", 0) * pos.get("cost", 0),
                }
            )

        st.dataframe(data, use_container_width=True)
    else:
        st.info("暂无持仓")

    # 快速操作
    st.markdown("---")
    st.subheader("快速操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("🧠 运行 AI 分析", use_container_width=True):
            st.session_state["run_analysis"] = True

    with col3:
        if st.button("📋 查看报告", use_container_width=True):
            st.info("请切换到 AI 决策页面查看")


def show_positions(config):
    """持仓监控页面"""
    st.header("📈 持仓监控")

    monitor = PositionMonitor()
    positions = monitor.check_positions()

    if not positions:
        st.info("暂无持仓")
        return

    # 预警概览
    alerts = monitor.get_all_alerts()
    if alerts:
        st.subheader("⚠️ 预警通知")
        for alert in alerts:
            if alert.severity == "HIGH":
                st.error(f"**{alert.stock_name}**: {alert.message}")
            elif alert.severity == "MEDIUM":
                st.warning(f"**{alert.stock_name}**: {alert.message}")
            else:
                st.info(f"**{alert.stock_name}**: {alert.message}")

        st.markdown("---")

    # 持仓详情
    st.subheader("持仓详情")

    for pos in positions:
        with st.expander(f"{pos.stock_name} ({pos.stock_code})", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("持仓", f"{pos.shares}股")

            with col2:
                st.metric("成本", f"¥{pos.cost:.2f}")

            with col3:
                st.metric("现价", f"¥{pos.current_price:.2f}")

            with col4:
                delta = f"{pos.profit_loss_pct:+.2f}%"
                st.metric("盈亏", f"¥{pos.profit_loss:,.0f}", delta=delta)

            if pos.alerts:
                st.markdown("**预警信息:**")
                for alert in pos.alerts:
                    st.write(f"- {alert}")


def show_ai_decision(config):
    """AI 决策页面"""
    st.header("🧠 AI 决策分析")

    # 输入股票代码
    col1, col2 = st.columns([3, 1])

    with col1:
        stock_input = st.text_input("股票代码", placeholder="输入股票代码，如 600519")

    with col2:
        analyze_btn = st.button("🔍 分析", type="primary", use_container_width=True)

    # 或选择持仓
    positions = config.get("user_positions", {})
    if positions:
        st.markdown("**或选择持仓股票:**")
        cols = st.columns(min(len(positions), 4))
        for i, (code, pos) in enumerate(positions.items()):
            with cols[i % 4]:
                if st.button(f"{pos.get('name', code)}", key=f"pos_{code}"):
                    stock_input = code
                    analyze_btn = True

    st.markdown("---")

    # 执行分析
    if analyze_btn and stock_input:
        with st.spinner("AI 正在分析中..."):
            try:
                council = AITradingCouncil()
                decision = council.analyze_stock(stock_input)

                # 显示结果
                st.subheader(f"分析结果: {decision.stock_name} ({decision.stock_code})")

                # 决策卡片
                col1, col2, col3 = st.columns(3)

                with col1:
                    decision_color = {
                        "STRONG_BUY": "🟢",
                        "BUY": "🔵",
                        "HOLD": "🟡",
                        "SELL": "🟠",
                        "STRONG_SELL": "🔴",
                    }
                    st.metric(
                        "决策",
                        f"{decision_color.get(decision.final_decision, '⚪')} {decision.final_decision}",
                    )

                with col2:
                    st.metric("置信度", f"{decision.confidence:.1%}")

                with col3:
                    st.metric("共识程度", decision.consensus_level)

                # 模型投票详情
                st.markdown("---")
                st.subheader("模型投票详情")

                for vote in decision.votes:
                    with st.expander(
                        f"{vote.role} ({vote.model_name})", expanded=False
                    ):
                        st.markdown(f"**决策**: {vote.decision}")
                        st.markdown(f"**置信度**: {vote.confidence:.1%}")
                        st.markdown(
                            f"**关键因素**: {', '.join(vote.key_factors) or '无'}"
                        )
                        st.markdown(f"**分析理由**:")
                        st.write(vote.reasoning[:500])

                # 风险警告
                if decision.risk_warnings:
                    st.markdown("---")
                    st.subheader("⚠️ 风险警告")
                    for warning in decision.risk_warnings:
                        st.warning(warning)

            except Exception as e:
                st.error(f"分析失败: {e}")

    # 历史报告
    st.markdown("---")
    st.subheader("📋 历史报告")

    report_dir = DATA_DIR / "reports"
    if report_dir.exists():
        reports = sorted(report_dir.glob("council_*.md"), reverse=True)[:5]
        if reports:
            for report in reports:
                with st.expander(report.name):
                    with open(report, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
        else:
            st.info("暂无历史报告")
    else:
        st.info("暂无历史报告")


def show_settings(config):
    """设置页面"""
    st.header("⚙️ 系统设置")

    # API 配置
    st.subheader("API 配置")

    models = config.get("models", {})
    for model_key, model_config in models.items():
        with st.expander(f"{model_config.get('role', model_key)} ({model_key})"):
            st.text_input(
                "模型名称",
                value=model_config.get("name", ""),
                key=f"name_{model_key}",
                disabled=True,
            )
            st.text_input(
                "API Key",
                value="已配置" if model_config.get("api_key") else "未配置",
                key=f"key_{model_key}",
                type="password",
                disabled=True,
            )

    # 风控设置
    st.markdown("---")
    st.subheader("风控设置")

    limits = config.get("risk_limits", {})

    col1, col2 = st.columns(2)

    with col1:
        st.number_input(
            "单股最大仓位 (%)",
            value=limits.get("max_position_pct", 20),
            min_value=1,
            max_value=100,
        )

    with col2:
        st.number_input(
            "最大亏损止损 (%)",
            value=limits.get("max_loss_pct", 5),
            min_value=1,
            max_value=20,
        )

    # 持仓管理
    st.markdown("---")
    st.subheader("持仓管理")

    positions = config.get("user_positions", {})

    if positions:
        st.write("当前持仓:")
        for code, pos in positions.items():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"{pos.get('name', code)}")
            with col2:
                st.write(f"{pos.get('shares', 0)}股")
            with col3:
                st.write(f"成本 {pos.get('cost', 0):.2f}")
            with col4:
                if st.button("删除", key=f"del_{code}"):
                    st.warning(f"已删除 {code}")

    # 添加持仓
    st.markdown("**添加持仓:**")
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        new_code = st.text_input("代码", key="new_code")
    with col2:
        new_name = st.text_input("名称", key="new_name")
    with col3:
        new_shares = st.number_input("数量", min_value=1, value=100, key="new_shares")
    with col4:
        new_cost = st.number_input("成本", min_value=0.01, value=10.0, key="new_cost")

    if st.button("添加"):
        if new_code and new_name:
            st.success(f"已添加 {new_name}({new_code})")
        else:
            st.error("请填写代码和名称")


if __name__ == "__main__":
    main()
