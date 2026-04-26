# -*- coding: utf-8 -*-
"""
北向资金追踪模块 - North Money Tracker
追踪沪深港通北向资金流向、外资重仓股、外资抄底逃顶信号

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from collections import defaultdict


class NorthMoneyTracker:
    """北向资金追踪器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 历史数据
        self.history_file = self.data_dir / 'north_money_history.json'
        self.history = self._load_history()
        
        # 外资重仓门槛
        self.heavy_position_threshold = 1000000000  # 10亿持仓
    
    def _load_history(self) -> Dict:
        """加载历史北向资金数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'daily': {}, 'stock_holdings': defaultdict(dict)}
    
    def _save_history(self):
        """保存北向资金历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def get_daily_flow(self, date: Optional[str] = None) -> Dict:
        """
        获取北向资金每日流向
        
        Args:
            date: 日期，默认今日
        
        Returns:
            北向资金流向数据
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        print(f"[{date}] 获取北向资金数据...")
        
        # TODO: 调用数据源API获取北向资金数据
        # 可以使用 akshare 的 hsgt capital flow 接口
        # 或者妙想/问财的沪深港通数据
        
        return {
            'date': date,
            'north_net_inflow': 0,  # 北向净流入（亿元）
            'north_buy_amount': 0,
            'north_sell_amount': 0,
            'shanghai_connect_net': 0,  # 沪股通净流入
            'shenzhen_connect_net': 0,  # 深股通净流入
        }
    
    def update_history(self, flow_data: Dict):
        """更新历史数据"""
        date = flow_data['date']
        self.history['daily'][date] = flow_data
        
        # 只保留最近90天
        dates = sorted(self.history['daily'].keys())
        if len(dates) > 90:
            for old_date in dates[:-90]:
                del self.history['daily'][old_date]
        
        self._save_history()
    
    def analyze_flow_trend(self, days: int = 5) -> Dict:
        """
        分析北向资金趋势
        
        Args:
            days: 分析天数
        
        Returns:
            趋势分析结果
        """
        dates = sorted(self.history['daily'].keys(), reverse=True)[:days]
        
        if len(dates) < 2:
            return {
                'trend': 'UNKNOWN',
                'interpretation': '数据不足'
            }
        
        net_flows = [self.history['daily'][d].get('north_net_inflow', 0) for d in dates]
        
        # 计算趋势
        recent_avg = sum(net_flows[:len(net_flows)//2+1]) / max(len(net_flows)//2+1, 1)
        older_avg = sum(net_flows[len(net_flows)//2:]) / max(len(net_flows)//2, 1)
        
        if recent_avg > older_avg * 1.5 and recent_avg > 0:
            trend = 'ACCELERATE_INFLOW'  # 加速流入
            interpretation = '外资加速买入，积极看多'
        elif recent_avg > older_avg and recent_avg > 0:
            trend = 'GRADUAL_INFLOW'  # 逐步流入
            interpretation = '外资持续买入，稳健看多'
        elif recent_avg < older_avg * 0.5 and recent_avg < 0:
            trend = 'ACCELERATE_OUTFLOW'  # 加速流出
            interpretation = '外资加速卖出，谨慎观望'
        elif recent_avg < older_avg and recent_avg < 0:
            trend = 'GRADUAL_OUTFLOW'  # 逐步流出
            interpretation = '外资持续卖出，轻仓观望'
        elif recent_avg > 0:
            trend = 'BUYING'
            interpretation = '外资净买入'
        else:
            trend = 'NEUTRAL'
            interpretation = '外资观望为主'
        
        return {
            'trend': trend,
            'recent_avg': round(recent_avg, 2),
            'older_avg': round(older_avg, 2),
            'interpretation': interpretation,
            'days': len(dates),
            'net_flows': net_flows
        }
    
    def get_top_holdings(self, date: Optional[str] = None) -> List[Dict]:
        """
        获取外资重仓股排行
        
        Args:
            date: 日期，默认今日
        
        Returns:
            外资重仓股列表
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # TODO: 调用数据源获取外资持股数据
        # 可以用 akshare: akshare.stock.hsgt_stock_rank_latest()
        
        return []
    
    def identify_bottom_fishing_signal(self,
                                       stock_code: str,
                                       north_net_inflow_pct: float,
                                       price_change: float,
                                       historical_avg_net: float) -> Optional[Dict]:
        """
        识别外资抄底信号
        
        Args:
            stock_code: 股票代码
            north_net_inflow_pct: 北向净流入占比
            price_change: 股价涨跌
            historical_avg_net: 历史平均净流入
        
        Returns:
            抄底信号
        """
        # 抄底条件：
        # 1. 股价下跌（负面信号，但外资逆势买入）
        # 2. 北向净流入远超历史平均
        # 3. 净流入占比高（说明外资在买入）
        
        if price_change >= 0:
            return None  # 股价没跌，不是抄底
        
        # 外资大幅净买入信号
        if north_net_inflow_pct > historical_avg_net * 2 and north_net_inflow_pct > 5:
            return {
                'code': stock_code,
                'signal': 'BOTTOM_FISHING',
                'action': '买入',
                'confidence': 'HIGH' if north_net_inflow_pct > historical_avg_net * 3 else 'MEDIUM',
                'reason': f'外资逆势加仓，净流入占比{north_net_inflow_pct:.1f}%，远超历史平均{historical_avg_net:.1f}%',
                'price_change': price_change,
                'north_net_inflow_pct': north_net_inflow_pct
            }
        
        return None
    
    def identify_top_escape_signal(self,
                                  stock_code: str,
                                  north_net_outflow_pct: float,
                                  price_change: float,
                                  historical_avg_net: float) -> Optional[Dict]:
        """
        识别外资逃顶信号
        
        Args:
            stock_code: 股票代码
            north_net_outflow_pct: 北向净流出占比
            price_change: 股价涨跌
            historical_avg_net: 历史平均净流入
        
        Returns:
            逃顶信号
        """
        # 逃顶条件：
        # 1. 股价上涨（多头行情）
        # 2. 外资反而净卖出（背离）
        
        if price_change <= 0:
            return None  # 股价没涨，不算逃顶
        
        # 外资逆势卖出信号
        if north_net_outflow_pct > abs(historical_avg_net) * 2 and north_net_outflow_pct > 5:
            return {
                'code': stock_code,
                'signal': 'TOP_ESCAPE',
                'action': '卖出',
                'confidence': 'HIGH' if north_net_outflow_pct > abs(historical_avg_net) * 3 else 'MEDIUM',
                'reason': f'外资高位减仓，净流出占比{north_net_outflow_pct:.1f}%，警惕！',
                'price_change': price_change,
                'north_net_outflow_pct': north_net_outflow_pct
            }
        
        return None
    
    def generate_north_money_report(self,
                                   date: Optional[str] = None) -> str:
        """
        生成北向资金报告
        
        Args:
            date: 日期
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 获取当日数据
        flow = self.get_daily_flow(date)
        self.update_history(flow)
        
        # 分析趋势
        trend = self.analyze_flow_trend(5)
        
        # 获取外资重仓
        top_holdings = self.get_top_holdings(date)
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 北向资金追踪报告 - {date}")
        report.append(f"{'='*60}")
        report.append("")
        
        # 今日流向
        report.append(f"💰 今日北向资金:")
        report.append(f"   净流入: {flow['north_net_inflow']:.2f}亿元")
        report.append(f"   买入: {flow['north_buy_amount']:.2f}亿元")
        report.append(f"   卖出: {flow['north_sell_amount']:.2f}亿元")
        report.append("")
        
        # 沪股通/深股通
        report.append(f"📈 沪深港通分布:")
        report.append(f"   沪股通: {flow['shanghai_connect_net']:.2f}亿元")
        report.append(f"   深股通: {flow['shenzhen_connect_net']:.2f}亿元")
        report.append("")
        
        # 趋势分析
        report.append(f"🔍 5日趋势分析:")
        report.append(f"   趋势: {trend.get('interpretation', 'N/A')}")
        report.append(f"   近几日平均: {trend.get('recent_avg', 0):.2f}亿元")
        report.append("")
        
        # 外资重仓
        if top_holdings:
            report.append(f"🏆 外资重仓股 TOP10:")
            report.append("-"*50)
            for i, stock in enumerate(top_holdings[:10], 1):
                report.append(f"  {i}. {stock.get('name', '')}({stock.get('code', '')})")
                report.append(f"     持仓: {stock.get('hold_amount', 0):.2f}亿元")
                report.append(f"     持股占比: {stock.get('hold_ratio', 0):.2f}%")
            report.append("")
        
        # 操作建议
        report.append(f"{'='*60}")
        report.append("📋 操作建议")
        report.append("-"*50)
        
        trend_type = trend.get('trend', 'NEUTRAL')
        if 'INFLOW' in trend_type:
            report.append("✅ 外资持续净买入，积极参与")
            report.append("   建议：跟随外资布局优质龙头股")
        elif 'OUTFLOW' in trend_type:
            report.append("⚠️ 外资净卖出，谨慎观望")
            report.append("   建议：降低仓位，规避外资重仓股")
        else:
            report.append("⚖️ 外资中性，等待信号")
            report.append("   建议：轻仓观望")
        
        report.append("")
        report.append(f"{'='*60}")
        
        return "\n".join(report)


def main():
    """命令行入口"""
    tracker = NorthMoneyTracker()
    
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    report = tracker.generate_north_money_report(date)
    print(report)


if __name__ == '__main__':
    main()
