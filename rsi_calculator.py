"""
RSI 지표 계산 모듈
"""
import pandas as pd
import numpy as np
from typing import Tuple


class RSICalculator:
    """RSI(Relative Strength Index) 계산 클래스"""
    
    # 추세 강도 판단 기준 (%)
    STRONG_TREND_PRICE_THRESHOLD = 5.0  # 가격이 MA20보다 5% 이상 위/아래
    STRONG_TREND_MA_THRESHOLD = 3.0     # MA20이 MA50보다 3% 이상 위/아래
    
    def __init__(self, short_period: int = 9, medium_period: int = 14, long_period: int = 26):
        """
        RSICalculator 초기화
        
        Args:
            short_period: 단기 RSI 기간 (기본: 9일)
            medium_period: 중기 RSI 기간 (기본: 14일)
            long_period: 장기 RSI 기간 (기본: 26일)
        """
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        RSI를 계산합니다.
        
        Args:
            data: 주식 데이터 DataFrame (Close 컬럼 필요)
            period: RSI 계산 기간
            
        Returns:
            RSI 값이 포함된 pandas Series
        """
        if 'Close' not in data.columns:
            raise ValueError("DataFrame must contain 'Close' column")
        
        # 가격 변화량 계산
        delta = data['Close'].diff()
        
        # 상승과 하락 분리
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        # 평균 상승/하락 계산 (EMA 사용)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # RS (Relative Strength) 계산
        rs = avg_gain / avg_loss
        
        # RSI 계산
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_all_rsi(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        단기, 중기, 장기 RSI를 모두 계산합니다.
        
        Args:
            data: 주식 데이터 DataFrame
            
        Returns:
            RSI 값들이 추가된 DataFrame
        """
        result = data.copy()
        
        # 3개의 RSI 계산
        result['RSI_Short'] = self.calculate_rsi(data, self.short_period)
        result['RSI_Medium'] = self.calculate_rsi(data, self.medium_period)
        result['RSI_Long'] = self.calculate_rsi(data, self.long_period)
        
        return result
    
    def get_latest_rsi_values(self, data: pd.DataFrame) -> Tuple[float, float, float]:
        """
        최신 RSI 값들을 반환합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            
        Returns:
            (단기 RSI, 중기 RSI, 장기 RSI) tuple
        """
        if data.empty:
            return None, None, None
        
        short_rsi = data['RSI_Short'].iloc[-1] if 'RSI_Short' in data.columns else None
        medium_rsi = data['RSI_Medium'].iloc[-1] if 'RSI_Medium' in data.columns else None
        long_rsi = data['RSI_Long'].iloc[-1] if 'RSI_Long' in data.columns else None
        
        return short_rsi, medium_rsi, long_rsi
    
    def detect_rsi_reversal(self, data: pd.DataFrame, rsi_column: str, lookback: int = 2) -> str:
        """
        RSI 반전 감지 (상승 반전 또는 하락 반전)
        
        Args:
            data: RSI가 계산된 DataFrame
            rsi_column: RSI 컬럼 이름
            lookback: 반전 확인을 위한 이전 기간
            
        Returns:
            'up' (상승 반전), 'down' (하락 반전), 'none' (반전 없음)
        """
        if rsi_column not in data.columns or len(data) < lookback + 1:
            return 'none'
        
        recent_values = data[rsi_column].iloc[-(lookback+1):].values
        
        if len(recent_values) < lookback + 1 or np.any(np.isnan(recent_values)):
            return 'none'
        
        # 상승 반전: 이전에 하락하다가 최근 상승
        if recent_values[-1] > recent_values[-2]:
            if all(recent_values[i] >= recent_values[i+1] for i in range(len(recent_values)-2)):
                return 'up'
        
        # 하락 반전: 이전에 상승하다가 최근 하락
        if recent_values[-1] < recent_values[-2]:
            if all(recent_values[i] <= recent_values[i+1] for i in range(len(recent_values)-2)):
                return 'down'
        
        return 'none'
    
    def is_rsi_rising(self, data: pd.DataFrame, rsi_column: str, lookback: int = 2) -> bool:
        """
        RSI가 상승 중인지 확인합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            rsi_column: RSI 컬럼 이름
            lookback: 확인할 이전 기간
            
        Returns:
            상승 중이면 True, 아니면 False
        """
        if rsi_column not in data.columns or len(data) < lookback + 1:
            return False
        
        recent_values = data[rsi_column].iloc[-(lookback+1):].values
        
        if len(recent_values) < lookback + 1 or np.any(np.isnan(recent_values)):
            return False
        
        # 연속적으로 상승하는지 확인
        return all(recent_values[i] < recent_values[i+1] for i in range(len(recent_values)-1))
    
    def is_rsi_falling(self, data: pd.DataFrame, rsi_column: str, lookback: int = 2) -> bool:
        """
        RSI가 하락 중인지 확인합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            rsi_column: RSI 컬럼 이름
            lookback: 확인할 이전 기간
            
        Returns:
            하락 중이면 True, 아니면 False
        """
        if rsi_column not in data.columns or len(data) < lookback + 1:
            return False
        
        recent_values = data[rsi_column].iloc[-(lookback+1):].values
        
        if len(recent_values) < lookback + 1 or np.any(np.isnan(recent_values)):
            return False
        
        # 연속적으로 하락하는지 확인
        return all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1))
    
    def calculate_moving_average(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        이동평균선을 계산합니다.
        
        Args:
            data: 주식 데이터 DataFrame (Close 컬럼 필요)
            period: 이동평균 기간 (기본: 20일)
            
        Returns:
            이동평균 값이 포함된 pandas Series
        """
        if 'Close' not in data.columns:
            raise ValueError("DataFrame must contain 'Close' column")
        
        return data['Close'].rolling(window=period).mean()
    
    def calculate_multiple_moving_averages(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        여러 기간의 이동평균선을 계산합니다 (20일, 50일).
        
        Args:
            data: 주식 데이터 DataFrame
            
        Returns:
            이동평균선들이 추가된 DataFrame
        """
        result = data.copy()
        result['MA_20'] = self.calculate_moving_average(data, 20)
        result['MA_50'] = self.calculate_moving_average(data, 50)
        return result
    
    def detect_trend(self, data: pd.DataFrame) -> str:
        """
        이동평균선을 기반으로 추세를 판단합니다.
        
        Args:
            data: 이동평균선이 계산된 DataFrame (MA_20, MA_50 필요)
            
        Returns:
            'uptrend' (상승 추세), 'downtrend' (하락 추세), 'neutral' (중립)
        """
        if data.empty or len(data) < 50:
            return 'neutral'
        
        if 'MA_20' not in data.columns or 'MA_50' not in data.columns:
            # 이동평균선이 없으면 계산
            data = self.calculate_multiple_moving_averages(data)
        
        current_price = data['Close'].iloc[-1]
        ma_20 = data['MA_20'].iloc[-1]
        ma_50 = data['MA_50'].iloc[-1]
        
        # NaN 체크
        if pd.isna(ma_20) or pd.isna(ma_50):
            return 'neutral'
        
        # 상승 추세: 가격 > MA20 > MA50
        if current_price > ma_20 and ma_20 > ma_50:
            return 'uptrend'
        
        # 하락 추세: 가격 < MA20 < MA50
        if current_price < ma_20 and ma_20 < ma_50:
            return 'downtrend'
        
        return 'neutral'
    
    def is_trend_strong(self, data: pd.DataFrame, trend: str) -> bool:
        """
        추세가 강한지 확인합니다.
        
        Args:
            data: 이동평균선이 계산된 DataFrame
            trend: 추세 ('uptrend' 또는 'downtrend')
            
        Returns:
            강한 추세면 True, 아니면 False
        """
        if data.empty or len(data) < 50:
            return False
        
        if 'MA_20' not in data.columns or 'MA_50' not in data.columns:
            data = self.calculate_multiple_moving_averages(data)
        
        current_price = data['Close'].iloc[-1]
        ma_20 = data['MA_20'].iloc[-1]
        ma_50 = data['MA_50'].iloc[-1]
        
        if pd.isna(ma_20) or pd.isna(ma_50):
            return False
        
        # 강한 상승 추세: 가격이 MA20보다 STRONG_TREND_PRICE_THRESHOLD% 이상 위에 있고, 
        # MA20이 MA50보다 STRONG_TREND_MA_THRESHOLD% 이상 위
        if trend == 'uptrend':
            price_above_ma20 = (current_price - ma_20) / ma_20 * 100 > self.STRONG_TREND_PRICE_THRESHOLD
            ma20_above_ma50 = (ma_20 - ma_50) / ma_50 * 100 > self.STRONG_TREND_MA_THRESHOLD
            return price_above_ma20 and ma20_above_ma50
        
        # 강한 하락 추세: 가격이 MA20보다 STRONG_TREND_PRICE_THRESHOLD% 이상 아래에 있고, 
        # MA20이 MA50보다 STRONG_TREND_MA_THRESHOLD% 이상 아래
        if trend == 'downtrend':
            price_below_ma20 = (ma_20 - current_price) / ma_20 * 100 > self.STRONG_TREND_PRICE_THRESHOLD
            ma20_below_ma50 = (ma_50 - ma_20) / ma_50 * 100 > self.STRONG_TREND_MA_THRESHOLD
            return price_below_ma20 and ma20_below_ma50
        
        return False
    
    def detect_rsi_divergence(self, data: pd.DataFrame, rsi_column: str = 'RSI_Medium', lookback: int = 14) -> str:
        """
        RSI 다이버전스를 감지합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            rsi_column: RSI 컬럼 이름 (기본: 'RSI_Medium')
            lookback: 다이버전스 확인 기간
            
        Returns:
            'bullish' (강세 다이버전스), 'bearish' (약세 다이버전스), 'none' (없음)
        """
        if data.empty or len(data) < lookback + 1:
            return 'none'
        
        if rsi_column not in data.columns or 'Close' not in data.columns:
            return 'none'
        
        recent_data = data.iloc[-lookback-1:]
        prices = recent_data['Close'].values
        rsi_values = recent_data[rsi_column].values
        
        # NaN 체크
        if np.any(np.isnan(prices)) or np.any(np.isnan(rsi_values)):
            return 'none'
        
        # 가격과 RSI의 추세 비교
        price_change = prices[-1] - prices[0]
        rsi_change = rsi_values[-1] - rsi_values[0]
        
        # 강세 다이버전스: 가격은 하락하는데 RSI는 상승 (매수 신호 강화)
        if price_change < 0 and rsi_change > 0:
            # 가격의 저점이 낮아지는지 확인
            first_half_price_min = np.min(prices[:lookback//2])
            second_half_price_min = np.min(prices[lookback//2:])
            first_half_rsi_min = np.min(rsi_values[:lookback//2])
            second_half_rsi_min = np.min(rsi_values[lookback//2:])
            
            if second_half_price_min < first_half_price_min and second_half_rsi_min > first_half_rsi_min:
                return 'bullish'
        
        # 약세 다이버전스: 가격은 상승하는데 RSI는 하락 (매도 신호 강화)
        if price_change > 0 and rsi_change < 0:
            # 가격의 고점이 높아지는지 확인
            first_half_price_max = np.max(prices[:lookback//2])
            second_half_price_max = np.max(prices[lookback//2:])
            first_half_rsi_max = np.max(rsi_values[:lookback//2])
            second_half_rsi_max = np.max(rsi_values[lookback//2:])
            
            if second_half_price_max > first_half_price_max and second_half_rsi_max < first_half_rsi_max:
                return 'bearish'
        
        return 'none'
    
    def calculate_rsi_slope(self, data: pd.DataFrame, rsi_column: str, lookback: int = 3) -> float:
        """
        RSI의 기울기(변화율)를 계산합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            rsi_column: RSI 컬럼 이름
            lookback: 기울기 계산 기간
            
        Returns:
            RSI 기울기 (양수: 상승, 음수: 하락)
        """
        if rsi_column not in data.columns or len(data) < lookback + 1:
            return 0.0
        
        recent_values = data[rsi_column].iloc[-(lookback+1):].values
        
        if len(recent_values) < lookback + 1 or np.any(np.isnan(recent_values)):
            return 0.0
        
        # 선형 회귀를 사용한 기울기 계산
        x = np.arange(len(recent_values))
        slope = np.polyfit(x, recent_values, 1)[0]
        
        return slope
