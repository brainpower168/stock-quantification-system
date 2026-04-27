#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓自动监控 v2.0
运行时间: 交易日 9:30-14:30 每30分钟

【v2.0 华工科技血泪教训彻底改正 2026-04-27】
1. 止损线：强势股止损改为MA5均线（不再用固定-3%）
2. 止损执行：触发止损先预警，等10:00-10:30反弹窗口再执行
3. 止损后跟踪：卖出后3天内自动跟踪，企稳提醒重新关注
"""
import json, os, sys, time
from datetime import datetime

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), 'positions.json')
ALERT_LOG = os.path.join(os.path.dirname(__file__), 'alerts.log')
SELL_TRACK_FILE = os.path.join(os.path.dirname(__file__), 'sell_track.json')

# 风控参数
RISK = {
    'stop_loss_pct': 0.05,       # 【改】强势股止损 -5%（不再用-3%）
    'take_profit_pct': 0.10,     # 止盈 +10%
    'trailing_stop_pct': 0.03,   # 移动止损回撤 -3%
    'day_loss_limit': 0.05,      # 当日跌幅预警 -5%（不再用-3%）
    'day_gain_alert': 0.07,      # 当日大涨预警 +7%
    'ddx_exit_threshold': -2.0,  # 10日DDX低于此值强制退出
    'stop_loss_wait_minutes': 60, # 【改】止损等待反弹窗口（分钟）
}


def log(msg, to_file=True):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    if to_file:
        with open(ALERT_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def load_positions():
    """加载持仓配置"""
    try:
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"[ERR] 加载持仓失败: {e}")
        return None


def save_positions(data):
    """保存持仓配置"""
    with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_sell_track():
    """加载止损/卖出后跟踪记录"""
    try:
        if os.path.exists(SELL_TRACK_FILE):
            with open(SELL_TRACK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {'tracked': []}


def save_sell_track(data):
    """保存止损后跟踪记录"""
    with open(SELL_TRACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_sell_track(code, name, sell_price, reason, qty, sell_date):
    """记录卖出的股票，进入跟踪状态"""
    track = load_sell_track()
    # 清理超过3天的记录
    today = datetime.now().strftime('%Y-%m-%d')
    track['tracked'] = [
        t for t in track['tracked']
        if t.get('sell_date', '') >= (datetime.now().timestamp() - 3*86400) and t['code'] != code
    ]
    # 添加新记录
    track['tracked'].append({
        'code': code,
        'name': name,
        'sell_price': sell_price,
        'reason': reason,
        'qty': qty,
        'sell_date': sell_date,
        'sell_ts': datetime.now().timestamp(),
        'status': 'TRACKING',  # TRACKING | REBOUYING | IGNORE
        'rebuy_price': None,
        'last_price': sell_price,
        'highest_after_sell': sell_price,
    })
    save_sell_track(track)
    log(f"[跟踪] {name}({code}) 卖出后进入跟踪列表 | 卖出价{sell_price} | 原因:{reason}")


def get_prices(codes):
    """腾讯财经批量获取实时行情"""
    result = {}
    try:
        import urllib.request
        code_str = ','.join([
            ('sh' if c[0] in '569' else 'sz') + c for c in codes
        ])
        url = f"https://qt.gtimg.cn/q={code_str}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('gbk','ignore')
            for line in raw.split(';'):
                if '~' not in line:
                    continue
                parts = line.split('~')
                if len(parts) < 35:
                    continue
                m = line.split('"')
                if len(m) < 2:
                    continue
                code_full = m[1].split('=')[0] if '=' in m[1] else m[1]
                code = code_full.replace('sh','').replace('sz','')
                result[code] = {
                    'price': float(parts[3]),
                    'prev_close': float(parts[4]),
                    'open': float(parts[5]),
                    'high': float(parts[33]),
                    'low': float(parts[34]),
                    'pct': float(parts[32]) if parts[32] else 0,
                    'out_vol': int(parts[51]) if len(parts)>51 and parts[51].isdigit() else 0,
                    'in_vol': int(parts[52]) if len(parts)>52 and parts[52].isdigit() else 0,
                }
    except Exception as e:
        log(f"[行情] 获取失败: {e}")
    return result


def get_ma5(code):
    """获取MA5均线（使用腾讯接口）"""
    try:
        import urllib.request
        market = 'sh' if code[0] in '569' else 'sz'
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={market}{code},day,,,,,5,qfq&r=0.1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        import re, json as jsonmod
        m = re.search(r'=\s*(\{.*\})', raw)
        if not m:
            return None
        data = jsonmod.loads(m.group(1))
        day_data = data.get('data', {}).get(f'{market}{code}', {})
        qfqday = day_data.get('qfqday', []) or day_data.get('day', [])
        if len(qfqday) < 5:
            return None
        # 取最近5天收盘价
        closes = [float(d[2]) for d in qfqday[-5:]]
        ma5 = sum(closes) / 5
        return round(ma5, 2)
    except Exception as e:
        log(f"[MA5] 获取失败 {code}: {e}")
        return None


def get_ddx(code):
    """获取10日DDX（使用mx-data）"""
    try:
        import os
        os.environ['MX_APIKEY'] = 'mkt_TWs49QJsDQJn-tVRHqPwmdWmTFO5_vqSpwUPfN-Ti6M'
        sys.path.insert(0, r'C:\Users\zhuyi\.agents\skills\mx-data')
        from mx_data import MXData
        mx = MXData()
        result = mx.query(f'{code} 10日DDX')
        tables, _, _, err = mx.parse_result(result)
        if err or not tables:
            return None
        # 找到10日DDX列
        headers = tables[0].get('headers', [])
        rows = tables[0].get('rows', [])
        if not rows:
            return None
        # 找10日DDX列索引
        ddx_col = None
        for i, h in enumerate(headers):
            if '10日DDX' in str(h) or '10日ddx' in str(h).lower():
                ddx_col = i
                break
        if ddx_col is None:
            return None
        val = rows[-1][ddx_col] if len(rows[-1]) > ddx_col else None
        return float(val) if val is not None else None
    except Exception:
        return None


def check_stop_loss_wait(pos, cur):
    """检查止损等待窗口逻辑"""
    # 华工科技教训：止损触发后不在开盘最低点卖，等反弹再走
    # 规则：止损触发后，给60分钟反弹窗口（9:30~10:30）
    # 触发后价格反弹超过1%则不执行止损，等下一个信号
    # 触发后价格继续下跌则立即执行止损
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    triggered_at = pos.get('stop_loss_triggered_at')
    
    # 止损触发时间记录
    if triggered_at and cur <= pos.get('stop_loss_price', 0):
        # 已经在等待窗口中
        wait_minutes = RISK['stop_loss_wait_minutes']
        if triggered_at + wait_minutes * 60 <= now.timestamp():
            # 等待窗口结束，必须执行
            return 'EXECUTE_NOW'
        # 窗口内：检查反弹
        entry_price = pos.get('stop_loss_entry_price', cur)
        if cur >= entry_price * 1.005:  # 反弹超过0.5%
            return 'WAIT_REBOUND'  # 等更高反弹
        else:
            return 'CONTINUE_WAIT'  # 继续等待或立即执行
    return 'OK'


def check_position_v2(pos, price_data, today_date):
    """
    【v2.0核心改正】检查单个持仓的风控状态
    
    改正1: 止损线用MA5，不死板用固定-3%
    改正2: 止损触发后给60分钟反弹窗口（9:30~10:30），不在最低点割
    改正3: 持仓全程每日检查DDX，DDX转负立即预警
    """
    code = pos['code']
    name = pos['name']
    buy_price = pos['buy_price']
    qty = pos['qty']
    
    # 动态止损线（MA5）
    ma5 = pos.get('ma5')
    stop_loss_pct = RISK['stop_loss_pct']  # -5%
    stop_loss = pos.get('stop_loss')
    if stop_loss is None:
        stop_loss = buy_price * (1 - stop_loss_pct)
    
    take_profit = pos.get('take_profit', buy_price * (1 + RISK['take_profit_pct']))
    highest = pos.get('highest', buy_price)
    
    if code not in price_data:
        return {'code': code, 'name': name, 'status': 'NO_DATA', 'alerts': [], 'actions': []}
    
    pd = price_data[code]
    cur = pd['price']
    day_pct = pd['pct']
    pl_pct = (cur - buy_price) / buy_price
    
    # 更新最高价
    if cur > highest:
        highest = cur
        pos['highest'] = highest
    
    # 更新MA5
    if ma5 is None:
        ma5_val = get_ma5(code)
        if ma5_val:
            ma5 = ma5_val
            pos['ma5'] = ma5
            log(f"[{name}] 获取MA5={ma5}")
    
    alerts = []
    status = 'HOLD'
    actions = []
    
    # ========== 改正1: 止损线用MAX(MA5, 买入价*0.95) ==========
    effective_stop = max(ma5 or 0, buy_price * 0.95)
    if effective_stop > stop_loss:
        stop_loss = effective_stop
        pos['stop_loss'] = stop_loss
    
    # ========== 改正3: DDX每日检查 ==========
    ddx = pos.get('ddx_current')
    if ddx is None or (datetime.now().hour == 9 and datetime.now().minute < 35):
        ddx_val = get_ddx(code)
        if ddx_val is not None:
            ddx = ddx_val
            pos['ddx_current'] = ddx
            log(f"[{name}] 10日DDX={ddx}")
    
    # DDX预警
    if ddx is not None:
        if ddx <= RISK['ddx_exit_threshold']:
            alerts.append(f"🚨 DDX={ddx}持续流出! 机构在撤! 建议减仓!")
        elif ddx < 0:
            alerts.append(f"⚠️ DDX={ddx}转负，需密切关注")
    
    # ========== 止损逻辑 ==========
    stop_wait_status = check_stop_loss_wait(pos, cur)
    
    if cur <= stop_loss:
        if stop_wait_status == 'EXECUTE_NOW':
            alerts.append(f"🚨 止损执行! 跌破止损线! 现价{cur}<=止损{stop_loss:.2f}, 亏损{(pl_pct*100):.1f}%")
            status = 'STOP_LOSS'
            actions.append({'action': 'SELL_ALL', 'reason': f'止损(MA5={ma5})', 'price': cur})
        elif stop_wait_status == 'CONTINUE_WAIT':
            alerts.append(f"⚠️ 触及止损{stop_loss:.2f}! 继续下杀，60分钟内执行!")
            status = 'STOP_LOSS_PENDING'
            actions.append({'action': 'SELL_ALL', 'reason': f'止损(继续杀)', 'price': cur})
        else:
            alerts.append(f"⚠️ 触及止损{stop_loss:.2f}! 但价格反弹中，等候窗口!")
            status = 'STOP_LOSS_WAIT'
            # 记录止损触发时间
            if not pos.get('stop_loss_triggered_at'):
                pos['stop_loss_triggered_at'] = datetime.now().timestamp()
                pos['stop_loss_entry_price'] = cur
                alerts.append(f"⏰ 止损触发时间记录: 等60分钟窗口({datetime.now().strftime('%H:%M')} ~ {(datetime.now().timestamp() + 3600) and datetime.fromtimestamp(datetime.now().timestamp() + 3600).strftime('%H:%M')})")
    # ========== 止盈逻辑 ==========
    elif cur >= take_profit:
        alerts.append(f"🎯 达到止盈! 现价{cur:.2f}>=目标{take_profit:.2f}, 盈利{(pl_pct*100):.1f}%")
        status = 'TAKE_PROFIT'
        actions.append({'action': 'SELL_HALF', 'reason': '止盈卖半仓', 'price': cur})
    # ========== 移动止损(盈利8%以上后，从高点回撤3%) ==========
    elif pl_pct >= 0.08:
        drawdown = (highest - cur) / highest
        if drawdown >= RISK['trailing_stop_pct']:
            alerts.append(f"📉 移动止损! 从高点{highest:.2f}回撤{drawdown*100:.1f}%, 现价{cur:.2f}")
            status = 'TRAILING_STOP'
            actions.append({'action': 'SELL_ALL', 'reason': '移动止损', 'price': cur})
        else:
            alerts.append(f"📈 盈利中 {pl_pct*100:.1f}%, 高点{highest:.2f}, 回撤{drawdown*100:.1f}%")
            status = 'PROFIT'
    else:
        alerts.append(f"📊 持仓中 | 盈亏{pl_pct*100:+.1f}% | 止损线{stop_loss:.2f}(MA5={ma5})")
        status = 'HOLD'
    
    # 当日大跌预警
    if day_pct <= -RISK['day_loss_limit'] * 100:
        alerts.append(f"⚠️ 当日大跌{day_pct:.1f}%! 密切监控")
        if status == 'HOLD':
            status = 'DAY_DROP'
    
    # 当日大涨预警
    if day_pct >= RISK['day_gain_alert'] * 100:
        alerts.append(f"🔥 当日大涨{day_pct:.1f}%! 考虑部分止盈")
    
    # 外/内盘比
    if pd.get('in_vol', 0) > 0:
        out_in = pd['out_vol'] / pd['in_vol']
        if out_in < 0.8:
            alerts.append(f"💰 买盘强势! 外/内={out_in:.2f}")
        elif out_in > 1.5:
            alerts.append(f"⚠️ 卖盘主导! 外/内={out_in:.2f}")
    
    return {
        'code': code,
        'name': name,
        'cur': cur,
        'buy_price': buy_price,
        'qty': qty,
        'pl_pct': round(pl_pct * 100, 2),
        'day_pct': day_pct,
        'highest': highest,
        'ma5': ma5,
        'stop_loss': round(stop_loss, 2),
        'ddx': ddx,
        'status': status,
        'alerts': alerts,
        'actions': actions,
        'value': round(cur * qty, 0),
        'pl': round((cur - buy_price) * qty, 0),
    }


def check_sell_track(price_data, today_date):
    """
    【改正3核心】卖出后跟踪检查
    止损/卖出后3天内，每天检查是否企稳/反弹
    如果企稳且逻辑修复，提醒用户可以重新关注
    """
    track = load_sell_track()
    if not track.get('tracked'):
        return []
    
    tracked = track['tracked']
    new_alerts = []
    updated = False
    
    for item in tracked:
        if item.get('status') == 'IGNORE':
            continue
        code = item['code']
        name = item['name']
        sell_price = item['sell_price']
        
        if code not in price_data:
            continue
        
        cur = price_data[code]['price']
        sell_ts = item.get('sell_ts', 0)
        days_passed = (datetime.now().timestamp() - sell_ts) / 86400
        
        # 更新最高价
        if cur > item.get('highest_after_sell', sell_price):
            item['highest_after_sell'] = cur
        
        item['last_price'] = cur
        
        pct_change = (cur - sell_price) / sell_price * 100
        
        if days_passed > 3:
            item['status'] = 'IGNORE'
            new_alerts.append(f"⏰ {name}({code}) 卖出3天，跟踪结束 | 卖出{sell_price} | 现价{cur}({pct_change:+.1f}%)")
            updated = True
            continue
        
        # 检查是否企稳（从卖出低点反弹超过3%）
        rebound_pct = (cur - sell_price) / sell_price * 100
        
        if rebound_pct >= 3.0 and item['status'] != 'REBOUYING':
            item['status'] = 'REBOUYING'
            new_alerts.append(f"🐔 {name}({code}) 卖出后反弹{rebound_pct:+.1f}%! 企稳信号，建议重新关注! | 卖出{sell_price} → 现价{cur}")
            updated = True
        elif rebound_pct >= 1.0 and item['status'] == 'TRACKING':
            new_alerts.append(f"👁️ {name}({code}) 卖出后价格回升{rebound_pct:+.1f}% | 卖出{sell_price} → 现价{cur} | 继续观察")
        elif rebound_pct < -3.0:
            new_alerts.append(f"✅ {name}({code}) 卖出正确! 继续下跌{rebound_pct:.1f}% | 卖出{sell_price} → 现价{cur}")
    
    if updated:
        save_sell_track(track)
    
    return new_alerts


def check_account(positions_data, results):
    """账户级风控检查"""
    total_pl = sum(r.get('pl', 0) for r in results)
    total_value = sum(r.get('value', 0) for r in results)
    cash = positions_data.get('cash_reserve', 20000)
    total_capital = positions_data.get('total_capital', 100000)
    
    log(f"\n{'='*60}")
    log(f"  账户风控检查")
    log(f"{'='*60}")
    log(f"  总资金: {total_capital:,.0f}元 | 现金: {cash:,.0f}元 | 持仓市值: {total_value:,.0f}元")
    log(f"  总浮盈亏: {total_pl:+,.0f}元 ({total_pl/total_capital*100:+.1f}%)")
    
    day_loss_pct = total_pl / total_capital
    if day_loss_pct <= -0.02:
        log(f"  🚨 日亏损熔断! 当日亏损{day_loss_pct*100:.1f}%, 停止开新仓!")
    if day_loss_pct <= -0.05:
        log(f"  🚨 账户回撤{day_loss_pct*100:.1f}%超过5%! 减仓至半仓!")
    
    holding_count = len([r for r in results if r['status'] not in ['STOP_LOSS', 'NO_DATA']])
    if holding_count >= 5:
        log(f"  ⚠️ 持仓数{holding_count}只, 接近上限")
    
    return {
        'total_pl': total_pl,
        'total_value': total_value,
        'day_loss_pct': day_loss_pct,
        'holding_count': holding_count,
    }


def generate_monitor_report(results, account, today_date):
    """生成监控报告"""
    date_str = datetime.now().strftime('%Y-%m-%d_%H%M')
    report = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'holdings': results,
        'account': account,
        'alert_count': sum(len(r['alerts']) for r in results),
    }
    report_file = os.path.join(os.path.dirname(__file__), f'monitor_{date_str}.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    log("="*70)
    log("  持仓自动监控 v2.0 启动 [华工科技教训改正版]")
    log(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("  改正: ①止损线用MA5 ②止损等待反弹窗口 ③卖出后3天跟踪")
    log("="*70)
    
    positions_data = load_positions()
    if not positions_data:
        log("[ERR] 无法加载持仓, 退出")
        return
    
    holdings = positions_data.get('holdings', [])
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    if not holdings:
        log("[INFO] 当前无持仓")
    else:
        log(f"\n[持仓加载] 共 {len(holdings)} 只")
        codes = [p['code'] for p in holdings]
        prices = get_prices(codes)
        log(f"[行情获取] 成功 {len(prices)} 只")
        
        log(f"\n{'='*70}")
        log(f"  持仓风控检查")
        log(f"{'='*70}")
        log(f"{'代码':<8} {'名称':<8} {'现价':>7} {'成本':>7} {'MA5':>7} {'止损':>7} {'盈亏%':>7} {'DDX':>7} {'状态':>12}")
        log("-"*85)
        
        results = []
        for pos in holdings:
            res = check_position_v2(pos, prices, today_date)
            results.append(res)
            
            icons = {
                'HOLD': '➖', 'PROFIT': '📈', 'STOP_LOSS': '🚨', 'STOP_LOSS_PENDING': '🚨⏰',
                'STOP_LOSS_WAIT': '⏰', 'TAKE_PROFIT': '🎯', 'TRAILING_STOP': '📉',
                'DAY_DROP': '⚠️', 'DAY_SURGE': '🔥', 'NO_DATA': '❓'
            }.get(res['status'], '➖')
            
            log(f"{res['code']:<8} {res['name']:<8} {res.get('cur',0):>7.2f} "
                f"{res.get('buy_price',0):>7.2f} {res.get('ma5') or 0:>7.2f} "
                f"{res.get('stop_loss',0):>7.2f} {res.get('pl_pct',0):>+6.1f}% "
                f"{res.get('ddx') or 0:>+6.2f} {icons} {res['status']:<8}")
            
            for alert in res['alerts']:
                log(f"    → {alert}")
            for action in res.get('actions', []):
                log(f"    ★ 建议: {action['action']} @ {action['price']:.2f} | {action['reason']}")
        
        account = check_account(positions_data, results)
        
        # 【改正3】检查卖出后跟踪
        sell_alerts = check_sell_track(prices, today_date)
        if sell_alerts:
            log(f"\n{'='*70}")
            log(f"  卖出后跟踪检查 🔄")
            log(f"{'='*70}")
            for a in sell_alerts:
                log(f"  {a}")
        
        save_positions(positions_data)
        report = generate_monitor_report(results, account, today_date)
        
        action_count = sum(len(r.get('actions', [])) for r in results)
        log(f"\n{'='*70}")
        log(f"  监控完成 | 持仓:{len(results)}只 | 预警:{report['alert_count']}条 | 建议操作:{action_count}条")
        log(f"{'='*70}")
        
        if action_count > 0:
            log("\n[紧急操作清单]")
            for r in results:
                for a in r['actions']:
                    log(f"  🚨 {r['name']}({r['code']}): {a['action']} @ {a['price']:.2f} | {a['reason']}")
    
    return report


if __name__ == '__main__':
    main()
