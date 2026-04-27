# -*- coding: utf-8 -*-
"""
统一数据源层 - Unified Data Source
自动切换可用数据源：腾讯财经 → 同花顺问财 → akshare → 新浪

Author: 炒股大师量化系统
"""

import os
import sys
import time
import json
import urllib.request
import ssl
from typing import Dict, Optional, List, Any
from datetime import datetime


class DataSource:
    """统一数据源"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        
        # 问财API Key
        self.iwencai_key = os.environ.get(
            'IWENCAI_API_KEY',
            'YOUR_IWENCAI_API_KEY_HERE'
        )
        
        # 状态记录
        self.source_status = {
            'tencent': {'ok': False, 'latency': 0},
            'iwencai': {'ok': False, 'latency': 0},
            'akshare': {'ok': False, 'latency': 0},
            'sina': {'ok': False, 'latency': 0},
        }
        
        # 探测可用数据源
        self._probe_sources()
    
    def _probe_sources(self):
        """探测各数据源可用性"""
        print("🔍 探测数据源...")
        
        # 腾讯财经探测
        try:
            t0 = time.time()
            url = 'https://qt.gtimg.cn/q=sh000001'
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
            data = resp.read()
            if len(data) > 100:
                self.source_status['tencent']['ok'] = True
                self.source_status['tencent']['latency'] = round((time.time() - t0) * 1000)
        except Exception:
            pass
        
        # 同花顺问财探测
        try:
            t0 = time.time()
            url = 'https://openapi.iwencai.com/v1/query2data'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.iwencai_key}'
            }
            body = json.dumps({'query': '上证指数', 'token': self.iwencai_key}).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=8)
            result = json.loads(resp.read())
            if result.get('status_code') == 0 or result.get('code') == 0:
                self.source_status['iwencai']['ok'] = True
                self.source_status['iwencai']['latency'] = round((time.time() - t0) * 1000)
        except Exception:
            pass
        
        # 新浪探测
        try:
            t0 = time.time()
            url = 'https://hq.sinajs.cn/list=sh000001'
            headers = {'Referer': 'https://finance.sina.com.cn'}
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=5)
            if len(resp.read()) > 50:
                self.source_status['sina']['ok'] = True
                self.source_status['sina']['latency'] = round((time.time() - t0) * 1000)
        except Exception:
            pass
        
        # 打印结果
        print("📡 数据源状态:")
        for name, status in self.source_status.items():
            ok = "✅" if status['ok'] else "❌"
            latency = f"{status['latency']}ms" if status['ok'] else "N/A"
            print(f"   {ok} {name.upper()}: {latency}")
        
        # 找最优
        available = [(n, s) for n, s in self.source_status.items() if s['ok']]
        if available:
            available.sort(key=lambda x: x[1]['latency'])
            best = available[0][0]
            print(f"   🎯 最优数据源: {best.upper()}")
        else:
            print("   ⚠️ 所有数据源均不可用!")
    
    def get_realtime_quote(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情（腾讯财经）
        
        Args:
            codes: 股票代码列表，如 ['sh000001', 'sz000858', 'sh600519']
        
        Returns:
            行情数据字典 {code: {name, price, change, change_pct, volume, ...}}
        """
        results = {}
        
        if not self.source_status['tencent']['ok']:
            return results
        
        try:
            codes_str = ','.join(codes)
            url = f'https://qt.gtimg.cn/q={codes_str}'
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=10)
            raw = resp.read().decode('gbk')
            
            for line in raw.strip().split('\n'):
                if '="' not in line:
                    continue
                
                parts = line.split('="')[1].split('"')[0].split('~')
                if len(parts) < 35:
                    continue
                
                raw_code = line.split('="')[0].split('q=')[-1].strip()
                # 腾讯返回 v_sh600519，转为 sh600519
                code = raw_code.replace('v_', '').strip()
                
                try:
                    price = float(parts[3]) if parts[3] else 0
                    yesterday_close = float(parts[4]) if parts[4] else price
                    change = price - yesterday_close
                    change_pct = (change / yesterday_close * 100) if yesterday_close else 0
                    
                    results[code] = {
                        'name': parts[1] if len(parts) > 1 else '',
                        'code': code,
                        'price': price,
                        'open': float(parts[5]) if parts[5] else 0,
                        'volume': int(parts[6]) if parts[6] else 0,  # 手
                        'yesterday_close': yesterday_close,
                        'change': round(change, 2),
                        'change_pct': round(change_pct, 2),
                        'high': float(parts[33]) if parts[33] else 0,
                        'low': float(parts[34]) if parts[34] else 0,
                        'turnover': float(parts[37]) if parts[37] else 0,  # 成交额(万元)
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except (ValueError, IndexError):
                    continue
                    
        except Exception as e:
            print(f"获取实时行情失败: {e}")
        
        return results
    
    def query_iwencai(self, query: str, count: int = 10) -> Dict:
        """
        查询同花顺问财
        
        Args:
            query: 查询语句，如 "今日涨停股" "主力资金流入"
            count: 返回条数
        
        Returns:
            问财查询结果
        """
        if not self.source_status['iwencai']['ok']:
            return {'success': False, 'message': '问财不可用'}
        
        try:
            url = 'https://openapi.iwencai.com/v1/query2data'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.iwencai_key}'
            }
            body = json.dumps({'query': query, 'token': self.iwencai_key, 'count': count}).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            resp = urllib.request.urlopen(req, context=self.ctx, timeout=15)
            result = json.loads(resp.read())
            
            if result.get('status_code') == 0 or result.get('code') == 0:
                return {
                    'success': True,
                    'data': result,
                    'query': query
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', '未知错误'),
                    'query': query
                }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'query': query
            }
    
    def get_limit_up_stocks(self) -> List[Dict]:
        """
        获取今日涨停股列表
        
        Returns:
            涨停股列表
        """
        result = self.query_iwencai("今日涨停股", count=50)
        
        if not result['success']:
            return []
        
        stocks = []
        try:
            data = result['data']
            columns = data.get('columns', [])
            rows = data.get('data', [])
            
            for row in rows:
                stock = dict(zip(columns, row))
                stocks.append({
                    'code': stock.get('代码', ''),
                    'name': stock.get('名称', ''),
                    'price': stock.get('现价', 0),
                    'change_pct': stock.get('涨跌幅', 0),
                    'reason': stock.get('涨停原因类别', ''),
                })
        except Exception as e:
            print(f"解析涨停股数据失败: {e}")
        
        return stocks
    
    def get_active_stocks(self, limit: int = 20) -> List[Dict]:
        """
        获取今日活跃股（涨幅居前）
        
        Returns:
            活跃股列表
        """
        result = self.query_iwencai("今日涨幅前十", count=limit)
        
        if not result['success']:
            return []
        
        stocks = []
        try:
            data = result['data']
            columns = data.get('columns', [])
            rows = data.get('data', [])
            
            for row in rows:
                stock = dict(zip(columns, row))
                stocks.append({
                    'code': stock.get('代码', ''),
                    'name': stock.get('名称', ''),
                    'price': stock.get('现价', 0),
                    'change_pct': stock.get('涨跌幅', 0),
                    'volume_ratio': stock.get('量比', 0),
                })
        except Exception:
            pass
        
        return stocks
    
    def get_main_flow(self, code: str) -> Dict:
        """
        获取主力资金流向（通过问财）
        
        Args:
            code: 股票代码，如 '000001' 或 'sh000001'
        
        Returns:
            资金流向数据
        """
        # 转换代码格式
        if code.startswith('sh') or code.startswith('sz'):
            code_clean = code[2:]
        else:
            code_clean = code
        
        result = self.query_iwencai(f"{code_clean} 主力资金流向", count=5)
        
        if not result['success']:
            return {}
        
        try:
            data = result['data']
            columns = data.get('columns', [])
            rows = data.get('data', [])
            
            if rows:
                row = rows[0]
                stock = dict(zip(columns, row))
                return {
                    'code': code_clean,
                    'name': stock.get('名称', ''),
                    'main_net_inflow': stock.get('主力净流入', 0),
                    'main_net_inflow_pct': stock.get('主力净流入占比', 0),
                    'price': stock.get('现价', 0),
                    'change_pct': stock.get('涨跌幅', 0),
                    'date': stock.get('日期', datetime.now().strftime('%Y-%m-%d')),
                }
        except Exception:
            pass
        
        return {}
    
    def get_market_sentiment(self) -> Dict:
        """
        获取市场情绪指标
        
        Returns:
            情绪数据字典
        """
        sentiment = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'index': {},
            'limit_up_count': 0,
            'limit_down_count': 0,
            'sentiment_level': 'UNKNOWN',
        }
        
        # 获取主要指数
        try:
            quotes = self.get_realtime_quote(['sh000001', 'sz399001', 'sz399006', 'sh000300'])
            sentiment['index'] = quotes
            
            # 计算整体情绪
            changes = [q['change_pct'] for q in quotes.values() if q.get('change_pct')]
            avg_change = sum(changes) / len(changes) if changes else 0
            
            if avg_change > 2:
                sentiment['sentiment_level'] = 'EXTREME_GREED'
            elif avg_change > 0.5:
                sentiment['sentiment_level'] = 'GREED'
            elif avg_change > -0.5:
                sentiment['sentiment_level'] = 'NEUTRAL'
            elif avg_change > -2:
                sentiment['sentiment_level'] = 'FEAR'
            else:
                sentiment['sentiment_level'] = 'EXTREME_FEAR'
        except Exception:
            pass
        
        # 涨停股数量
        try:
            limit_ups = self.get_limit_up_stocks()
            sentiment['limit_up_count'] = len(limit_ups)
        except Exception:
            pass
        
        return sentiment
    
    def print_sentiment_report(self, sentiment: Dict):
        """打印情绪报告"""
        index = sentiment.get('index', {})
        
        print(f"\n{'='*60}")
        print(f"📊 市场情绪报告 - {sentiment.get('date')} {sentiment.get('time')}")
        print(f"{'='*60}")
        
        # 指数
        print("\n📈 主要指数:")
        for code, data in index.items():
            change = data.get('change_pct', 0)
            emoji = '🔴' if change > 0 else '🟢' if change < 0 else '⚪'
            print(f"   {emoji} {data.get('name','未知')}: {data.get('price',0):.2f} ({change:+.2f}%)")
        
        # 情绪
        level = sentiment.get('sentiment_level', 'UNKNOWN')
        level_map = {
            'EXTREME_GREED': '😱 极度贪婪',
            'GREED': '😊 贪婪',
            'NEUTRAL': '😐 中性',
            'FEAR': '😰 恐惧',
            'EXTREME_FEAR': '😱 极度恐惧',
        }
        print(f"\n🎭 市场情绪: {level_map.get(level, level)}")
        print(f"   涨停股数量: {sentiment.get('limit_up_count', 0)}家")
        
        print(f"\n{'='*60}\n")


def main():
    """测试数据源"""
    ds = DataSource()
    
    # 获取市场情绪
    sentiment = ds.get_market_sentiment()
    ds.print_sentiment_report(sentiment)
    
    # 测试获取单股行情
    print("\n📋 个股行情测试:")
    quotes = ds.get_realtime_quote(['sh600519', 'sz000858', 'sh000001'])
    for code, data in quotes.items():
        print(f"   {data.get('name')}({code}): {data.get('price')} ({data.get('change_pct'):+.2f}%)")


if __name__ == '__main__':
    main()
