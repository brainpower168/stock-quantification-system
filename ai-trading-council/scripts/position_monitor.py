#!/usr/bin/env python3
"""
Position Monitor - 持仓监控模块
实时监控持仓状态，自动触发止损止盈预警
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "council_config.json"
DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class Position:
    """持仓信息"""

    stock_code: str
    stock_name: str
    shares: int
    cost: float
    current_price: float
    profit_loss: float
    profit_loss_pct: float
    market_value: float
    alerts: List[str]


@dataclass
class Alert:
    """预警信息"""

    stock_code: str
    stock_name: str
    alert_type: str  # STOP_LOSS, TAKE_PROFIT, PRICE_CHANGE, FUND_FLOW
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    timestamp: str


class PositionMonitor:
    """持仓监控器"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path or CONFIG_PATH)
        self.positions = self._load_positions()

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_positions(self) -> Dict[str, dict]:
        """加载持仓数据"""
        return self.config.get("user_positions", {})

    def check_positions(self) -> List[Position]:
        """检查所有持仓"""
        results = []

        for code, pos in self.positions.items():
            position = self._check_single_position(code, pos)
            results.append(position)

        return results

    def _check_single_position(self, code: str, pos: dict) -> Position:
        """检查单个持仓"""
        name = pos.get("name", code)
        shares = pos.get("shares", 0)
        cost = pos.get("cost", 0)

        # 模拟当前价格（实际应从API获取）
        current_price = cost * 1.02  # 模拟涨2%

        # 计算盈亏
        profit_loss = (current_price - cost) * shares
        profit_loss_pct = (current_price - cost) / cost * 100
        market_value = current_price * shares

        # 生成预警
        alerts = self._generate_alerts(code, name, cost, current_price, profit_loss_pct)

        return Position(
            stock_code=code,
            stock_name=name,
            shares=shares,
            cost=cost,
            current_price=current_price,
            profit_loss=profit_loss,
            profit_loss_pct=profit_loss_pct,
            market_value=market_value,
            alerts=alerts,
        )

    def _generate_alerts(
        self,
        code: str,
        name: str,
        cost: float,
        current_price: float,
        profit_loss_pct: float,
    ) -> List[str]:
        """生成预警信息"""
        alerts = []
        limits = self.config.get("risk_limits", {})

        # 止损检查
        max_loss = limits.get("max_loss_pct", 5)
        if profit_loss_pct <= -max_loss:
            alerts.append(
                f"🔴 止损预警: 亏损 {abs(profit_loss_pct):.2f}% 超过 {max_loss}%"
            )

        # 止盈提醒
        if profit_loss_pct >= 10:
            alerts.append(f"🟢 止盈提醒: 盈利 {profit_loss_pct:.2f}%，考虑保护利润")

        # 回撤提醒
        if profit_loss_pct > 5 and profit_loss_pct < 10:
            alerts.append(f"🟡 回撤提醒: 盈利 {profit_loss_pct:.2f}%，注意保护利润")

        return alerts

    def get_all_alerts(self) -> List[Alert]:
        """获取所有预警"""
        alerts = []
        positions = self.check_positions()

        for pos in positions:
            for alert_msg in pos.alerts:
                severity = "HIGH" if "止损" in alert_msg else "MEDIUM"

                alerts.append(
                    Alert(
                        stock_code=pos.stock_code,
                        stock_name=pos.stock_name,
                        alert_type="STOP_LOSS"
                        if "止损" in alert_msg
                        else "TAKE_PROFIT",
                        severity=severity,
                        message=alert_msg,
                        timestamp=datetime.now().isoformat(),
                    )
                )

        return alerts

    def add_position(self, code: str, name: str, shares: int, cost: float):
        """添加持仓"""
        self.positions[code] = {"name": name, "shares": shares, "cost": cost}
        self._save_positions()
        print(f"已添加持仓: {name}({code}) {shares}股 成本{cost}元")

    def remove_position(self, code: str):
        """移除持仓"""
        if code in self.positions:
            name = self.positions[code].get("name", code)
            del self.positions[code]
            self._save_positions()
            print(f"已移除持仓: {name}({code})")

    def _save_positions(self):
        """保存持仓到配置文件"""
        self.config["user_positions"] = self.positions
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def watch(self, interval: int = 60):
        """持续监控

        Args:
            interval: 检查间隔（秒）
        """
        print(f"开始监控持仓，每 {interval} 秒检查一次...")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检查持仓...")
                positions = self.check_positions()

                for pos in positions:
                    status = f"{pos.profit_loss_pct:+.2f}%"
                    alerts_str = " | ".join(pos.alerts) if pos.alerts else "正常"

                    print(f"  {pos.stock_name}: {status} | {alerts_str}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n监控已停止")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Position Monitor")
    parser.add_argument("--check", action="store_true", help="单次检查")
    parser.add_argument("--watch", action="store_true", help="持续监控")
    parser.add_argument("--add", type=str, help="添加持仓: 代码,数量,成本")
    parser.add_argument("--remove", type=str, help="移除持仓: 代码")
    args = parser.parse_args()

    monitor = PositionMonitor()

    if args.check:
        positions = monitor.check_positions()
        print("\n持仓状态:")
        print("-" * 60)
        for pos in positions:
            print(f"{pos.stock_name}({pos.stock_code})")
            print(f"  持仓: {pos.shares}股 | 成本: {pos.cost:.2f}元")
            print(
                f"  现价: {pos.current_price:.2f}元 | 盈亏: {pos.profit_loss_pct:+.2f}%"
            )
            if pos.alerts:
                print(f"  预警: {' | '.join(pos.alerts)}")
            print()

    elif args.watch:
        monitor.watch()

    elif args.add:
        parts = args.add.split(",")
        if len(parts) == 3:
            code, shares, cost = parts
            monitor.add_position(code, code, int(shares), float(cost))
        else:
            print("格式: 代码,数量,成本")

    elif args.remove:
        monitor.remove_position(args.remove)

    else:
        # 默认显示预警
        alerts = monitor.get_all_alerts()
        if alerts:
            print("\n当前预警:")
            for alert in alerts:
                print(f"  [{alert.severity}] {alert.stock_name}: {alert.message}")
        else:
            print("暂无预警")


if __name__ == "__main__":
    main()
