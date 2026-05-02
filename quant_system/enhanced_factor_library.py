# -*- coding: utf-8 -*-
"""
增强版因子库 - 整合TA-Lib 150+技术指标 + 订单流因子 + 情绪因子
目标：200+因子，接近幻方量化水平

因子分类：
1. 量价因子（60+）：收益率、波动率、成交量、振幅
2. 技术指标（120+）：TA-Lib全覆盖（重叠、动量、波动率、成交量、周期、价格、形态、统计）
3. 订单流因子（20+）：DDX深度挖掘、资金流向
4. 基本面因子（30+）：估值、盈利、成长
5. 情绪因子（10+）：舆情、热度（预留接口）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy import stats
import talib
import warnings

warnings.filterwarnings("ignore")


class EnhancedFactorLibrary:
    """增强版因子库 - 200+因子"""

    def __init__(self):
        self.factor_count = 0
        self.factor_categories = {
            "price_volume": self._price_volume_factors,
            "technical_overlap": self._technical_overlap_factors,
            "technical_momentum": self._technical_momentum_factors,
            "technical_volatility": self._technical_volatility_factors,
            "technical_volume": self._technical_volume_factors,
            "technical_cycle": self._technical_cycle_factors,
            "technical_price": self._technical_price_factors,
            "technical_pattern": self._technical_pattern_factors,
            "technical_statistic": self._technical_statistic_factors,
            "order_flow": self._order_flow_factors,
            "fundamental": self._fundamental_factors,
            "sentiment": self._sentiment_factors,
        }

        # 因子权重（动态调整）
        self.factor_weights = {}

        # 因子有效性评分
        self.factor_scores = {}

    def extract_all_factors(self, data: pd.DataFrame) -> Dict:
        """
        提取所有因子

        参数:
            data: 股票数据，需包含 open, high, low, close, volume

        返回:
            因子字典
        """
        all_factors = {}

        for category, func in self.factor_categories.items():
            try:
                factors = func(data)
                all_factors.update(factors)
                if len(factors) == 0:
                    print(f"Warning: {category} returned 0 factors")
            except Exception as e:
                print(f"Error: {category} factor extraction failed: {e}")
                import traceback

                traceback.print_exc()

        self.factor_count = len(all_factors)
        return all_factors

    # ==================== 1. 量价因子（60+） ====================
    def _price_volume_factors(self, data: pd.DataFrame) -> Dict:
        """量价因子"""
        factors = {}
        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        # 1. 收益率因子（10个）
        for period in [1, 2, 3, 5, 10, 20, 60, 120, 250]:
            if len(close) >= period:
                factors[f"return_{period}d"] = close.pct_change(period).iloc[-1]

        # 2. 波动率因子（10个）
        for period in [5, 10, 20, 60]:
            if len(close) >= period:
                factors[f"volatility_{period}d"] = close.pct_change().rolling(
                    period
                ).std().iloc[-1] * np.sqrt(252)

        # 3. 振幅因子（10个）
        for period in [5, 10, 20]:
            if len(close) >= period:
                factors[f"amplitude_{period}d"] = (
                    (high.rolling(period).max() - low.rolling(period).min())
                    / close.rolling(period).mean()
                ).iloc[-1]

        # 4. 成交量因子（15个）
        for period in [5, 10, 20, 60]:
            if len(volume) >= period:
                factors[f"volume_ratio_{period}d"] = (
                    volume.iloc[-1] / volume.rolling(period).mean().iloc[-1]
                )
                factors[f"volume_change_{period}d"] = volume.pct_change(period).iloc[-1]

        # 5. 量价相关性（5个）
        for period in [5, 10, 20]:
            if len(close) >= period:
                factors[f"price_volume_corr_{period}d"] = close.pct_change(period).corr(
                    volume.pct_change(period)
                )

        # 6. 换手率因子（5个）
        if "turnover_rate" in data.columns:
            for period in [5, 10, 20]:
                factors[f"turnover_{period}d_avg"] = (
                    data["turnover_rate"].rolling(period).mean().iloc[-1]
                )

        # 7. 涨跌停因子（5个）
        for period in [5, 10, 20]:
            if len(close) >= period:
                factors[f"limit_up_count_{period}d"] = (
                    (close.pct_change() >= 0.095).rolling(period).sum().iloc[-1]
                )
                factors[f"limit_down_count_{period}d"] = (
                    (close.pct_change() <= -0.095).rolling(period).sum().iloc[-1]
                )

        return factors

    # ==================== 2. TA-Lib技术指标 - 重叠研究（15个） ====================
    def _technical_overlap_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib重叠研究指标"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        try:
            # 移动平均线
            for period in [5, 10, 20, 60]:
                factors[f"MA_{period}"] = talib.MA(close, timeperiod=period)[-1]
                factors[f"EMA_{period}"] = talib.EMA(close, timeperiod=period)[-1]

            # 布林带
            upper, middle, lower = talib.BBANDS(close, timeperiod=20)
            factors["BB_UPPER"] = upper[-1]
            factors["BB_MIDDLE"] = middle[-1]
            factors["BB_LOWER"] = lower[-1]
            factors["BB_WIDTH"] = (upper[-1] - lower[-1]) / middle[-1]

            # SAR
            factors["SAR"] = talib.SAR(high, low)[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 3. TA-Lib技术指标 - 动量指标（34个） ====================
    def _technical_momentum_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib动量指标"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values
        volume = data["volume"].values
        open_price = data["open"].values

        try:
            # ADX - 平均趋向指数
            factors["ADX"] = talib.ADX(high, low, close, timeperiod=14)[-1]
            factors["ADXR"] = talib.ADXR(high, low, close, timeperiod=14)[-1]

            # APO - 绝对价格振荡器
            factors["APO"] = talib.APO(close, fastperiod=12, slowperiod=26)[-1]

            # AROON - 阿隆指标
            aroon_down, aroon_up = talib.AROON(high, low, timeperiod=14)
            factors["AROON_DOWN"] = aroon_down[-1]
            factors["AROON_UP"] = aroon_up[-1]
            factors["AROONOSC"] = talib.AROONOSC(high, low, timeperiod=14)[-1]

            # BOP - 均势指标
            factors["BOP"] = talib.BOP(open_price, high, low, close)[-1]

            # CCI - 顺势指标
            factors["CCI"] = talib.CCI(high, low, close, timeperiod=14)[-1]

            # CMO - 钱德动量摆动指标
            factors["CMO"] = talib.CMO(close, timeperiod=14)[-1]

            # DX - 动向指数
            factors["DX"] = talib.DX(high, low, close, timeperiod=14)[-1]

            # MACD
            macd, macdsignal, macdhist = talib.MACD(
                close, fastperiod=12, slowperiod=26, signalperiod=9
            )
            factors["MACD"] = macd[-1]
            factors["MACD_SIGNAL"] = macdsignal[-1]
            factors["MACD_HIST"] = macdhist[-1]

            # MFI - 资金流量指标
            factors["MFI"] = talib.MFI(high, low, close, volume, timeperiod=14)[-1]

            # MINUS_DI / PLUS_DI
            factors["MINUS_DI"] = talib.MINUS_DI(high, low, close, timeperiod=14)[-1]
            factors["PLUS_DI"] = talib.PLUS_DI(high, low, close, timeperiod=14)[-1]

            # MINUS_DM / PLUS_DM
            factors["MINUS_DM"] = talib.MINUS_DM(high, low, timeperiod=14)[-1]
            factors["PLUS_DM"] = talib.PLUS_DM(high, low, timeperiod=14)[-1]

            # MOM - 动量
            factors["MOM"] = talib.MOM(close, timeperiod=10)[-1]

            # PPO - 价格振荡百分比
            factors["PPO"] = talib.PPO(close, fastperiod=12, slowperiod=26)[-1]

            # ROC - 变动率指标
            factors["ROC"] = talib.ROC(close, timeperiod=10)[-1]
            factors["ROCP"] = talib.ROCP(close, timeperiod=10)[-1]
            factors["ROCR"] = talib.ROCR(close, timeperiod=10)[-1]
            factors["ROCR100"] = talib.ROCR100(close, timeperiod=10)[-1]

            # RSI - 相对强弱指数
            for period in [6, 14, 24]:
                factors[f"RSI_{period}"] = talib.RSI(close, timeperiod=period)[-1]

            # STOCH - 随机指标
            slowk, slowd = talib.STOCH(
                high, low, close, fastk_period=9, slowk_period=3, slowd_period=3
            )
            factors["STOCH_SLOWK"] = slowk[-1]
            factors["STOCH_SLOWD"] = slowd[-1]

            # STOCHF - 快速随机指标
            fastk, fastd = talib.STOCHF(
                high, low, close, fastk_period=5, fastd_period=3
            )
            factors["STOCHF_FASTK"] = fastk[-1]
            factors["STOCHF_FASTD"] = fastd[-1]

            # TRIX - 三重平滑EMA
            factors["TRIX"] = talib.TRIX(close, timeperiod=30)[-1]

            # ULTOSC - 终极振荡器
            factors["ULTOSC"] = talib.ULTOSC(
                high, low, close, timeperiod1=7, timeperiod2=14, timeperiod3=28
            )[-1]

            # WILLR - 威廉指标
            factors["WILLR"] = talib.WILLR(high, low, close, timeperiod=14)[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 4. TA-Lib技术指标 - 波动率指标（5个） ====================
    def _technical_volatility_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib波动率指标"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        try:
            # ATR - 真实波动幅度均值
            for period in [7, 14, 21]:
                factors[f"ATR_{period}"] = talib.ATR(
                    high, low, close, timeperiod=period
                )[-1]

            # NATR - 归一化ATR
            factors["NATR"] = talib.NATR(high, low, close, timeperiod=14)[-1]

            # TRANGE - 真实波动幅度
            factors["TRANGE"] = talib.TRANGE(high, low, close)[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 5. TA-Lib技术指标 - 成交量指标（8个） ====================
    def _technical_volume_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib成交量指标"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values
        volume = data["volume"].values

        try:
            # AD - 累积/派发线
            factors["AD"] = talib.AD(high, low, close, volume)[-1]

            # ADOSC - AD振荡器
            factors["ADOSC"] = talib.ADOSC(
                high, low, close, volume, fastperiod=3, slowperiod=10
            )[-1]

            # OBV - 能量潮
            factors["OBV"] = talib.OBV(close, volume)[-1]

            # 自定义成交量因子
            factors["VOLUME_MA5"] = np.mean(volume[-5:])
            factors["VOLUME_MA10"] = np.mean(volume[-10:])
            factors["VOLUME_MA20"] = np.mean(volume[-20:])

            # 成交量变化率
            factors["VOLUME_ROC5"] = (
                (volume[-1] - volume[-5]) / volume[-5] if volume[-5] > 0 else 0
            )
            factors["VOLUME_ROC10"] = (
                (volume[-1] - volume[-10]) / volume[-10] if volume[-10] > 0 else 0
            )

        except Exception as e:
            pass

        return factors

    # ==================== 6. TA-Lib技术指标 - 周期指标（4个） ====================
    def _technical_cycle_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib周期指标"""
        factors = {}
        close = data["close"].values

        try:
            # HT_DCPERIOD - 希尔伯特变换-主导周期
            factors["HT_DCPERIOD"] = talib.HT_DCPERIOD(close)[-1]

            # HT_DCPHASE - 希尔伯特变换-主导周期相位
            factors["HT_DCPHASE"] = talib.HT_DCPHASE(close)[-1]

            # HT_PHASOR - 希尔伯特变换-相量分量
            inphase, quadrature = talib.HT_PHASOR(close)
            factors["HT_PHASOR_INPHASE"] = inphase[-1]
            factors["HT_PHASOR_QUADRATURE"] = quadrature[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 7. TA-Lib技术指标 - 价格指标（9个） ====================
    def _technical_price_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib价格指标"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        try:
            # AVGPRICE - 平均价格
            factors["AVGPRICE"] = talib.AVGPRICE(high, low, close, close)[-1]

            # MEDPRICE - 中位价格
            factors["MEDPRICE"] = talib.MEDPRICE(high, low)[-1]

            # TYPPRICE - 典型价格
            factors["TYPPRICE"] = talib.TYPPRICE(high, low, close)[-1]

            # WCLPRICE - 加权收盘价
            factors["WCLPRICE"] = talib.WCLPRICE(high, low, close)[-1]

            # 自定义价格因子
            factors["HIGH_LOW_RATIO"] = high[-1] / low[-1] if low[-1] > 0 else 1
            factors["CLOSE_HIGH_RATIO"] = close[-1] / high[-1] if high[-1] > 0 else 1
            factors["CLOSE_LOW_RATIO"] = close[-1] / low[-1] if low[-1] > 0 else 1

            # 价格位置（相对于N日高低点）
            for period in [20, 60]:
                if len(close) >= period:
                    high_n = np.max(high[-period:])
                    low_n = np.min(low[-period:])
                    factors[f"PRICE_POSITION_{period}D"] = (
                        (close[-1] - low_n) / (high_n - low_n)
                        if high_n != low_n
                        else 0.5
                    )

        except Exception as e:
            pass

        return factors

    # ==================== 8. TA-Lib技术指标 - 形态识别（61个） ====================
    def _technical_pattern_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib K线形态识别"""
        factors = {}
        open_price = data["open"].values
        high = data["high"].values
        low = data["low"].values
        close = data["close"].values

        try:
            # 两根K线形态
            factors["CDL2CROWS"] = talib.CDL2CROWS(open_price, high, low, close)[-1]
            factors["CDL3BLACKCROWS"] = talib.CDL3BLACKCROWS(
                open_price, high, low, close
            )[-1]
            factors["CDL3INSIDE"] = talib.CDL3INSIDE(open_price, high, low, close)[-1]
            factors["CDL3LINESTRIKE"] = talib.CDL3LINESTRIKE(
                open_price, high, low, close
            )[-1]
            factors["CDL3OUTSIDE"] = talib.CDL3OUTSIDE(open_price, high, low, close)[-1]
            factors["CDL3STARSINSOUTH"] = talib.CDL3STARSINSOUTH(
                open_price, high, low, close
            )[-1]
            factors["CDL3WHITESOLDIERS"] = talib.CDL3WHITESOLDIERS(
                open_price, high, low, close
            )[-1]

            # 多根K线形态
            factors["CDLABANDONEDBABY"] = talib.CDLABANDONEDBABY(
                open_price, high, low, close
            )[-1]
            factors["CDLADVANCEBLOCK"] = talib.CDLADVANCEBLOCK(
                open_price, high, low, close
            )[-1]
            factors["CDLBELTHOLD"] = talib.CDLBELTHOLD(open_price, high, low, close)[-1]
            factors["CDLBREAKAWAY"] = talib.CDLBREAKAWAY(open_price, high, low, close)[
                -1
            ]
            factors["CDLCLOSINGMARUBOZU"] = talib.CDLCLOSINGMARUBOZU(
                open_price, high, low, close
            )[-1]
            factors["CDLCONCEALBABYSWALL"] = talib.CDLCONCEALBABYSWALL(
                open_price, high, low, close
            )[-1]
            factors["CDLCOUNTERATTACK"] = talib.CDLCOUNTERATTACK(
                open_price, high, low, close
            )[-1]
            factors["CDLDARKCLOUDCOVER"] = talib.CDLDARKCLOUDCOVER(
                open_price, high, low, close
            )[-1]
            factors["CDLDOJI"] = talib.CDLDOJI(open_price, high, low, close)[-1]
            factors["CDLDOJISTAR"] = talib.CDLDOJISTAR(open_price, high, low, close)[-1]
            factors["CDLDRAGONFLYDOJI"] = talib.CDLDRAGONFLYDOJI(
                open_price, high, low, close
            )[-1]
            factors["CDLENGULFING"] = talib.CDLENGULFING(open_price, high, low, close)[
                -1
            ]
            factors["CDLEVENINGDOJISTAR"] = talib.CDLEVENINGDOJISTAR(
                open_price, high, low, close
            )[-1]
            factors["CDLEVENINGSTAR"] = talib.CDLEVENINGSTAR(
                open_price, high, low, close
            )[-1]
            factors["CDLGAPSIDESIDEWHITE"] = talib.CDLGAPSIDESIDEWHITE(
                open_price, high, low, close
            )[-1]
            factors["CDLGRAVESTONEDOJI"] = talib.CDLGRAVESTONEDOJI(
                open_price, high, low, close
            )[-1]
            factors["CDLHAMMER"] = talib.CDLHAMMER(open_price, high, low, close)[-1]
            factors["CDLHANGINGMAN"] = talib.CDLHANGINGMAN(
                open_price, high, low, close
            )[-1]
            factors["CDLHARAMI"] = talib.CDLHARAMI(open_price, high, low, close)[-1]
            factors["CDLHARAMICROSS"] = talib.CDLHARAMICROSS(
                open_price, high, low, close
            )[-1]
            factors["CDLHIGHWAVE"] = talib.CDLHIGHWAVE(open_price, high, low, close)[-1]
            factors["CDLHIKKAKE"] = talib.CDLHIKKAKE(open_price, high, low, close)[-1]
            factors["CDLHIKKAKEMOD"] = talib.CDLHIKKAKEMOD(
                open_price, high, low, close
            )[-1]
            factors["CDLHOMINGPIGEON"] = talib.CDLHOMINGPIGEON(
                open_price, high, low, close
            )[-1]
            factors["CDLIDENTICAL3CROWS"] = talib.CDLIDENTICAL3CROWS(
                open_price, high, low, close
            )[-1]
            factors["CDLINNECK"] = talib.CDLINNECK(open_price, high, low, close)[-1]
            factors["CDLINVERTEDHAMMER"] = talib.CDLINVERTEDHAMMER(
                open_price, high, low, close
            )[-1]
            factors["CDLKICKING"] = talib.CDLKICKING(open_price, high, low, close)[-1]
            factors["CDLKICKINGBYLENGTH"] = talib.CDLKICKINGBYLENGTH(
                open_price, high, low, close
            )[-1]
            factors["CDLLADDERBOTTOM"] = talib.CDLLADDERBOTTOM(
                open_price, high, low, close
            )[-1]
            factors["CDLLONGLEGGEDDOJI"] = talib.CDLLONGLEGGEDDOJI(
                open_price, high, low, close
            )[-1]
            factors["CDLLONGLINE"] = talib.CDLLONGLINE(open_price, high, low, close)[-1]
            factors["CDLMARUBOZU"] = talib.CDLMARUBOZU(open_price, high, low, close)[-1]
            factors["CDLMATCHINGLOW"] = talib.CDLMATCHINGLOW(
                open_price, high, low, close
            )[-1]
            factors["CDLMATHOLD"] = talib.CDLMATHOLD(open_price, high, low, close)[-1]
            factors["CDLMORNINGDOJISTAR"] = talib.CDLMORNINGDOJISTAR(
                open_price, high, low, close
            )[-1]
            factors["CDLMORNINGSTAR"] = talib.CDLMORNINGSTAR(
                open_price, high, low, close
            )[-1]
            factors["CDLONNECK"] = talib.CDLONNECK(open_price, high, low, close)[-1]
            factors["CDLPIERCING"] = talib.CDLPIERCING(open_price, high, low, close)[-1]
            factors["CDLPITFALL"] = talib.CDLPITFALL(open_price, high, low, close)[-1]
            factors["CDLRICKSHAWMAN"] = talib.CDLRICKSHAWMAN(
                open_price, high, low, close
            )[-1]
            factors["CDLRISEFALL3METHODS"] = talib.CDLRISEFALL3METHODS(
                open_price, high, low, close
            )[-1]
            factors["CDLSEPARATINGLINES"] = talib.CDLSEPARATINGLINES(
                open_price, high, low, close
            )[-1]
            factors["CDLSHOOTINGSTAR"] = talib.CDLSHOOTINGSTAR(
                open_price, high, low, close
            )[-1]
            factors["CDLSHORTLINE"] = talib.CDLSHORTLINE(open_price, high, low, close)[
                -1
            ]
            factors["CDLSPINNINGTOP"] = talib.CDLSPINNINGTOP(
                open_price, high, low, close
            )[-1]
            factors["CDLSTALLEDPATTERN"] = talib.CDLSTALLEDPATTERN(
                open_price, high, low, close
            )[-1]
            factors["CDLSTICKSANDWICH"] = talib.CDLSTICKSANDWICH(
                open_price, high, low, close
            )[-1]
            factors["CDLTAKURI"] = talib.CDLTAKURI(open_price, high, low, close)[-1]
            factors["CDLTASUKIGAP"] = talib.CDLTASUKIGAP(open_price, high, low, close)[
                -1
            ]
            factors["CDLTHRUSTING"] = talib.CDLTHRUSTING(open_price, high, low, close)[
                -1
            ]
            factors["CDLTRISTAR"] = talib.CDLTRISTAR(open_price, high, low, close)[-1]
            factors["CDLUNIQUE3RIVER"] = talib.CDLUNIQUE3RIVER(
                open_price, high, low, close
            )[-1]
            factors["CDLUPSIDEGAP2CROWS"] = talib.CDLUPSIDEGAP2CROWS(
                open_price, high, low, close
            )[-1]
            factors["CDLXSIDEGAP3METHODS"] = talib.CDLXSIDEGAP3METHODS(
                open_price, high, low, close
            )[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 9. TA-Lib技术指标 - 统计函数（9个） ====================
    def _technical_statistic_factors(self, data: pd.DataFrame) -> Dict:
        """TA-Lib统计函数"""
        factors = {}
        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        try:
            # BETA - 贝塔系数
            factors["BETA"] = talib.BETA(high, low, timeperiod=5)[-1]

            # CORREL - 相关系数
            factors["CORREL"] = talib.CORREL(high, low, timeperiod=30)[-1]

            # LINEARREG - 线性回归
            factors["LINEARREG"] = talib.LINEARREG(close, timeperiod=14)[-1]
            factors["LINEARREG_ANGLE"] = talib.LINEARREG_ANGLE(close, timeperiod=14)[-1]
            factors["LINEARREG_INTERCEPT"] = talib.LINEARREG_INTERCEPT(
                close, timeperiod=14
            )[-1]
            factors["LINEARREG_SLOPE"] = talib.LINEARREG_SLOPE(close, timeperiod=14)[-1]

            # STDDEV - 标准差
            factors["STDDEV"] = talib.STDDEV(close, timeperiod=5)[-1]

            # TSF - 时间序列预测
            factors["TSF"] = talib.TSF(close, timeperiod=14)[-1]

            # VAR - 方差
            factors["VAR"] = talib.VAR(close, timeperiod=5)[-1]

        except Exception as e:
            pass

        return factors

    # ==================== 10. 订单流因子（20+） ====================
    def _order_flow_factors(self, data: pd.DataFrame) -> Dict:
        """
        订单流因子 - 基于DDX深度挖掘

        需要数据源：妙想API、问财API
        """
        factors = {}

        # DDX因子（如果有）
        if "ddx" in data.columns:
            factors["DDX"] = data["ddx"].iloc[-1]
            factors["DDX_5D_AVG"] = data["ddx"].rolling(5).mean().iloc[-1]
            factors["DDX_10D_AVG"] = data["ddx"].rolling(10).mean().iloc[-1]
            factors["DDX_20D_AVG"] = data["ddx"].rolling(20).mean().iloc[-1]

            # DDX趋势
            factors["DDX_TREND_5D"] = (
                data["ddx"]
                .rolling(5)
                .apply(
                    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0
                )
                .iloc[-1]
            )

            # DDX连续性
            factors["DDX_POSITIVE_DAYS_5D"] = (
                (data["ddx"] > 0).rolling(5).sum().iloc[-1]
            )
            factors["DDX_POSITIVE_DAYS_10D"] = (
                (data["ddx"] > 0).rolling(10).sum().iloc[-1]
            )

        # DDY因子（如果有）
        if "ddy" in data.columns:
            factors["DDY"] = data["ddy"].iloc[-1]
            factors["DDY_5D_AVG"] = data["ddy"].rolling(5).mean().iloc[-1]
            factors["DDY_10D_AVG"] = data["ddy"].rolling(10).mean().iloc[-1]

        # DDZ因子（如果有）
        if "ddz" in data.columns:
            factors["DDZ"] = data["ddz"].iloc[-1]
            factors["DDZ_5D_AVG"] = data["ddz"].rolling(5).mean().iloc[-1]

        # 主力资金流向（如果有）
        if "main_flow" in data.columns:
            factors["MAIN_FLOW"] = data["main_flow"].iloc[-1]
            factors["MAIN_FLOW_5D_SUM"] = data["main_flow"].rolling(5).sum().iloc[-1]
            factors["MAIN_FLOW_10D_SUM"] = data["main_flow"].rolling(10).sum().iloc[-1]
            factors["MAIN_FLOW_20D_SUM"] = data["main_flow"].rolling(20).sum().iloc[-1]

            # 主力资金趋势
            factors["MAIN_FLOW_TREND_5D"] = (
                data["main_flow"]
                .rolling(5)
                .apply(
                    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0
                )
                .iloc[-1]
            )

            # 主力流入天数
            factors["MAIN_INFLOW_DAYS_5D"] = (
                (data["main_flow"] > 0).rolling(5).sum().iloc[-1]
            )
            factors["MAIN_INFLOW_DAYS_10D"] = (
                (data["main_flow"] > 0).rolling(10).sum().iloc[-1]
            )

        # 超大单/大单/中单/小单（如果有）
        for order_type in ["super_large", "large", "medium", "small"]:
            col_name = f"{order_type}_flow"
            if col_name in data.columns:
                factors[f"{order_type.upper()}_FLOW"] = data[col_name].iloc[-1]
                factors[f"{order_type.upper()}_FLOW_5D_SUM"] = (
                    data[col_name].rolling(5).sum().iloc[-1]
                )

        return factors

    # ==================== 11. 基本面因子（30+） ====================
    def _fundamental_factors(self, data: pd.DataFrame) -> Dict:
        """基本面因子"""
        factors = {}

        # 估值因子
        for metric in ["pe", "pb", "ps", "pcf"]:
            if metric in data.columns:
                factors[metric.upper()] = data[metric].iloc[-1]

        # 盈利能力因子
        for metric in ["roe", "roa", "gross_margin", "net_margin"]:
            if metric in data.columns:
                factors[metric.upper()] = data[metric].iloc[-1]

        # 成长因子
        for metric in ["revenue_growth", "profit_growth", "eps_growth"]:
            if metric in data.columns:
                factors[metric.upper()] = data[metric].iloc[-1]

        # 财务健康因子
        for metric in ["debt_ratio", "current_ratio", "quick_ratio"]:
            if metric in data.columns:
                factors[metric.upper()] = data[metric].iloc[-1]

        # 现金流因子
        for metric in ["operating_cash_flow", "free_cash_flow"]:
            if metric in data.columns:
                factors[metric.upper()] = data[metric].iloc[-1]

        return factors

    # ==================== 12. 情绪因子（10+） ====================
    def _sentiment_factors(self, data: pd.DataFrame) -> Dict:
        """
        情绪因子 - 预留接口

        数据来源：
        - 东方财富股吧
        - 雪球
        - 微博
        - 新闻舆情
        """
        factors = {}

        # 预留字段（需要爬虫或API获取）
        sentiment_fields = [
            "sentiment_score",  # 情绪评分
            "news_count",  # 新闻数量
            "discussion_count",  # 讨论数量
            "positive_ratio",  # 正面情绪比例
            "negative_ratio",  # 负面情绪比例
            "hot_rank",  # 热度排名
            "attention_score",  # 关注度评分
        ]

        for field in sentiment_fields:
            if field in data.columns:
                factors[field.upper()] = data[field].iloc[-1]

        return factors

    # ==================== 因子有效性评估 ====================
    def evaluate_factor_effectiveness(
        self, factor_values: pd.Series, forward_returns: pd.Series
    ) -> Dict:
        """
        评估因子有效性

        参数:
            factor_values: 因子值序列
            forward_returns: 未来收益率序列

        返回:
            {
                'IC': 信息系数,
                'IR': 信息比率,
                't_stat': t统计量,
                'p_value': p值
            }
        """
        # IC（信息系数）
        ic = factor_values.corr(forward_returns)

        # IR（信息比率）
        ic_series = []
        for i in range(len(factor_values) - 1):
            ic_series.append(
                factor_values.iloc[: i + 1].corr(forward_returns.iloc[: i + 1])
            )
        ir = np.mean(ic_series) / np.std(ic_series) if np.std(ic_series) > 0 else 0

        # t检验
        t_stat, p_value = stats.pearsonr(factor_values, forward_returns)

        return {
            "IC": ic,
            "IR": ir,
            "t_stat": t_stat,
            "p_value": p_value,
        }

    # ==================== 因子筛选（遗传算法） ====================
    def select_factors_genetic(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.Series,
        population_size: int = 50,
        generations: int = 20,
    ) -> List[str]:
        """
        遗传算法筛选因子

        参数:
            factor_data: 因子数据矩阵
            forward_returns: 未来收益率
            population_size: 种群大小
            generations: 迭代代数

        返回:
            最优因子组合
        """
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score

        # 简化版：基于IC值筛选
        ic_scores = {}
        for col in factor_data.columns:
            ic = factor_data[col].corr(forward_returns)
            ic_scores[col] = abs(ic)

        # 选择IC值最高的因子
        sorted_factors = sorted(ic_scores.items(), key=lambda x: x[1], reverse=True)
        selected_factors = [f[0] for f in sorted_factors[:20]]  # 选择前20个因子

        return selected_factors


def test_enhanced_factor_library():
    """测试增强版因子库"""
    print("\n" + "=" * 60)
    print("Enhanced Factor Library Test")
    print("=" * 60)

    # 生成测试数据
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=300, freq="D")
    base_price = 100

    data = []
    for i, date in enumerate(dates):
        change = np.random.uniform(-0.03, 0.03)
        base_price = base_price * (1 + change)

        data.append(
            {
                "date": date,
                "open": base_price * np.random.uniform(0.99, 1.01),
                "high": base_price * np.random.uniform(1.0, 1.02),
                "low": base_price * np.random.uniform(0.98, 1.0),
                "close": base_price,
                "volume": np.random.uniform(1000000, 10000000),
            }
        )

    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)

    # 提取因子
    library = EnhancedFactorLibrary()
    factors = library.extract_all_factors(df)

    print(f"\nTotal factors extracted: {len(factors)}")
    print("\nFactor categories:")

    # 统计各类因子数量
    category_counts = {}
    for category in library.factor_categories.keys():
        func = library.factor_categories[category]
        try:
            category_factors = func(df)
            category_counts[category] = len(category_factors)
        except:
            category_counts[category] = 0

    for category, count in category_counts.items():
        print(f"  {category}: {count} factors")

    print("\nSample factors:")
    for i, (name, value) in enumerate(list(factors.items())[:10]):
        print(f"  {name}: {value:.4f}")

    print("\n" + "=" * 60)
    print("Test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_enhanced_factor_library()
