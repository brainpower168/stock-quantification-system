# -*- coding: utf-8 -*-
"""
涨停板接力追踪模块 - LimitUp Tracker
追踪连板股、识别龙头、捕捉跟风机会

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# 尝试导入数据源
try:
    from .data_sources import WenCaiDataSource, MxDataSource
    HAS_DATA_SOURCE = True
except ImportError:
    HAS_DATA_SOURCE = False


class LimitUpTracker:
    """涨停板接力追踪器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据源
        if HAS_DATA_SOURCE:
            self.wencai = WenCaiDataSource()
            self.mx = MxDataSource()
        else:
            self.wencai = None
            self.mx = None
        
        # 连板股历史缓存
        self.history_file = self.data_dir / 'limit_up_history.json'
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """加载历史连板数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_history(self):
        """保存连板历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def scan_limit_up_stocks(self, date: Optional[str] = None) -> List[Dict]:
        """
        扫描当日涨停股
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认今日
        
        Returns:
            涨停股列表
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        print(f"[{date}] 扫描涨停股...")
        
        # 使用问财API查询涨停股
        if self.wencai:
            query = f"今日涨停股，日期{date}"
            result = self.wencai.query(query)
            if result:
                return self._parse_limit_up_result(result)
        
        # 备用：使用妙想查询
        if self.mx:
            result = self.mx.query(f"今日涨停股 {date}")
            if result:
                return self._parse_limit_up_result(result)
        
        return []
    
    def _parse_limit_up_result(self, result: str) -> List[Dict]:
        """解析涨停股查询结果"""
        stocks = []
        lines = result.strip().split('\n')
        
        for line in lines:
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) >= 4:
                stock = {
                    'name': parts[0].strip(),
                    'code': parts[1].strip(),
                    'price': float(parts[2].strip()) if parts[2].strip() else 0,
                    'change_pct': float(parts[3].strip().replace('%','')) if len(parts) > 3 else 10.0,
                    'volume_ratio': float(parts[4].strip()) if len(parts) > 4 else 0,
                    'turnover': float(parts[5].strip()) if len(parts) > 5 else 0,
                }
                stocks.append(stock)
        
        return stocks
    
    def identify_consecutive_limit_up(self, stocks: List[Dict], date: str) -> List[Dict]:
        """
        识别连板股（2板以上）
        
        Args:
            stocks: 当日涨停股列表
            date: 日期
        
        Returns:
            连板股列表（附加连板天数）
        """
        consecutive = []
        
        for stock in stocks:
            code = stock['code']
            
            # 查找历史记录
            key = f"{code}_{stock['name']}"
            if key not in self.history:
                self.history[key] = {'dates': [], 'prices': []}
            
            history = self.history[key]
            
            # 检查是否昨日也涨停
            yesterday = self._get_yesterday(date)
            if yesterday in history['dates']:
                # 昨日涨停，计算连板天数
                idx = history['dates'].index(yesterday)
                consecutive_days = len(history['dates']) - idx + 1
                stock['consecutive_days'] = consecutive_days
                stock['first_limit_up_date'] = history['dates'][idx]
            else:
                # 新首板
                stock['consecutive_days'] = 1
                stock['first_limit_up_date'] = date
                # 清理旧历史，只保留最近30天
                history['dates'] = []
                history['prices'] = []
            
            # 更新历史
            history['dates'].append(date)
            history['prices'].append(stock['price'])
            
            # 评分
            stock['quality_score'] = self._score_limit_up(stock)
            
            consecutive.append(stock)
        
        # 保存历史
        self._save_history()
        
        # 按连板天数和评分排序
        consecutive.sort(key=lambda x: (x.get('consecutive_days', 0), x.get('quality_score', 0)), reverse=True)
        
        return consecutive
    
    def _get_yesterday(self, date: str) -> str:
        """获取指定日期的前一个交易日"""
        from datetime import timedelta
        d = datetime.datetime.strptime(date, '%Y-%m-%d')
        d -= timedelta(days=1)
        
        # 简单处理：往前减1天（实际应该跳过周末）
        return d.strftime('%Y-%m-%d')
    
    def _score_limit_up(self, stock: Dict) -> float:
        """
        评估涨停股质量
        
        评分维度：
        - 连板天数（越高越好）
        - 换手率（适中最好，5%-20%）
        - 量比（>1.5较好）
        - 流通市值（中小盘更好）
        """
        score = 0.0
        
        # 连板天数得分（最高40分）
        consecutive = stock.get('consecutive_days', 1)
        score += min(consecutive * 10, 40)
        
        # 换手率得分（最高30分）
        turnover = stock.get('turnover', 0)
        if 5 <= turnover <= 20:
            score += 30
        elif turnover < 5:
            score += turnover * 3
        elif turnover <= 50:
            score += max(30 - (turnover - 20) * 0.5, 10)
        else:
            score += 5
        
        # 量比得分（最高20分）
        volume_ratio = stock.get('volume_ratio', 0)
        if volume_ratio >= 2:
            score += 20
        elif volume_ratio >= 1.5:
            score += 15
        elif volume_ratio >= 1:
            score += 10
        else:
            score += 5
        
        # 成交额得分（最高10分）
        # 10亿以下中小盘加分
        # 这个字段可能没有，预留
        score += 10
        
        return round(score, 2)
    
    def filter_follow_stocks(self, limit_up_stocks: List[Dict], 
                           market_data: Dict[str, Dict]) -> List[Dict]:
        """
        筛选跟风股（涨停股同板块的跟风标的）
        
        Args:
            limit_up_stocks: 涨停股列表（龙头）
            market_data: 市场数据（包含板块信息）
        
        Returns:
            跟风股列表
        """
        follow_stocks = []
        
        for leader in limit_up_stocks:
            leader_code = leader['code']
            leader_board = market_data.get(leader_code, {}).get('board', '')
            
            if not leader_board:
                continue
            
            # 找同板块的股票
            for code, data in market_data.items():
                if code == leader_code:
                    continue
                
                if data.get('board', '') == leader_board:
                    # 同板块，判断涨幅和资金流向
                    change_pct = data.get('change_pct', 0)
                    ddx = data.get('ddx', 0)
                    
                    # 跟风条件：涨幅3%-8%，DDX为正
                    if 3 <= change_pct < 10 and ddx > 0:
                        follow_stocks.append({
                            'code': code,
                            'name': data.get('name', ''),
                            'leader_code': leader_code,
                            'leader_name': leader['name'],
                            'change_pct': change_pct,
                            'ddx': ddx,
                            'board': leader_board,
                            'reason': f"跟风{leader['name']}涨停"
                        })
        
        # 按涨幅排序
        follow_stocks.sort(key=lambda x: x['change_pct'], reverse=True)
        
        return follow_stocks[:20]  # 最多返回20只
    
    def get_trading_signals(self, consecutive_stocks: List[Dict], 
                           real_time_data: Dict[str, Dict]) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            consecutive_stocks: 连板股列表
            real_time_data: 实时行情数据
        
        Returns:
            交易信号列表
        """
        signals = []
        
        for stock in consecutive_stocks:
            code = stock['code']
            data = real_time_data.get(code, {})
            
            consecutive_days = stock.get('consecutive_days', 1)
            score = stock.get('quality_score', 0)
            
            # === 买入信号 ===
            if consecutive_days == 2:
                # 二板：可追，但控制仓位
                signal = {
                    'code': code,
                    'name': stock['name'],
                    'action': 'BUY',
                    'consecutive_days': consecutive_days,
                    'quality_score': score,
                    'position': 'MINI',  # 迷你仓
                    'reason': f"2板接力，{stock.get('reason', '')}",
                    'stop_loss': data.get('price', 0) * 0.97,  # -3%止损
                    'target': data.get('price', 0) * 1.05,      # +5%目标
                }
                signals.append(signal)
                
            elif consecutive_days == 3:
                # 三板：高风险，观望或极轻仓
                signal = {
                    'code': code,
                    'name': stock['name'],
                    'action': 'WATCH',
                    'consecutive_days': consecutive_days,
                    'quality_score': score,
                    'position': 'NONE',
                    'reason': f"3板{stock.get('reason', '')}，高位震荡，风险较大",
                    'stop_loss': data.get('price', 0) * 0.95,
                    'target': data.get('price', 0) * 1.03,
                }
                signals.append(signal)
                
            elif consecutive_days >= 4:
                # 4板以上：妖股，不建议追
                signal = {
                    'code': code,
                    'name': stock['name'],
                    'action': 'AVOID',
                    'consecutive_days': consecutive_days,
                    'quality_score': score,
                    'position': 'NONE',
                    'reason': f"{consecutive_days}板妖股，风险极高，不建议追",
                }
                signals.append(signal)
            
            # === 断板卖出信号 ===
            # 如果昨日涨停，今日涨幅<9.5%，视为断板
            yesterday_change = data.get('yesterday_change_pct', 0)
            today_change = data.get('change_pct', 0)
            
            if yesterday_change >= 9.5 and today_change < 9.5:
                signal = {
                    'code': code,
                    'name': stock['name'],
                    'action': 'SELL',
                    'consecutive_days': consecutive_days,
                    'reason': f"断板！昨日涨停{consecutive_days}天，今日涨幅{today_change:.1f}%，立即卖出",
                    'priority': 'HIGH',
                }
                signals.append(signal)
        
        return signals
    
    def generate_report(self, date: Optional[str] = None) -> str:
        """
        生成涨停板追踪报告
        
        Args:
            date: 日期，默认今日
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 扫描涨停股
        all_limit_up = self.scan_limit_up_stocks(date)
        
        if not all_limit_up:
            return f"[{date}] 今日无涨停股数据"
        
        # 识别连板股
        consecutive = self.identify_consecutive_limit_up(all_limit_up, date)
        
        # 分类
        two_board = [s for s in consecutive if s.get('consecutive_days') == 2]
        three_board = [s for s in consecutive if s.get('consecutive_days') == 3]
        more_board = [s for s in consecutive if s.get('consecutive_days', 0) >= 4]
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 涨停板追踪报告 - {date}")
        report.append(f"{'='*60}")
        report.append(f"今日涨停总数: {len(all_limit_up)}")
        report.append(f"连板股数量: {len(consecutive)}")
        report.append("")
        
        # 2板股
        if two_board:
            report.append(f"📈 2板股 ({len(two_board)}只) - 可轻仓追入")
            report.append("-"*50)
            for s in two_board:
                report.append(f"  {s['name']}({s['code']}) 评分:{s.get('quality_score',0):.1f} {s.get('reason','')}")
            report.append("")
        
        # 3板股
        if three_board:
            report.append(f"⚠️ 3板股 ({len(three_board)}只) - 观望为主")
            report.append("-"*50)
            for s in three_board:
                report.append(f"  {s['name']}({s['code']}) 评分:{s.get('quality_score',0):.1f} {s.get('reason','')}")
            report.append("")
        
        # 4板+
        if more_board:
            report.append(f"🚫 4板+妖股 ({len(more_board)}只) - 坚决不追")
            report.append("-"*50)
            for s in more_board:
                report.append(f"  {s['name']}({s['code']}) {s.get('consecutive_days')}连板 评分:{s.get('quality_score',0):.1f}")
            report.append("")
        
        # 操作建议
        report.append(f"{'='*60}")
        report.append("📋 今日操作建议")
        report.append("-"*50)
        
        if two_board:
            best = two_board[0]
            report.append(f"🔥 最佳标的: {best['name']}({best['code']}) 2板接力")
            report.append(f"   评分: {best.get('quality_score',0):.1f}/100")
            report.append(f"   仓位建议: 迷你仓（≤10%）")
            report.append(f"   止损: -3%")
            report.append(f"   目标: +5%")
        
        if more_board:
            worst = more_board[0]
            report.append(f"⛔ 规避标的: {worst['name']}({worst['code']}) {worst.get('consecutive_days')}连板")
            report.append("   妖股高位，坚决不追！")
        
        report.append("")
        report.append(f"{'='*60}")
        
        return "\n".join(report)


def main():
    """命令行入口"""
    tracker = LimitUpTracker()
    
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    report = tracker.generate_report(date)
    print(report)


if __name__ == '__main__':
    main()
