"""
매매 신호 생성 모듈
"""
import pandas as pd
from typing import Tuple
from rsi_calculator import RSICalculator


class SignalGenerator:
    """매매 신호 생성 클래스"""
    
    # 신호 타입
    STRONG_BUY = "강력 매수"
    BUY = "매수"
    HOLD = "관망"
    SELL = "매도"
    STRONG_SELL = "강력 매도"
    
    def __init__(self, rsi_calculator: RSICalculator = None):
        """
        SignalGenerator 초기화
        
        Args:
            rsi_calculator: RSI 계산기 인스턴스
        """
        self.rsi_calc = rsi_calculator or RSICalculator()
    
    def generate_signal(self, data: pd.DataFrame) -> Tuple[str, str, float]:
        """
        매매 신호를 생성합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            
        Returns:
            (신호, 설명, 신호강도) tuple
        """
        if data.empty or len(data) < 3:
            return self.HOLD, "데이터 부족", 0.0
        
        # 최신 RSI 값 가져오기
        short_rsi, medium_rsi, long_rsi = self.rsi_calc.get_latest_rsi_values(data)
        
        if short_rsi is None or medium_rsi is None or long_rsi is None:
            return self.HOLD, "RSI 계산 불가", 0.0
        
        # 반전 및 추세 확인
        short_reversal = self.rsi_calc.detect_rsi_reversal(data, 'RSI_Short', lookback=2)
        short_rising = self.rsi_calc.is_rsi_rising(data, 'RSI_Short', lookback=2)
        medium_rising = self.rsi_calc.is_rsi_rising(data, 'RSI_Medium', lookback=2)
        medium_falling = self.rsi_calc.is_rsi_falling(data, 'RSI_Medium', lookback=2)
        
        # 강력 매수 조건
        # 단기 RSI가 30 이하에서 상승 반전 + 중기 RSI 30~50 구간 상승 중 + 장기 RSI 50 이상
        if (short_rsi <= 30 and short_reversal == 'up' and 
            30 <= medium_rsi <= 50 and medium_rising and 
            long_rsi >= 50):
            strength = self._calculate_buy_strength(short_rsi, medium_rsi, long_rsi)
            description = f"단기 RSI 상승 반전({short_rsi:.1f}), 중기 RSI 상승 중({medium_rsi:.1f}), 장기 RSI 안정({long_rsi:.1f})"
            return self.STRONG_BUY, description, strength
        
        # 매수 조건
        # 단기 RSI 30 이하 + 중기 RSI 40 이하
        if short_rsi <= 30 and medium_rsi <= 40:
            strength = self._calculate_buy_strength(short_rsi, medium_rsi, long_rsi) * 0.7
            description = f"단기 RSI 과매도({short_rsi:.1f}), 중기 RSI 낮음({medium_rsi:.1f})"
            return self.BUY, description, strength
        
        # 강력 매도 조건
        # 단기 RSI가 70 이상에서 하락 반전 + 중기 RSI 70 이상 하락 시작 + 장기 RSI 70 이상
        if (short_rsi >= 70 and short_reversal == 'down' and 
            medium_rsi >= 70 and medium_falling and 
            long_rsi >= 70):
            strength = self._calculate_sell_strength(short_rsi, medium_rsi, long_rsi)
            description = f"단기 RSI 하락 반전({short_rsi:.1f}), 중기 RSI 하락 중({medium_rsi:.1f}), 장기 RSI 과열({long_rsi:.1f})"
            return self.STRONG_SELL, description, strength
        
        # 매도 조건
        # 단기 RSI 70 이상 + 중기 RSI 60 이상
        if short_rsi >= 70 and medium_rsi >= 60:
            strength = self._calculate_sell_strength(short_rsi, medium_rsi, long_rsi) * 0.7
            description = f"단기 RSI 과매수({short_rsi:.1f}), 중기 RSI 높음({medium_rsi:.1f})"
            return self.SELL, description, strength
        
        # 관망
        description = f"단기 RSI: {short_rsi:.1f}, 중기 RSI: {medium_rsi:.1f}, 장기 RSI: {long_rsi:.1f}"
        return self.HOLD, description, 0.0
    
    def _calculate_buy_strength(self, short_rsi: float, medium_rsi: float, long_rsi: float) -> float:
        """
        매수 신호 강도를 계산합니다 (0~100).
        
        Args:
            short_rsi: 단기 RSI
            medium_rsi: 중기 RSI
            long_rsi: 장기 RSI
            
        Returns:
            신호 강도 (0~100)
        """
        # RSI가 낮을수록 강도가 높음
        short_strength = max(0, (30 - short_rsi) / 30 * 50)  # 최대 50점
        medium_strength = max(0, (40 - medium_rsi) / 40 * 30)  # 최대 30점
        long_strength = min(20, (long_rsi - 30) / 20 * 20) if long_rsi >= 30 else 0  # 최대 20점
        
        total_strength = short_strength + medium_strength + long_strength
        return min(100, total_strength)
    
    def _calculate_sell_strength(self, short_rsi: float, medium_rsi: float, long_rsi: float) -> float:
        """
        매도 신호 강도를 계산합니다 (0~100).
        
        Args:
            short_rsi: 단기 RSI
            medium_rsi: 중기 RSI
            long_rsi: 장기 RSI
            
        Returns:
            신호 강도 (0~100)
        """
        # RSI가 높을수록 강도가 높음
        short_strength = max(0, (short_rsi - 70) / 30 * 50)  # 최대 50점
        medium_strength = max(0, (medium_rsi - 60) / 40 * 30)  # 최대 30점
        long_strength = max(0, (long_rsi - 70) / 30 * 20)  # 최대 20점
        
        total_strength = short_strength + medium_strength + long_strength
        return min(100, total_strength)
    
    def get_signal_color(self, signal: str) -> str:
        """
        신호에 따른 색상 코드를 반환합니다.
        
        Args:
            signal: 신호 타입
            
        Returns:
            색상 코드 문자열
        """
        colors = {
            self.STRONG_BUY: "blue",
            self.BUY: "green",
            self.HOLD: "gray",
            self.SELL: "orange",
            self.STRONG_SELL: "red"
        }
        return colors.get(signal, "gray")
    
    def get_all_signals(self, all_data: dict) -> pd.DataFrame:
        """
        모든 종목에 대한 신호를 생성합니다.
        
        Args:
            all_data: {심볼: DataFrame} 형태의 딕셔너리
            
        Returns:
            신호 요약 DataFrame
        """
        results = []
        
        for symbol, data in all_data.items():
            if data is not None and not data.empty:
                # RSI 계산
                data_with_rsi = self.rsi_calc.calculate_all_rsi(data)
                
                # 신호 생성
                signal, description, strength = self.generate_signal(data_with_rsi)
                
                # 최신 RSI 값
                short_rsi, medium_rsi, long_rsi = self.rsi_calc.get_latest_rsi_values(data_with_rsi)
                
                results.append({
                    '심볼': symbol,
                    '신호': signal,
                    '단기 RSI': f"{short_rsi:.1f}" if short_rsi else "N/A",
                    '중기 RSI': f"{medium_rsi:.1f}" if medium_rsi else "N/A",
                    '장기 RSI': f"{long_rsi:.1f}" if long_rsi else "N/A",
                    '신호 강도': f"{strength:.1f}",
                    '설명': description
                })
        
        return pd.DataFrame(results)
