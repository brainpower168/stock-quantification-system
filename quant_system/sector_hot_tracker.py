# -*- coding: utf-8 -*-
"""
题材热点板块追踪模块 - Sector Hot Tracker
追踪热点板块、识别龙头股、捕捉板块轮动机会

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from collections import defaultdict


class SectorHotTracker:
    """热点板块追踪器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 板块历史热度
        self.history_file = self.data_dir / 'sector_hot_history.json'
        self.history = self._load_history()
        
        # 板块分类映射
        self.sector_mapping = self._load_sector_mapping()
    
    def _load_history(self) -> Dict:
        """加载历史板块数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_history(self):
        """保存板块历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def _load_sector_mapping(self) -> Dict:
        """加载板块映射表"""
        return {
            '科技': ['半导体', '芯片', '人工智能', '软件', '电子', '通信'],
            '新能源': ['锂电池', '光伏', '风电', '储能', '新能源汽车'],
            '消费': ['白酒', '食品', '家电', '旅游', '零售'],
            '医药': ['中药', '创新药', '医疗器械', '疫苗'],
            '金融': ['银行', '保险', '证券', '多元金融'],
            '周期': ['钢铁', '煤炭', '有色', '化工', '建材'],
            '基建': ['房地产', '建筑', '工程机械', '水泥'],
            '军工': ['航空', '航天', '船舶', '军工电子'],
        }
    
    def scan_sectors(self, sector_data: List[Dict], date: str) -> List[Dict]:
        """
        扫描板块涨跌情况
        
        Args:
            sector_data: 板块数据列表，每项包含name, change_pct, volume, lead_stock等
            date: 日期
        
        Returns:
            排序后的板块列表
        """
        hot_sectors = []
        
        for sector in sector_data:
            name = sector.get('name', '')
            change_pct = sector.get('change_pct', 0)
            volume = sector.get('volume', 0)
            lead_stock = sector.get('lead_stock', '')  # 龙头股
            
            # 计算热度评分
            hot_score = self._calculate_hot_score(
                change_pct=change_pct,
                volume=volume,
                lead_limit_up=sector.get('lead_limit_up', False)
            )
            
            hot_sector = {
                'name': name,
                'change_pct': change_pct,
                'volume': volume,
                'lead_stock': lead_stock,
                'lead_limit_up': sector.get('lead_limit_up', False),
                'hot_score': hot_score,
                'hot_level': self._get_hot_level(hot_score),
                'timestamp': date
            }
            
            hot_sectors.append(hot_sector)
            
            # 更新历史
            if name not in self.history:
                self.history[name] = {'records': [], 'avg_score': 0}
            
            self.history[name]['records'].append({
                'date': date,
                'hot_score': hot_score,
                'change_pct': change_pct
            })
            
            # 只保留最近30天记录
            if len(self.history[name]['records']) > 30:
                self.history[name]['records'] = self.history[name]['records'][-30:]
            
            # 计算平均热度
            scores = [r['hot_score'] for r in self.history[name]['records']]
            self.history[name]['avg_score'] = sum(scores) / len(scores)
        
        # 保存历史
        self._save_history()
        
        # 按热度排序
        hot_sectors.sort(key=lambda x: x['hot_score'], reverse=True)
        
        return hot_sectors
    
    def _calculate_hot_score(self, change_pct: float, volume: float, 
                            lead_limit_up: bool) -> float:
        """
        计算板块热度评分
        
        Args:
            change_pct: 涨跌幅
            volume: 成交量
            lead_limit_up: 龙头是否涨停
        
        Returns:
            热度评分 (0-100)
        """
        score = 50.0
        
        # 1. 涨跌幅得分 (最高40分)
        if change_pct >= 9.5:  # 涨停
            score += 40
        elif change_pct >= 5:
            score += 30
        elif change_pct >= 3:
            score += 20
        elif change_pct >= 1:
            score += 10
        elif change_pct >= 0:
            score += 5
        elif change_pct >= -2:
            score += 0
        elif change_pct >= -5:
            score -= 15
        else:
            score -= 30
        
        # 2. 成交量得分 (最高30分)
        if volume >= 100000000000:  # 1000亿+
            score += 30
        elif volume >= 50000000000:  # 500亿+
            score += 20
        elif volume >= 20000000000:  # 200亿+
            score += 10
        elif volume >= 10000000000:  # 100亿+
            score += 5
        else:
            score -= 5
        
        # 3. 龙头涨停加分 (最高30分)
        if lead_limit_up:
            score += 30
        
        return max(0, min(100, score))
    
    def _get_hot_level(self, score: float) -> str:
        """根据评分判断热度等级"""
        if score >= 90:
            return '极热'
        elif score >= 75:
            return '很热'
        elif score >= 60:
            return '较热'
        elif score >= 45:
            return '一般'
        elif score >= 30:
            return '偏冷'
        else:
            return '冷淡'
    
    def identify_rotation_opportunity(self, 
                                     sectors: List[Dict],
                                     yesterday_sectors: List[Dict]) -> List[Dict]:
        """
        识别板块轮动机会
        
        Args:
            sectors: 今日板块列表
            yesterday_sectors: 昨日板块列表
        
        Returns:
            轮动机会列表
        """
        opportunities = []
        
        # 构建昨日热度字典
        yesterday_dict = {s['name']: s['hot_score'] for s in yesterday_sectors}
        
        for sector in sectors:
            name = sector['name']
            today_score = sector['hot_score']
            yesterday_score = yesterday_dict.get(name, 50)
            
            # 评分变化
            score_change = today_score - yesterday_score
            
            # 板块轮动信号
            # 1. 昨日冷门，今日变热 → 轮动进入
            if score_change >= 30 and yesterday_score < 40 and today_score >= 60:
                opportunities.append({
                    'name': name,
                    'type': 'ROTATION_IN',
                    'change_pct': sector['change_pct'],
                    'today_score': today_score,
                    'yesterday_score': yesterday_score,
                    'score_change': score_change,
                    'action': '强势买入',
                    'reason': f'板块从{yesterday_score:.0f}分升至{today_score:.0f}分，轮动进入信号'
                })
            
            # 2. 连续两天热度上升
            elif score_change >= 15 and yesterday_score >= 50:
                opportunities.append({
                    'name': name,
                    'type': 'CONTINUE_RISE',
                    'change_pct': sector['change_pct'],
                    'today_score': today_score,
                    'yesterday_score': yesterday_score,
                    'score_change': score_change,
                    'action': '继续持有/买入',
                    'reason': f'板块热度持续上升，连续强势'
                })
            
            # 3. 昨日热门，今日降温 → 轮动退出
            elif score_change <= -30 and yesterday_score >= 70:
                opportunities.append({
                    'name': name,
                    'type': 'ROTATION_OUT',
                    'change_pct': sector['change_pct'],
                    'today_score': today_score,
                    'yesterday_score': yesterday_score,
                    'score_change': score_change,
                    'action': '卖出/规避',
                    'reason': f'板块从{yesterday_score:.0f}分降至{today_score:.0f}分，轮动退出信号'
                })
        
        # 按评分变化排序
        opportunities.sort(key=lambda x: x['score_change'], reverse=True)
        
        return opportunities
    
    def get_leader_follow_stocks(self, 
                                sector: Dict,
                                all_stocks: List[Dict]) -> Dict[str, List]:
        """
        获取龙头股和跟风股
        
        Args:
            sector: 板块信息
            all_stocks: 所有股票数据
        
        Returns:
            龙头股和跟风股列表
        """
        sector_name = sector['name']
        leader_stock = sector.get('lead_stock', '')
        
        leader = None
        followers = []
        
        for stock in all_stocks:
            if stock.get('sector', '') != sector_name:
                continue
            
            code = stock.get('code', '')
            name = stock.get('name', '')
            change_pct = stock.get('change_pct', 0)
            
            if code == leader_stock or name == leader_stock:
                leader = stock
            elif change_pct >= 5 and change_pct < 10:
                followers.append(stock)
        
        return {
            'leader': leader,
            'followers': followers[:10]  # 最多10只跟风股
        }
    
    def generate_sector_report(self,
                              sectors: List[Dict],
                              opportunities: List[Dict],
                              date: Optional[str] = None) -> str:
        """
        生成板块追踪报告
        
        Args:
            sectors: 板块列表
            opportunities: 轮动机会
            date: 日期
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 题材热点板块报告 - {date}")
        report.append(f"{'='*60}")
        report.append("")
        
        # 最热板块
        report.append("🔥 最热板块 TOP5:")
        report.append("-"*50)
        for i, s in enumerate(sectors[:5], 1):
            leader_tag = "🐲" if s.get('lead_limit_up') else "  "
            report.append(f"  {i}. {leader_tag}{s['name']} 涨幅:{s['change_pct']:.1f}% 热度:{s['hot_score']:.0f}({s['hot_level']})")
            if s.get('lead_stock'):
                report.append(f"     龙头: {s['lead_stock']}")
        report.append("")
        
        # 轮动机会
        if opportunities:
            report.append("🔄 板块轮动信号:")
            report.append("-"*50)
            
            # 轮动进入
            rot_in = [o for o in opportunities if o['type'] == 'ROTATION_IN']
            if rot_in:
                report.append("  📈 轮动进入:")
                for o in rot_in[:3]:
                    report.append(f"    {o['name']} → {o['reason']} [{o['action']}]")
            
            # 轮动退出
            rot_out = [o for o in opportunities if o['type'] == 'ROTATION_OUT']
            if rot_out:
                report.append("  📉 轮动退出:")
                for o in rot_out[:3]:
                    report.append(f"    {o['name']} → {o['reason']} [{o['action']}]")
            
            report.append("")
        
        # 操作建议
        report.append(f"{'='*60}")
        report.append("📋 操作建议")
        report.append("-"*50)
        
        if sectors:
            best = sectors[0]
            if best['change_pct'] >= 5 and best.get('lead_limit_up'):
                report.append(f"🔥 最强标的: {best['name']}")
                report.append(f"   龙头{best.get('lead_stock','未知')}已涨停，跟风机会")
            elif best['change_pct'] >= 3:
                report.append(f"✅ 关注: {best['name']} 涨幅{best['change_pct']:.1f}%")
        
        report.append("")
        report.append(f"{'='*60}")
        
        return "\n".join(report)


def main():
    """命令行入口"""
    tracker = SectorHotTracker()
    
    # 模拟板块数据
    sector_data = [
        {'name': '人工智能', 'change_pct': 5.2, 'volume': 80000000000, 'lead_limit_up': True},
        {'name': '锂电池', 'change_pct': 3.1, 'volume': 50000000000, 'lead_limit_up': False},
        {'name': '白酒', 'change_pct': -1.5, 'volume': 20000000000, 'lead_limit_up': False},
    ]
    
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    sectors = tracker.scan_sectors(sector_data, date)
    
    for s in sectors[:3]:
        print(f"{s['name']}: 热度{s['hot_score']:.0f}({s['hot_level']})")


if __name__ == '__main__':
    main()
