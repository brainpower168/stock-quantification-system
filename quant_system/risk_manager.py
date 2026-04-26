# -*- coding: utf-8 -*-
"""
智能风控模块 - Risk Manager
凯利公式仓位计算、动态止损、组合最大回撤监控

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class RiskManager:
    """智能风控引擎"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 风控参数
        self.max_position_per_stock = self.config.get('max_position_per_stock', 0.20)  # 单票最大仓位20%
        self.max_total_position = self.config.get('max_total_position', 0.80)  # 总仓位上限80%
        self.max_drawdown = self.config.get('max_drawdown', 0.05)  # 最大回撤5%
        self.default_stop_loss = self.config.get('default_stop_loss', 0.03)  # 默认止损-3%
        self.default_take_profit = self.config.get('default_take_profit', 0.08)  # 默认止盈+8%
        
        # 历史记录
        self.trade_history_file = self.data_dir / 'risk_trade_history.json'
        self.trade_history = self._load_trade_history()
    
    def _load_trade_history(self) -> Dict:
        """加载交易历史"""
        if self.trade_history_file.exists():
            try:
                with open(self.trade_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'trades': [], 'peak_equity': 0, 'current_equity': 0}
    
    def _save_trade_history(self):
        """保存交易历史"""
        try:
            with open(self.trade_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存交易历史失败: {e}")
    
    def calculate_kelly_position(self, 
                                 win_rate: float,
                                 avg_win: float,
                                 avg_loss: float,
                                 kelly_fraction: float = 0.5) -> float:
        """
        凯利公式计算最优仓位
        
        凯利公式: f* = (p * b - q) / b
        其中:
          f* = 仓位比例
          p = 获胜概率
          q = 失败概率 (1-p)
          b = 赔率 (avg_win/avg_loss)
        
        Args:
            win_rate: 胜率 (0-1)
            avg_win: 平均盈利比例 (正数，如0.08表示+8%)
            avg_loss: 平均亏损比例 (正数，如0.03表示-3%)
            kelly_fraction: 凯利系数（0.5为半凯利，更保守）
        
        Returns:
            最优仓位比例 (0-1)
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        
        b = avg_win / avg_loss  # 赔率
        p = win_rate  # 胜率
        q = 1 - p  # 败率
        
        # 凯利公式
        kelly = (p * b - q) / b
        
        # 应用凯利系数（半凯利更保守）
        position = kelly * kelly_fraction
        
        # 限制在合理范围
        position = max(0, min(position, self.max_position_per_stock))
        
        return round(position, 4)
    
    def calculate_position_size(self,
                              account_equity: float,
                              stock_price: float,
                              stop_loss_pct: float,
                              max_loss_pct: float = 0.02) -> Tuple[int, float]:
        """
        计算买入股数
        
        Args:
            account_equity: 账户总资金
            stock_price: 股票价格
            stop_loss_pct: 止损幅度 (如0.03表示-3%)
            max_loss_pct: 最大单笔亏损比例 (默认2%)
        
        Returns:
            (买入股数, 实际仓位比例)
        """
        # 最大亏损金额
        max_loss_amount = account_equity * max_loss_pct
        
        # 每股价差（止损幅度）
        price_diff = stock_price * stop_loss_pct
        
        # 计算股数
        if price_diff <= 0:
            return 0, 0.0
        
        shares = int(max_loss_amount / price_diff / 100) * 100  # 整手
        
        # 计算实际仓位
        actual_amount = shares * stock_price
        position_ratio = actual_amount / account_equity
        
        return shares, round(position_ratio, 4)
    
    def calculate_stop_loss(self, 
                           entry_price: float,
                           strategy: str = 'fixed',
                           atr: float = 0,
                           ma5: float = 0,
                           ma10: float = 0) -> float:
        """
        计算止损价
        
        Args:
            entry_price: 买入价格
            strategy: 止损策略
                - fixed: 固定止损（-3%）
                - atr: ATR止损
                - ma: 均线止损
            atr: ATR值（用于ATR策略）
            ma5: 5日均线（用于均线策略）
            ma10: 10日均线
        
        Returns:
            止损价格
        """
        if strategy == 'atr':
            if atr > 0:
                stop_price = entry_price - 2 * atr
            else:
                stop_price = entry_price * 0.97  # 备用固定止损
        elif strategy == 'ma':
            if ma5 > 0 and ma10 > 0:
                stop_price = min(ma5, ma10)
            elif ma5 > 0:
                stop_price = ma5
            else:
                stop_price = entry_price * 0.97
        else:  # fixed
            stop_price = entry_price * (1 - self.default_stop_loss)
        
        return round(stop_price, 2)
    
    def calculate_take_profit(self,
                            entry_price: float,
                            strategy: str = 'fixed',
                            risk_reward_ratio: float = 2.0,
                            recent_high: float = 0) -> float:
        """
        计算止盈价
        
        Args:
            entry_price: 买入价格
            strategy: 止盈策略
                - fixed: 固定止盈
                - trailing: 移动止盈
                - risk_reward: 风险收益比止盈
            risk_reward_ratio: 风险收益比
            recent_high: 近期高点（用于移动止盈）
        
        Returns:
            止盈价格
        """
        if strategy == 'trailing':
            if recent_high > 0:
                # 移动止盈：从近期高点回落8%止盈
                stop_price = recent_high * 0.92
            else:
                stop_price = entry_price * (1 + self.default_take_profit)
        elif strategy == 'risk_reward':
            risk = entry_price * self.default_stop_loss
            stop_price = entry_price + risk * risk_reward_ratio
        else:  # fixed
            stop_price = entry_price * (1 + self.default_take_profit)
        
        return round(stop_price, 2)
    
    def check_portfolio_risk(self, 
                           positions: List[Dict],
                           account_equity: float) -> Dict:
        """
        检查组合风险
        
        Args:
            positions: 持仓列表
            account_equity: 账户总资金
        
        Returns:
            风险评估结果
        """
        total_value = sum(p.get('market_value', 0) for p in positions)
        total_position_ratio = total_value / account_equity
        
        # 统计盈亏
        total_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
        
        # 检查单票仓位
        position_alerts = []
        for pos in positions:
            ratio = pos.get('market_value', 0) / account_equity
            if ratio > self.max_position_per_stock:
                position_alerts.append({
                    'code': pos.get('code'),
                    'name': pos.get('name'),
                    'ratio': round(ratio * 100, 1),
                    'alert': f"仓位超限 ({ratio*100:.1f}% > {self.max_position_per_stock*100}%)"
                })
        
        # 检查总仓位
        total_position_alert = None
        if total_position_ratio > self.max_total_position:
            total_position_alert = f"总仓位超限 ({total_position_ratio*100:.1f}% > {self.max_total_position*100}%)"
        
        # 检查回撤
        peak = self.trade_history.get('peak_equity', account_equity)
        current = account_equity + total_pnl
        drawdown = (peak - current) / peak if peak > 0 else 0
        
        drawdown_alert = None
        if drawdown > self.max_drawdown:
            drawdown_alert = f"回撤超限 ({drawdown*100:.1f}% > {self.max_drawdown*100}%)"
        
        # 综合评级
        risk_level = 'LOW'
        risk_score = 0
        
        if position_alerts:
            risk_score += 30
            risk_level = 'HIGH'
        if total_position_alert:
            risk_score += 30
            risk_level = 'HIGH'
        if drawdown_alert:
            risk_score += 40
            risk_level = 'HIGH'
        elif total_position_ratio > 0.6:
            risk_score += 15
            risk_level = 'MEDIUM'
        
        return {
            'total_value': total_value,
            'total_position_ratio': round(total_position_ratio * 100, 1),
            'total_pnl': round(total_pnl, 2),
            'current_drawdown': round(drawdown * 100, 2),
            'position_alerts': position_alerts,
            'total_position_alert': total_position_alert,
            'drawdown_alert': drawdown_alert,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'suggestion': self._get_risk_suggestion(risk_level, position_alerts, drawdown_alert)
        }
    
    def _get_risk_suggestion(self, 
                            risk_level: str,
                            position_alerts: List,
                            drawdown_alert: str) -> str:
        """生成风险建议"""
        if risk_level == 'HIGH':
            if drawdown_alert:
                return "⚠️ 回撤超限，建议立即减仓50%！"
            if position_alerts:
                return f"⚠️ {len(position_alerts)}只股票仓位超限，建议减仓！"
            return "⚠️ 风险偏高，建议降低仓位！"
        elif risk_level == 'MEDIUM':
            return "⚡ 风险适中，注意控制仓位"
        else:
            return "✅ 风险可控，可以正常操作"
    
    def update_peak_equity(self, current_equity: float):
        """更新峰值资金"""
        self.trade_history['peak_equity'] = max(
            self.trade_history.get('peak_equity', 0),
            current_equity
        )
        self.trade_history['current_equity'] = current_equity
        self._save_trade_history()
    
    def add_trade_record(self, trade: Dict):
        """添加交易记录"""
        trade['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.trade_history['trades'].append(trade)
        
        # 只保留最近1000条记录
        if len(self.trade_history['trades']) > 1000:
            self.trade_history['trades'] = self.trade_history['trades'][-1000:]
        
        self._save_trade_history()
    
    def generate_risk_report(self,
                            positions: List[Dict],
                            account_equity: float,
                            date: Optional[str] = None) -> str:
        """
        生成风控报告
        
        Args:
            positions: 持仓列表
            account_equity: 账户总资金
            date: 日期
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        risk = self.check_portfolio_risk(positions, account_equity)
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 智能风控报告 - {date}")
        report.append(f"{'='*60}")
        report.append("")
        
        # 账户概览
        report.append(f"💰 账户概览:")
        report.append(f"   总资金: {account_equity:,.2f}元")
        report.append(f"   持仓市值: {risk['total_value']:,.2f}元")
        report.append(f"   总仓位: {risk['total_position_ratio']:.1f}%")
        report.append(f"   浮动盈亏: {risk['total_pnl']:,.2f}元")
        report.append("")
        
        # 风险评级
        report.append(f"🎯 风险评级: {risk['risk_level']} (得分:{risk['risk_score']})")
        report.append(f"   建议: {risk['suggestion']}")
        report.append("")
        
        # 当前回撤
        report.append(f"📉 当前回撤: {risk['current_drawdown']:.2f}%")
        if risk['drawdown_alert']:
            report.append(f"   ⚠️ {risk['drawdown_alert']}")
        report.append("")
        
        # 仓位提醒
        if risk['position_alerts']:
            report.append(f"⚠️ 仓位超限提醒:")
            for alert in risk['position_alerts']:
                report.append(f"   {alert['name']}({alert['code']}): {alert['ratio']}%")
            report.append("")
        
        if risk['total_position_alert']:
            report.append(f"⚠️ {risk['total_position_alert']}")
            report.append("")
        
        # 持仓明细
        if positions:
            report.append(f"📋 持仓明细 ({len(positions)}只)")
            report.append("-"*50)
            for pos in positions:
                ratio = pos.get('market_value', 0) / account_equity * 100
                pnl = pos.get('unrealized_pnl', 0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                
                flag = "🔴" if ratio > self.max_position_per_stock * 100 else ""
                pnl_str = f"+{pnl:.0f}" if pnl >= 0 else f"{pnl:.0f}"
                
                report.append(f"  {flag}{pos.get('name','未知')}({pos.get('code','')})")
                report.append(f"    持仓: {ratio:.1f}% | 盈亏: {pnl_str}元({pnl_pct:+.1f}%)")
            report.append("")
        
        # 凯利公式建议
        report.append(f"{'='*60}")
        report.append("📐 凯利公式仓位计算")
        report.append("-"*50)
        
        # 示例：假设胜率55%，平均盈利8%，平均亏损3%
        kelly_pos = self.calculate_kelly_position(
            win_rate=0.55,
            avg_win=0.08,
            avg_loss=0.03,
            kelly_fraction=0.5
        )
        report.append(f"  假设胜率55%，盈亏比2.67:1")
        report.append(f"  凯利最优仓位: {kelly_pos*100:.1f}%（半凯利保守）")
        report.append(f"  建议实际仓位: {min(kelly_pos*100, 20):.1f}%")
        
        report.append("")
        report.append(f"{'='*60}")
        
        return "\n".join(report)


def main():
    """命令行入口"""
    manager = RiskManager()
    
    # 模拟持仓
    positions = [
        {'code': '000001', 'name': '平安银行', 'market_value': 30000, 'unrealized_pnl': 500, 'unrealized_pnl_pct': 1.7},
        {'code': '600519', 'name': '贵州茅台', 'market_value': 50000, 'unrealized_pnl': -1000, 'unrealized_pnl_pct': -2.0},
    ]
    
    account_equity = 200000
    report = manager.generate_risk_report(positions, account_equity)
    print(report)


if __name__ == '__main__':
    main()
