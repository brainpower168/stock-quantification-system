# -*- coding: utf-8 -*-
"""
龙虎榜追踪模块 - Long Horn Billboard Tracker
追踪龙虎榜数据、识别机构席位、挖掘机构动向

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class LhbTracker:
    """龙虎榜追踪器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 龙虎榜历史
        self.history_file = self.data_dir / 'lhb_history.json'
        self.history = self._load_history()
        
        # 机构席位识别
        self.institutional_seats = [
            '机构专用',
            '沪股通专用',
            '深股通专用',
            'QFII',
            'RQFII',
            '保险资金',
            '社保基金',
            '公募基金',
            '私募基金',
        ]
    
    def _load_history(self) -> Dict:
        """加载龙虎榜历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_history(self):
        """保存龙虎榜历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def scan_lhb(self, date: Optional[str] = None) -> List[Dict]:
        """
        扫描龙虎榜数据
        
        Args:
            date: 日期，默认今日
        
        Returns:
            龙虎榜股票列表
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        print(f"[{date}] 扫描龙虎榜...")
        
        # 这里需要调用数据源API
        # 问财/妙想等数据源应该有龙虎榜查询接口
        # 暂时返回模拟数据结构
        
        return []
    
    def parse_lhb_detail(self, lhb_text: str) -> List[Dict]:
        """
        解析龙虎榜文本数据
        
        Args:
            lhb_text: 龙虎榜原始文本
        
        Returns:
            解析后的数据列表
        """
        records = []
        lines = lhb_text.strip().split('\n')
        
        current_stock = None
        
        for line in lines:
            if not line:
                continue
            
            # 解析股票名称行
            if line.startswith('【') and '】' in line:
                name = line.split('】')[0][1:]
                code = line.split('】')[1].split('(')[0].strip() if ')' in line else ''
                current_stock = {
                    'name': name,
                    'code': code,
                    'reason': '',
                    'buy_seats': [],
                    'sell_seats': [],
                }
                continue
            
            # 解析买入席位
            if '买入' in line and current_stock:
                parts = line.split('\t')
                for part in parts:
                    if '席位' in part or '机构' in part:
                        seat = self._parse_seat(part)
                        if seat:
                            current_stock['buy_seats'].append(seat)
            
            # 解析卖出席位
            if '卖出' in line and current_stock:
                parts = line.split('\t')
                for part in parts:
                    if '席位' in part or '机构' in part:
                        seat = self._parse_seat(part)
                        if seat:
                            current_stock['sell_seats'].append(seat)
            
            # 解析原因
            if '原因' in line and current_stock:
                current_stock['reason'] = line.split('原因:')[-1].strip()
            
            # 记录一条完整数据
            if current_stock and len(current_stock.get('buy_seats', [])) > 0:
                if line.startswith('【') and current_stock in records:
                    records.append(current_stock)
                    current_stock = None
        
        if current_stock:
            records.append(current_stock)
        
        return records
    
    def _parse_seat(self, text: str) -> Optional[Dict]:
        """解析席位信息"""
        text = text.strip()
        if not text:
            return None
        
        # 判断是否机构席位
        is_institutional = any(inst in text for inst in self.institutional_seats)
        
        # 提取金额
        amount = 0
        for word in text:
            if word.isdigit() or word == '.':
                try:
                    amount = float(text.split('万')[0][-8:].replace(',', ''))
                    break
                except:
                    pass
        
        return {
            'name': text,
            'is_institutional': is_institutional,
            'amount': amount  # 万元
        }
    
    def analyze_institutional_activity(self, lhb_records: List[Dict]) -> List[Dict]:
        """
        分析机构席位活动
        
        Args:
            lhb_records: 龙虎榜记录
        
        Returns:
            机构活动分析结果
        """
        activities = []
        
        for record in lhb_records:
            code = record.get('code', '')
            name = record.get('name', '')
            
            # 统计机构买入
            inst_buy_amount = 0
            inst_buy_count = 0
            for seat in record.get('buy_seats', []):
                if seat.get('is_institutional'):
                    inst_buy_amount += seat.get('amount', 0)
                    inst_buy_count += 1
            
            # 统计机构卖出
            inst_sell_amount = 0
            inst_sell_count = 0
            for seat in record.get('sell_seats', []):
                if seat.get('is_institutional'):
                    inst_sell_amount += seat.get('amount', 0)
                    inst_sell_count += 1
            
            # 净买入
            net_amount = inst_buy_amount - inst_sell_amount
            
            # 判断机构态度
            if net_amount > 5000:  # 净买入5000万以上
                attitude = 'STRONG_BUY'
            elif net_amount > 1000:
                attitude = 'BUY'
            elif net_amount < -5000:
                attitude = 'STRONG_SELL'
            elif net_amount < -1000:
                attitude = 'SELL'
            else:
                attitude = 'NEUTRAL'
            
            activity = {
                'code': code,
                'name': name,
                'reason': record.get('reason', ''),
                'inst_buy_amount': round(inst_buy_amount, 2),  # 万元
                'inst_sell_amount': round(inst_sell_amount, 2),
                'net_amount': round(net_amount, 2),
                'inst_buy_count': inst_buy_count,
                'inst_sell_count': inst_sell_count,
                'attitude': attitude,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d')
            }
            
            activities.append(activity)
        
        # 按净买入排序
        activities.sort(key=lambda x: x['net_amount'], reverse=True)
        
        return activities
    
    def filter_low_position_stocks(self, 
                                   activities: List[Dict],
                                   current_prices: Dict[str, float]) -> List[Dict]:
        """
        筛选低位机构买入股
        
        Args:
            activities: 机构活动列表
            current_prices: 当前价格字典
        
        Returns:
            低位机构股列表
        """
        low_position_stocks = []
        
        for activity in activities:
            code = activity['code']
            price = current_prices.get(code, 0)
            
            if price <= 0:
                continue
            
            # 计算相对低位
            # 这里需要历史价格数据
            # 暂时用模拟逻辑
            
            # 机构大幅买入 + 股价相对低位 = 潜在机会
            if activity['net_amount'] > 1000:  # 净买入1000万以上
                # 需要判断是否在低位
                # 简化：价格<20元视为相对低位
                if price < 20:
                    low_position_stocks.append({
                        **activity,
                        'price': price,
                        'suggestion': '机构低位买入，可关注',
                        'risk': 'MEDIUM'
                    })
        
        # 按净买入排序
        low_position_stocks.sort(key=lambda x: x['net_amount'], reverse=True)
        
        return low_position_stocks
    
    def generate_lhb_report(self,
                           activities: List[Dict],
                           date: Optional[str] = None) -> str:
        """
        生成龙虎榜分析报告
        
        Args:
            activities: 机构活动列表
            date: 日期
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 龙虎榜机构追踪报告 - {date}")
        report.append(f"{'='*60}")
        report.append("")
        
        # 机构净买入 TOP
        inst_buy = [a for a in activities if a['net_amount'] > 0]
        inst_sell = [a for a in activities if a['net_amount'] < 0]
        
        if inst_buy:
            report.append(f"📈 机构净买入 ({len(inst_buy)}只)")
            report.append("-"*50)
            for a in inst_buy[:10]:
                report.append(f"  {a['name']}({a['code']})")
                report.append(f"    净买入: {a['net_amount']:.0f}万元")
                report.append(f"    买入: {a['inst_buy_amount']:.0f}万 | 卖出: {a['inst_sell_amount']:.0f}万")
                report.append(f"    上榜原因: {a['reason']}")
            report.append("")
        
        if inst_sell:
            report.append(f"📉 机构净卖出 ({len(inst_sell)}只)")
            report.append("-"*50)
            for a in inst_sell[:5]:
                report.append(f"  {a['name']}({a['code']})")
                report.append(f"    净卖出: {abs(a['net_amount']):.0f}万元")
            report.append("")
        
        # 操作建议
        report.append(f"{'='*60}")
        report.append("📋 操作建议")
        report.append("-"*50)
        
        if inst_buy:
            best = inst_buy[0]
            report.append(f"🔥 最佳标的: {best['name']}({best['code']})")
            report.append(f"   机构净买入: {best['net_amount']:.0f}万元")
            report.append(f"   建议: 开盘关注，择机买入")
        
        report.append("")
        report.append(f"{'='*60}")
        
        return "\n".join(report)


def main():
    """命令行入口"""
    tracker = LhbTracker()
    
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"龙虎榜追踪器已初始化")
    print(f"数据目录: {tracker.data_dir}")


if __name__ == '__main__':
    main()
