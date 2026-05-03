# -*- coding: utf-8 -*-
"""
连板股策略 - Limit Up Stock Strategy
基于涨停基因、板块效应、资金流向的短线策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .logger import get_logger
from .data_sources import DataSource

logger = get_logger('limit_up_strategy')


class ChainLevel(Enum):
    """连板等级"""
    FIRST = "首板"  # 第一个涨停
    SECOND = "二板"  # 第二个涨停
    THIRD = "三板"  # 第三个涨停
    HIGH = "高标"  # 四板及以上


class LimitUpStrategy:
    """连板股策略"""
    
    def __init__(self):
        self.ds = DataSource()
        
        # 策略参数
        self.min_limit_up_days = 2  # 最小连板天数
        self.max_chase_pct = 0.05  # 最大追高比例（5%）
        
        # 涨停基因评分权重
        self.weights = {
            'chain_level': 0.30,  # 连板等级
            'sector_effect': 0.25,  # 板块效应
            'capital_flow': 0.25,  # 资金流向
            'limit_up_quality': 0.20,  # 涨停质量
        }
    
    def select_stocks(self, date: str = None) -> List[Dict]:
        """
        选股：筛选潜在连板股
        
        Returns:
            股票列表，包含代码、名称、评分、连板数等
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"[{date}] 开始筛选连板股...")
        
        candidates = []
        
        # 1. 获取今日涨停股
        limit_up_stocks = self._get_limit_up_stocks()
        
        # 2. 分析连板等级
        for stock in limit_up_stocks:
            analysis = self._analyze_stock(stock, date)
            if analysis['score'] >= 60:  # 及格分
                candidates.append(analysis)
        
        # 3. 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"筛选到 {len(candidates)} 只连板候选股")
        
        return candidates
    
    def _get_limit_up_stocks(self) -> List[str]:
        """获取今日涨停股列表"""
        try:
            # 使用问财 API 获取涨停股
            result = self.ds.query_iwencai("今日涨停股", count=100)
            
            if result.get('success'):
                stocks = []
                # 解析结果
                data = result.get('data', {}).get('data', [])
                for item in data:
                    if isinstance(item, dict):
                        code = item.get('code', '')
                        if code:
                            stocks.append(code)
                
                logger.info(f"获取到 {len(stocks)} 只涨停股")
                return stocks
            
        except Exception as e:
            logger.error(f"获取涨停股失败：{e}")
        
        return []
    
    def _analyze_stock(self, code: str, date: str) -> Dict:
        """分析个股"""
        score = 0
        details = {}
        
        # 1. 连板等级分析（30 分）
        chain_level, chain_days = self._analyze_chain_level(code)
        level_score = self._score_chain_level(chain_level)
        score += level_score * self.weights['chain_level']
        
        details['chain_level'] = chain_level.value
        details['chain_days'] = chain_days
        
        # 2. 板块效应分析（25 分）
        sector_effect = self._analyze_sector_effect(code)
        sector_score = self._score_sector_effect(sector_effect)
        score += sector_score * self.weights['sector_effect']
        
        details['sector'] = sector_effect.get('sector')
        details['sector_limit_up_count'] = sector_effect.get('limit_up_count', 0)
        
        # 3. 资金流向分析（25 分）
        capital_flow = self._analyze_capital_flow(code)
        flow_score = self._score_capital_flow(capital_flow)
        score += flow_score * self.weights['capital_flow']
        
        details['main_flow'] = capital_flow.get('main_flow', 0)
        details['ddx'] = capital_flow.get('ddx', 0)
        
        # 4. 涨停质量分析（20 分）
        quality_score = self._analyze_limit_up_quality(code)
        score += quality_score * self.weights['limit_up_quality']
        
        details['quality_score'] = quality_score
        
        return {
            'code': code,
            'date': date,
            'score': round(score, 2),
            'details': details,
        }
    
    def _analyze_chain_level(self, code: str, lookback_days: int = 10) -> Tuple[ChainLevel, int]:
        """分析连板等级"""
        # 获取历史 K 线
        try:
            df = self._get_stock_history(code, lookback_days)
            
            # 计算每日涨跌幅
            df['pct_change'] = df['close'].pct_change()
            
            # 统计连续涨停天数
            limit_up_threshold = 0.095  # 9.5% 算涨停
            
            consecutive = 0
            for pct in df['pct_change'].iloc[-1::-1]:  # 从后往前
                if pct >= limit_up_threshold:
                    consecutive += 1
                else:
                    break
            
            # 确定连板等级
            if consecutive >= 4:
                return ChainLevel.HIGH, consecutive
            elif consecutive == 3:
                return ChainLevel.THIRD, consecutive
            elif consecutive == 2:
                return ChainLevel.SECOND, consecutive
            else:
                return ChainLevel.FIRST, consecutive if consecutive > 0 else 1
        
        except Exception as e:
            logger.debug(f"分析连板等级失败：{code} - {e}")
            return ChainLevel.FIRST, 1
    
    def _score_chain_level(self, level: ChainLevel) -> float:
        """连板等级评分"""
        scores = {
            ChainLevel.HIGH: 100,
            ChainLevel.THIRD: 85,
            ChainLevel.SECOND: 70,
            ChainLevel.FIRST: 50,
        }
        return scores.get(level, 50)
    
    def _analyze_sector_effect(self, code: str) -> Dict:
        """分析板块效应"""
        try:
            # 获取股票所属板块
            sector_info = self._get_stock_sector(code)
            sector = sector_info.get('sector', '')
            
            if not sector:
                return {'sector': '', 'limit_up_count': 0, 'effect': 'none'}
            
            # 获取板块内涨停股数量
            query = f"{sector} 板块 今日涨停"
            result = self.ds.query_iwencai(query, count=50)
            
            limit_up_count = len(result.get('data', {}).get('data', []))
            
            # 判断板块效应
            if limit_up_count >= 5:
                effect = 'strong'
            elif limit_up_count >= 3:
                effect = 'moderate'
            else:
                effect = 'weak'
            
            return {
                'sector': sector,
                'limit_up_count': limit_up_count,
                'effect': effect,
            }
        
        except Exception as e:
            logger.debug(f"分析板块效应失败：{code} - {e}")
            return {'sector': '', 'limit_up_count': 0, 'effect': 'none'}
    
    def _score_sector_effect(self, sector_effect: Dict) -> float:
        """板块效应评分"""
        effect_scores = {
            'strong': 100,
            'moderate': 70,
            'weak': 40,
            'none': 20,
        }
        return effect_scores.get(sector_effect.get('effect', 'none'), 20)
    
    def _analyze_capital_flow(self, code: str) -> Dict:
        """分析资金流向"""
        try:
            # 获取资金流向数据
            # 简化处理，实际需要调用数据源 API
            return {
                'main_flow': 0,
                'ddx': 0,
            }
        except Exception as e:
            logger.debug(f"分析资金流向失败：{code} - {e}")
            return {'main_flow': 0, 'ddx': 0}
    
    def _score_capital_flow(self, flow: Dict) -> float:
        """资金流向评分"""
        score = 50  # 基础分
        
        # 主力流入加分
        main_flow = flow.get('main_flow', 0)
        if main_flow > 10000:  # 流入超 1 亿
            score += 40
        elif main_flow > 5000:  # 流入超 5000 万
            score += 25
        elif main_flow > 0:
            score += 10
        elif main_flow < -5000:
            score -= 30
        elif main_flow < -10000:
            score -= 50
        
        return max(0, min(100, score))
    
    def _analyze_limit_up_quality(self, code: str) -> float:
        """分析涨停质量"""
        score = 50  # 基础分
        
        try:
            # 获取当日分时数据
            # 简化处理，这里只返回基础分
            return score
        
        except Exception as e:
            logger.debug(f"分析涨停质量失败：{code} - {e}")
            return score
    
    def _get_stock_history(self, code: str, days: int = 10) -> pd.DataFrame:
        """获取股票历史数据"""
        try:
            # 使用腾讯财经获取
            if not code.startswith(('sh', 'sz', 'bj')):
                if code.startswith('6'):
                    code = f'sh{code}'
                else:
                    code = f'sz{code}'
            
            url = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,,{days},qfq'
            import urllib.request
            import ssl
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, context=ctx, timeout=5)
            data = resp.read().decode('utf-8')
            
            import json
            result = json.loads(data)
            
            kline = result.get('data', {}).get(code, {}).get('qfqday', [])
            
            df = pd.DataFrame(kline, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'something'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            return df
        
        except Exception as e:
            logger.error(f"获取历史数据失败：{code} - {e}")
            return pd.DataFrame()
    
    def _get_stock_sector(self, code: str) -> Dict:
        """获取股票所属板块"""
        try:
            # 查询问财获取板块信息
            query = f"{code} 所属板块"
            result = self.ds.query_iwencai(query, count=1)
            
            if result.get('success'):
                data = result.get('data', {}).get('data', [])
                if data:
                    return {'sector': data[0].get('板块', '')}
        
        except Exception as e:
            logger.debug(f"获取板块信息失败：{code} - {e}")
        
        return {}
    
    def should_buy(self, code: str, current_price: float, 
                   yester_close: float) -> Dict:
        """
        判断是否应该买入
        
        Args:
            code: 股票代码
            current_price: 当前价格
            yester_close: 昨日收盘价
        
        Returns:
            {
                'should_buy': bool,
                'reason': str,
                'suggested_price': float,
            }
        """
        analysis = self._analyze_stock(code, datetime.now().strftime('%Y-%m-%d'))
        
        # 计算涨幅
        change_pct = (current_price - yester_close) / yester_close
        
        # 判断条件
        should_buy = False
        reason = ""
        suggested_price = current_price
        
        if analysis['score'] < 70:
            reason = f"评分过低：{analysis['score']:.1f}"
        elif change_pct > 0.07:
            reason = f"涨幅过高：{change_pct*100:.1f}%，风险大"
        elif analysis['details'].get('sector_limit_up_count', 0) < 2:
            reason = "板块效应不足"
        else:
            should_buy = True
            reason = "符合连板策略条件"
            suggested_price = yester_close * 1.02  # 建议买入价：涨幅 2%
        
        return {
            'should_buy': should_buy,
            'reason': reason,
            'suggested_price': round(suggested_price, 2),
            'score': analysis['score'],
        }


# 快捷函数
def select_limit_up_stocks() -> List[Dict]:
    """快速选股"""
    strategy = LimitUpStrategy()
    return strategy.select_stocks()
