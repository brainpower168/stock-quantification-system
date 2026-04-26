# -*- coding: utf-8 -*-
"""
增强版回测引擎 - Enhanced Backtest Engine
支持T+1规则、手续费、滑点模拟、多策略对比回测

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Trade:
    """交易记录"""
    date: str
    action: str  # BUY / SELL
    code: str
    name: str
    price: float
    shares: int
    amount: float
    commission: float = 0  # 手续费
    slippage: float = 0  # 滑点


@dataclass
class Position:
    """持仓"""
    code: str
    name: str
    shares: int
    avg_price: float
    buy_date: str


@dataclass
class BacktestResult:
    """回测结果"""
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    total_return: float = 0
    max_drawdown: float = 0
    sharpe_ratio: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    profit_loss_ratio: float = 0
    holding_days: int = 0


class BacktestEngine:
    """增强版回测引擎"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 交易参数
        self.initial_capital = self.config.get('initial_capital', 1000000)  # 初始资金100万
        self.commission_rate = self.config.get('commission_rate', 0.0003)  # 佣金万3
        self.stamp_tax_rate = self.config.get('stamp_tax_rate', 0.001)  # 印花税千1（卖出时）
        self.slippage_rate = self.config.get('slippage_rate', 0.001)  # 滑点千1
        
        # 账户状态
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
        # 持仓限制
        self.max_stocks = self.config.get('max_stocks', 10)  # 最多持仓10只
        self.max_position_per_stock = self.config.get('max_position_per_stock', 0.2)  # 单票最大20%
    
    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
    
    def _calculate_commission(self, amount: float, is_sell: bool = False) -> float:
        """计算手续费"""
        # 佣金（最低5元）
        commission = max(amount * self.commission_rate, 5)
        
        # 印花税（仅卖出）
        if is_sell:
            commission += amount * self.stamp_tax_rate
        
        return commission
    
    def _apply_slippage(self, price: float, is_buy: bool = True) -> float:
        """应用滑点"""
        if is_buy:
            return price * (1 + self.slippage_rate)  # 买入滑点
        else:
            return price * (1 - self.slippage_rate)  # 卖出滑点
    
    def _calculate_equity(self, prices: Dict[str, float], date: str) -> float:
        """计算当前总权益"""
        position_value = sum(
            pos.shares * prices.get(pos.code, pos.avg_price)
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def buy(self, 
            date: str,
            code: str, 
            name: str, 
            price: float, 
            shares: int,
            max_shares: Optional[int] = None):
        """
        买入
        
        Args:
            date: 交易日期
            code: 股票代码
            name: 股票名称
            price: 买入价格
            shares: 买入股数（必须是100的倍数）
            max_shares: 最大持股数（用于仓位控制）
        """
        # T+1检查：今日不能卖
        if code in self.positions:
            print(f"[{date}] {code} 今日买入，需T+1后才能卖出")
        
        # 整手检查
        shares = (shares // 100) * 100
        if shares <= 0:
            return False
        
        # 应用滑点
        buy_price = self._apply_slippage(price, is_buy=True)
        
        # 计算金额和费用
        amount = shares * buy_price
        commission = self._calculate_commission(amount, is_sell=False)
        total_cost = amount + commission
        
        # 资金检查
        if total_cost > self.cash:
            # 资金不足，按最大可买计算
            max_cost = self.cash * 0.98  # 预留手续费
            shares = int(max_cost / (buy_price * 100)) * 100
            if shares < 100:
                return False
            amount = shares * buy_price
            commission = self._calculate_commission(amount, is_sell=False)
            total_cost = amount + commission
        
        # 仓位检查
        equity = self._calculate_equity({code: buy_price}, date)
        position_ratio = (shares * buy_price) / equity if equity > 0 else 0
        
        if max_shares and position_ratio > max_shares:
            # 超过最大仓位，按最大仓位计算
            shares = int(equity * max_shares / buy_price / 100) * 100
            if shares < 100:
                return False
            amount = shares * buy_price
            commission = self._calculate_commission(amount, is_sell=False)
            total_cost = amount + commission
        
        # 执行买入
        self.cash -= total_cost
        
        if code in self.positions:
            # 补仓：重新计算均价
            old_pos = self.positions[code]
            total_shares = old_pos.shares + shares
            total_cost = old_pos.shares * old_pos.avg_price + shares * buy_price
            avg_price = total_cost / total_shares
            self.positions[code] = Position(
                code=code,
                name=name,
                shares=total_shares,
                avg_price=avg_price,
                buy_date=old_pos.buy_date  # 保持最初买入日期
            )
        else:
            self.positions[code] = Position(
                code=code,
                name=name,
                shares=shares,
                avg_price=buy_price,
                buy_date=date
            )
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            action='BUY',
            code=code,
            name=name,
            price=buy_price,
            shares=shares,
            amount=amount,
            commission=commission,
            slippage=buy_price - price
        ))
        
        return True
    
    def sell(self, 
             date: str,
             code: str, 
             price: float, 
             shares: Optional[int] = None,
             sell_all: bool = True):
        """
        卖出
        
        Args:
            date: 交易日期
            code: 股票代码
            price: 卖出价格
            shares: 卖出股数（None表示全部卖出）
            sell_all: 是否全部卖出
        """
        if code not in self.positions:
            return False
        
        pos = self.positions[code]
        
        # T+1检查
        if pos.buy_date == date:
            print(f"[{date}] {code} 今日买入，T+1规则不能卖出")
            return False
        
        # 确定卖出数量
        if sell_all or shares is None:
            shares = pos.shares
        else:
            shares = min(shares, pos.shares)
        
        # 整手检查
        shares = (shares // 100) * 100
        if shares <= 0:
            return False
        
        # 应用滑点
        sell_price = self._apply_slippage(price, is_buy=False)
        
        # 计算金额和费用
        amount = shares * sell_price
        commission = self._calculate_commission(amount, is_sell=True)
        net_amount = amount - commission
        
        # 执行卖出
        self.cash += net_amount
        
        # 更新持仓
        if shares >= pos.shares:
            del self.positions[code]
        else:
            pos.shares -= shares
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            action='SELL',
            code=code,
            name=pos.name,
            price=sell_price,
            shares=shares,
            amount=amount,
            commission=commission,
            slippage=price - sell_price
        ))
        
        return True
    
    def run_backtest(self,
                     signals: List[Dict],
                     prices: Dict[str, Dict[str, float]],
                     start_date: str,
                     end_date: str) -> BacktestResult:
        """
        运行回测
        
        Args:
            signals: 交易信号列表，每项包含 date, code, name, action, price
            prices: 价格数据，格式 {code: {date: price}}
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            回测结果
        """
        self.reset()
        
        # 按日期排序信号
        signals.sort(key=lambda x: x['date'])
        
        # 逐日回测
        dates = sorted(set(s['date'] for s in signals 
                         if start_date <= s['date'] <= end_date))
        
        for date in dates:
            # 获取当日价格
            day_prices = {
                code: price_data.get(date, 0)
                for code, price_data in prices.items()
            }
            
            # 执行当日信号
            for signal in signals:
                if signal['date'] != date:
                    continue
                
                code = signal['code']
                price = day_prices.get(code, signal.get('price', 0))
                
                if price <= 0:
                    continue
                
                if signal['action'] == 'BUY':
                    shares = signal.get('shares', 100)
                    self.buy(date, code, signal.get('name', code), price, shares,
                            max_shares=self.max_position_per_stock)
                
                elif signal['action'] == 'SELL':
                    self.sell(date, code, price, sell_all=signal.get('sell_all', True))
            
            # 更新权益曲线
            equity = self._calculate_equity(day_prices, date)
            self.equity_curve.append({
                'date': date,
                'equity': equity,
                'cash': self.cash,
                'position_value': equity - self.cash
            })
        
        # 计算结果
        return self._calculate_result()
    
    def _calculate_result(self) -> BacktestResult:
        """计算回测结果"""
        if not self.trades:
            return BacktestResult()
        
        # 统计交易
        sells = [t for t in self.trades if t.action == 'SELL']
        
        win_trades = 0
        loss_trades = 0
        total_pnl = 0
        total_win = 0
        total_loss = 0
        total_holding_days = 0
        
        # 配对买卖计算盈亏
        buy_info = {}
        for trade in self.trades:
            if trade.action == 'BUY':
                buy_info[trade.code] = trade
            elif trade.action == 'SELL':
                if trade.code in buy_info:
                    buy_trade = buy_info[trade.code]
                    pnl = (trade.price - buy_trade.price) * trade.shares - trade.commission
                    total_pnl += pnl
                    
                    if pnl > 0:
                        win_trades += 1
                        total_win += pnl
                    else:
                        loss_trades += 1
                        total_loss += abs(pnl)
                    
                    # 持仓天数
                    buy_date = datetime.datetime.strptime(buy_trade.date, '%Y-%m-%d')
                    sell_date = datetime.datetime.strptime(trade.date, '%Y-%m-%d')
                    total_holding_days += (sell_date - buy_date).days
        
        # 计算各项指标
        total_trades = win_trades + loss_trades
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_return = total_pnl / self.initial_capital if self.initial_capital > 0 else 0
        
        avg_win = total_win / win_trades if win_trades > 0 else 0
        avg_loss = total_loss / loss_trades if loss_trades > 0 else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 最大回撤
        peak = 0
        max_drawdown = 0
        for item in self.equity_curve:
            equity = item['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        # 夏普比率（简化版）
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                ret = (self.equity_curve[i]['equity'] - self.equity_curve[i-1]['equity']) / self.equity_curve[i-1]['equity']
                returns.append(ret)
            
            if returns:
                avg_ret = sum(returns) / len(returns)
                std_ret = (sum((r - avg_ret) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = (avg_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return BacktestResult(
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_loss_ratio=profit_loss_ratio,
            holding_days=int(total_holding_days / total_trades) if total_trades > 0 else 0
        )
    
    def compare_strategies(self, 
                         strategy_results: Dict[str, BacktestResult]) -> str:
        """
        对比多策略回测结果
        
        Args:
            strategy_results: 策略名 -> 回测结果
        
        Returns:
            对比报告
        """
        report = []
        report.append("="*70)
        report.append("📊 多策略回测对比报告")
        report.append("="*70)
        report.append("")
        
        # 表头
        report.append(f"{'策略':<20} {'总交易':>8} {'胜率':>8} {'总收益':>10} {'最大回撤':>10} {'夏普比率':>10}")
        report.append("-"*70)
        
        best_sharpe = None
        best_return = None
        
        for name, result in strategy_results.items():
            report.append(
                f"{name:<20} "
                f"{result.total_trades:>8} "
                f"{result.win_rate*100:>7.1f}% "
                f"{result.total_return*100:>9.1f}% "
                f"{result.max_drawdown*100:>9.1f}% "
                f"{result.sharpe_ratio:>10.2f}"
            )
            
            if best_sharpe is None or result.sharpe_ratio > strategy_results[best_sharpe].sharpe_ratio:
                best_sharpe = name
            if best_return is None or result.total_return > strategy_results[best_return].total_return:
                best_return = name
        
        report.append("")
        
        # 最佳策略
        report.append(f"🏆 收益最高: {best_return}")
        report.append(f"📈 夏普比最优: {best_sharpe}")
        
        report.append("")
        report.append("="*70)
        
        return "\n".join(report)
    
    def generate_report(self, result: BacktestResult) -> str:
        """生成详细回测报告"""
        report = []
        report.append("="*60)
        report.append("📊 回测报告")
        report.append("="*60)
        report.append("")
        
        # 基础统计
        report.append("📈 基础统计:")
        report.append(f"   初始资金: {self.initial_capital:,.2f}元")
        report.append(f"   总交易次数: {result.total_trades}")
        report.append(f"   盈利交易: {result.win_trades}")
        report.append(f"   亏损交易: {result.loss_trades}")
        report.append(f"   胜率: {result.win_rate*100:.2f}%")
        report.append("")
        
        # 收益统计
        report.append("💰 收益统计:")
        report.append(f"   总盈亏: {result.total_pnl:+,.2f}元")
        report.append(f"   总收益率: {result.total_return*100:+.2f}%")
        report.append(f"   平均盈利: {result.avg_win:+,.2f}元")
        report.append(f"   平均亏损: {result.avg_loss:-,.2f}元")
        report.append(f"   盈亏比: {result.profit_loss_ratio:.2f}")
        report.append("")
        
        # 风险统计
        report.append("⚠️ 风险统计:")
        report.append(f"   最大回撤: {result.max_drawdown*100:.2f}%")
        report.append(f"   夏普比率: {result.sharpe_ratio:.2f}")
        report.append(f"   平均持仓天数: {result.holding_days}天")
        report.append("")
        
        # 综合评级
        score = 0
        if result.win_rate > 0.5:
            score += 25
        if result.profit_loss_ratio > 1.5:
            score += 25
        if result.max_drawdown < 0.15:
            score += 25
        if result.sharpe_ratio > 1:
            score += 25
        
        if score >= 75:
            grade = "A 优秀"
        elif score >= 50:
            grade = "B 良好"
        elif score >= 25:
            grade = "C 一般"
        else:
            grade = "D 较差"
        
        report.append("🎯 综合评级:")
        report.append(f"   得分: {score}/100 ({grade})")
        report.append("")
        
        report.append("="*60)
        
        return "\n".join(report)


def main():
    """命令行入口"""
    engine = BacktestEngine()
    
    print("增强版回测引擎已初始化")
    print(f"初始资金: {engine.initial_capital:,.2f}元")
    print(f"佣金: {engine.commission_rate*100:.2f}%")
    print(f"印花税: {engine.stamp_tax_rate*100:.2f}%")


if __name__ == '__main__':
    main()
