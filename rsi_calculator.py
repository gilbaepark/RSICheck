"""
RSI 지표 계산 모듈
"""
import pandas as pd
import numpy as np
from typing import Tuple


class RSICalculator:
    """RSI(Relative Strength Index) 계산 클래스"""
    
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
