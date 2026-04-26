# -*- coding: utf-8 -*-
"""
竞价情绪分析模块 - Auction Sentiment Analyzer
分析9:15-9:25竞价阶段的市场情绪和个股表现

Author: 炒股大师量化系统
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class AuctionSentiment:
    """竞价情绪分析器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 情绪阈值
        self.thresholds = {
            'extreme_greed': 80,      # 极度贪婪
            'greed': 65,              # 贪婪
            'neutral': 50,            # 中性
            'fear': 35,              # 恐慌
            'extreme_fear': 20,      # 极度恐慌
        }
        
        # 历史情绪缓存
        self.history_file = self.data_dir / 'auction_sentiment_history.json'
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """加载历史情绪数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_history(self):
        """保存情绪历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def calculate_market_sentiment(self, 
                                   limit_up_count: int,
                                   limit_down_count: int,
                                   advance_count: int,
                                   decline_count: int) -> Dict:
        """
        计算市场整体竞价情绪
        
        Args:
            limit_up_count: 竞价涨停数
            limit_down_count: 竞价跌停数
            advance_count: 竞价上涨数
            decline_count: 竞价下跌数
        
        Returns:
            情绪分析结果
        """
        total = advance_count + decline_count
        
        if total == 0:
            return {
                'sentiment_score': 50,
                'level': 'NEUTRAL',
                'interpretation': '无法判断',
                'action': '观望'
            }
        
        # 计算涨跌比
        advance_ratio = advance_count / total * 100
        
        # 计算涨停/跌停比
        if limit_down_count > 0:
            limit_ratio = limit_up_count / limit_down_count
        else:
            limit_ratio = limit_up_count if limit_up_count > 0 else 1.0
        
        # 情绪综合评分
        # 基础分：涨跌比 * 0.6 + 涨停比 * 0.4
        sentiment = advance_ratio * 0.6 + min(limit_ratio * 20, 100) * 0.4
        
        # 判断情绪等级
        if sentiment >= self.thresholds['extreme_greed']:
            level = 'EXTREME_GREED'
            interpretation = '极度贪婪，警惕短线回调风险'
            action = '不追高，关注止盈机会'
        elif sentiment >= self.thresholds['greed']:
            level = 'GREED'
            interpretation = '市场情绪偏热，可积极参与'
            action = '轻仓追强势股'
        elif sentiment >= self.thresholds['neutral']:
            level = 'NEUTRAL'
            interpretation = '市场情绪中性，观望为主'
            action = '谨慎操作，等待明确信号'
        elif sentiment >= self.thresholds['fear']:
            level = 'FEAR'
            interpretation = '市场情绪偏冷，但可能是机会'
            action = '关注错杀优质股'
        else:
            level = 'EXTREME_FEAR'
            interpretation = '极度恐慌，可能出现超跌反弹'
            action = '等待恐慌结束，择机布局'
        
        return {
            'sentiment_score': round(sentiment, 1),
            'level': level,
            'advance_count': advance_count,
            'decline_count': decline_count,
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count,
            'advance_ratio': round(advance_ratio, 1),
            'limit_ratio': round(limit_ratio, 1),
            'interpretation': interpretation,
            'action': action,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def analyze_stock_auction(self, 
                             stock_code: str,
                             stock_name: str,
                             yesterday_close: float,
                             auction_price: float,
                             auction_volume: float,
                             auction_amount: float) -> Dict:
        """
        分析个股竞价情况
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            yesterday_close: 昨日收盘价
            auction_price: 竞价价格
            auction_volume: 竞价成交量（手）
            auction_amount: 竞价成交额（元）
        
        Returns:
            个股竞价分析结果
        """
        # 计算竞价涨跌幅
        change_pct = (auction_price - yesterday_close) / yesterday_close * 100
        
        # 竞价强度评分
        score = 50
        
        # 1. 竞价涨幅评分（最高40分）
        if change_pct >= 10:
            score += 40  # 涨停竞价
        elif change_pct >= 5:
            score += 30
        elif change_pct >= 3:
            score += 20
        elif change_pct >= 0:
            score += 10
        elif change_pct >= -3:
            score += 0
        elif change_pct >= -5:
            score -= 10
        elif change_pct >= -10:
            score -= 20
        else:
            score -= 40  # 跌停竞价
        
        # 2. 竞价成交额评分（最高30分）
        # 假设竞价成交额占全天成交的5-15%为正常
        estimated_total_amount = auction_amount / 0.1  # 估算全天成交额
        
        if auction_amount >= 100000000:  # 1亿以上
            score += 30
        elif auction_amount >= 50000000:  # 5000万以上
            score += 20
        elif auction_amount >= 20000000:  # 2000万以上
            score += 10
        elif auction_amount >= 10000000:  # 1000万以上
            score += 5
        else:
            score -= 5
        
        # 3. 竞价成交量评分（最高30分）
        if auction_volume >= 50000:  # 5万手以上
            score += 30
        elif auction_volume >= 30000:
            score += 20
        elif auction_volume >= 10000:
            score += 10
        elif auction_volume >= 5000:
            score += 5
        else:
            score -= 5
        
        score = max(0, min(100, score))
        
        # 判断竞价类型
        if change_pct >= 9.5:
            auction_type = '涨停竞价'
        elif change_pct >= 5:
            auction_type = '高开竞价'
        elif change_pct >= 2:
            auction_type = '小幅高开'
        elif change_pct >= 0:
            auction_type = '平开'
        elif change_pct >= -2:
            auction_type = '小幅低开'
        elif change_pct >= -5:
            auction_type = '低开竞价'
        else:
            auction_type = '跌停竞价'
        
        # 生成信号
        if score >= 80:
            signal = 'STRONG_BUY'
            action = '强势竞价，可开盘买入'
        elif score >= 60:
            signal = 'BUY'
            action = '竞价较强，可关注'
        elif score >= 40:
            signal = 'HOLD'
            action = '竞价中性，等待盘中机会'
        elif score >= 20:
            signal = 'SELL'
            action = '竞价较弱，考虑卖出'
        else:
            signal = 'STRONG_SELL'
            action = '竞价极弱，开盘止损'
        
        return {
            'code': stock_code,
            'name': stock_name,
            'yesterday_close': yesterday_close,
            'auction_price': auction_price,
            'change_pct': round(change_pct, 2),
            'auction_volume': auction_volume,
            'auction_amount': auction_amount,
            'score': score,
            'auction_type': auction_type,
            'signal': signal,
            'action': action,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def scan_auction_opportunities(self, 
                                  auction_data: List[Dict],
                                  market_sentiment: Dict) -> Dict[str, List]:
        """
        扫描竞价机会股
        
        Args:
            auction_data: 个股竞价数据列表
            market_sentiment: 市场整体情绪
        
        Returns:
            分类后的机会股
        """
        opportunities = {
            'strong_buy': [],   # 强烈买入
            'buy': [],          # 可以买入
            'watch': [],        # 观望
            'sell': [],         # 考虑卖出
            'avoid': []         # 坚决规避
        }
        
        sentiment_level = market_sentiment.get('level', 'NEUTRAL')
        sentiment_score = market_sentiment.get('sentiment_score', 50)
        
        for stock in auction_data:
            score = stock.get('score', 50)
            change_pct = stock.get('change_pct', 0)
            
            # === 竞价涨停股 ===
            if change_pct >= 9.5:
                if sentiment_level in ['GREED', 'EXTREME_GREED']:
                    opportunities['strong_buy'].append({
                        **stock,
                        'reason': '竞价涨停+市场情绪热，积极参与'
                    })
                else:
                    opportunities['buy'].append({
                        **stock,
                        'reason': '竞价涨停，但市场情绪一般，谨慎参与'
                    })
            
            # === 竞价高开股 ===
            elif change_pct >= 5:
                if score >= 70:
                    opportunities['buy'].append({
                        **stock,
                        'reason': f'竞价高开{change_pct:.1f}%，竞价评分{score}'
                    })
                else:
                    opportunities['watch'].append({
                        **stock,
                        'reason': f'竞价高开{change_pct:.1f}%，但竞价评分一般'
                    })
            
            # === 竞价平开/小低开 ===
            elif change_pct >= -2:
                opportunities['watch'].append({
                    **stock,
                    'reason': f'竞价平开附近，{stock.get("reason","")}'
                })
            
            # === 竞价低开 ===
            elif change_pct >= -5:
                if sentiment_level in ['FEAR', 'EXTREME_FEAR']:
                    opportunities['watch'].append({
                        **stock,
                        'reason': '低开后关注反弹机会'
                    })
                else:
                    opportunities['sell'].append({
                        **stock,
                        'reason': f'竞价低开{change_pct:.1f}%，谨慎'
                    })
            
            # === 竞价大跌 ===
            else:
                opportunities['avoid'].append({
                    **stock,
                    'reason': f'竞价大跌{change_pct:.1f}%，不参与'
                })
        
        # 按评分排序
        for key in opportunities:
            opportunities[key].sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return opportunities
    
    def generate_auction_report(self,
                               market_sentiment: Dict,
                               opportunities: Dict[str, List],
                               date: Optional[str] = None) -> str:
        """
        生成竞价情绪报告
        
        Args:
            market_sentiment: 市场情绪
            opportunities: 机会股分类
            date: 日期
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        report = []
        report.append(f"{'='*60}")
        report.append(f"📊 竞价情绪分析报告 - {date}")
        report.append(f"{'='*60}")
        report.append("")
        
        # 市场整体情绪
        sentiment = market_sentiment
        report.append(f"🎯 市场情绪评分: {sentiment.get('sentiment_score', 0)}/100")
        report.append(f"   情绪等级: {sentiment.get('level', 'N/A')}")
        report.append(f"   解读: {sentiment.get('interpretation', '')}")
        report.append(f"   操作建议: {sentiment.get('action', '')}")
        report.append("")
        
        # 涨跌统计
        report.append(f"📈 竞价统计:")
        report.append(f"   上涨家数: {sentiment.get('advance_count', 0)}")
        report.append(f"   下跌家数: {sentiment.get('decline_count', 0)}")
        report.append(f"   涨停竞价: {sentiment.get('limit_up_count', 0)}")
        report.append(f"   跌停竞价: {sentiment.get('limit_down_count', 0)}")
        report.append(f"   上涨比例: {sentiment.get('advance_ratio', 0)}%")
        report.append("")
        
        # 机会股
        if opportunities['strong_buy']:
            report.append(f"🔥 强烈买入 ({len(opportunities['strong_buy'])}只)")
            report.append("-"*50)
            for s in opportunities['strong_buy'][:5]:
                report.append(f"  {s['name']}({s['code']}) 评分:{s['score']:.0f} 涨幅:{s['change_pct']:.1f}%")
                report.append(f"    {s.get('reason', '')}")
            report.append("")
        
        if opportunities['buy']:
            report.append(f"✅ 可以买入 ({len(opportunities['buy'])}只)")
            report.append("-"*50)
            for s in opportunities['buy'][:5]:
                report.append(f"  {s['name']}({s['code']}) 评分:{s['score']:.0f} 涨幅:{s['change_pct']:.1f}%")
                report.append(f"    {s.get('reason', '')}")
            report.append("")
        
        if opportunities['watch']:
            report.append(f"👀 观望 ({len(opportunities['watch'])}只)")
            report.append("-"*50)
            for s in opportunities['watch'][:3]:
                report.append(f"  {s['name']}({s['code']}) 评分:{s['score']:.0f} 涨幅:{s['change_pct']:.1f}%")
            report.append("")
        
        if opportunities['avoid']:
            report.append(f"🚫 坚决规避 ({len(opportunities['avoid'])}只)")
            report.append("-"*50)
            for s in opportunities['avoid'][:3]:
                report.append(f"  {s['name']}({s['code']}) 评分:{s['score']:.0f} 跌幅:{s['change_pct']:.1f}%")
            report.append("")
        
        report.append(f"{'='*60}")
        
        return "\n".join(report)
    
    def get_9_25_signals(self, 
                         limit_up_stocks: List[Dict],
                         auction_data: List[Dict]) -> List[Dict]:
        """
        生成9:25竞价结束信号
        
        Args:
            limit_up_stocks: 竞价涨停股列表
            auction_data: 所有竞价数据
        
        Returns:
            交易信号列表
        """
        signals = []
        
        for stock in auction_data:
            change_pct = stock.get('change_pct', 0)
            score = stock.get('score', 50)
            
            # === 9:25核心信号 ===
            
            # 1. 竞价涨停信号
            if change_pct >= 9.5:
                signals.append({
                    'time': '09:25',
                    'code': stock['code'],
                    'name': stock['name'],
                    'signal': 'LIMIT_UP_AUCTION',
                    'action': '开盘买入' if score >= 70 else '观望',
                    'priority': 'HIGH',
                    'price': stock.get('auction_price', 0),
                    'change_pct': change_pct,
                    'score': score,
                    'reason': f'竞价涨停{change_pct:.1f}%，9:25可考虑买入'
                })
            
            # 2. 竞价高开强势信号
            elif change_pct >= 5 and score >= 65:
                signals.append({
                    'time': '09:25',
                    'code': stock['code'],
                    'name': stock['name'],
                    'signal': 'STRONG_OPEN',
                    'action': '开盘关注',
                    'priority': 'MEDIUM',
                    'price': stock.get('auction_price', 0),
                    'change_pct': change_pct,
                    'score': score,
                    'reason': f'竞价高开{change_pct:.1f}%，竞价强势'
                })
            
            # 3. 竞价低开警示信号
            elif change_pct <= -5 and score <= 30:
                signals.append({
                    'time': '09:25',
                    'code': stock['code'],
                    'name': stock['name'],
                    'signal': 'WEAK_OPEN',
                    'action': '开盘止损',
                    'priority': 'HIGH',
                    'price': stock.get('auction_price', 0),
                    'change_pct': change_pct,
                    'score': score,
                    'reason': f'竞价低开{change_pct:.1f}%，竞价评分低，谨慎'
                })
        
        # 按优先级和评分排序
        signals.sort(key=lambda x: (
            0 if x['priority'] == 'HIGH' else 1,
            -x['score']
        ))
        
        return signals


def main():
    """命令行入口"""
    analyzer = AuctionSentiment()
    
    # 模拟数据
    sentiment = analyzer.calculate_market_sentiment(
        limit_up_count=30,
        limit_down_count=5,
        advance_count=1500,
        decline_count=800
    )
    
    print(f"市场情绪: {sentiment['level']}")
    print(f"评分: {sentiment['sentiment_score']}")
    print(f"解读: {sentiment['interpretation']}")


if __name__ == '__main__':
    main()
