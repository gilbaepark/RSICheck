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
    
    # RSI 임계값 설정
    DEFAULT_BUY_THRESHOLD = 30
    DEFAULT_SELL_THRESHOLD = 70
    UPTREND_SELL_THRESHOLD = 75
    STRONG_UPTREND_SELL_THRESHOLD = 80
    STRONG_UPTREND_SELL_OFFSET = 5  # 강한 상승 추세에서 strong_sell_threshold 추가 오프셋
    DOWNTREND_BUY_THRESHOLD = 27
    STRONG_DOWNTREND_BUY_THRESHOLD = 25
    
    # 다이버전스 신호 강도 배율
    DIVERGENCE_STRENGTH_MULTIPLIER = 1.2  # 강력 매수/매도 시 사용
    DIVERGENCE_BUY_MULTIPLIER = 1.3  # 일반 매수 시 사용
    DIVERGENCE_SELL_MULTIPLIER = 1.3  # 일반 매도 시 사용
    
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
        추세, 다이버전스, 모멘텀을 고려한 개선된 전략을 사용합니다.
        
        Args:
            data: RSI가 계산된 DataFrame
            
        Returns:
            (신호, 설명, 신호강도) tuple
        """
        if data.empty or len(data) < 3:
            return self.HOLD, "데이터 부족", 0.0
        
        # 이동평균선 계산 (없으면)
        if 'MA_20' not in data.columns or 'MA_50' not in data.columns:
            data = self.rsi_calc.calculate_multiple_moving_averages(data)
        
        # 최신 RSI 값 가져오기
        short_rsi, medium_rsi, long_rsi = self.rsi_calc.get_latest_rsi_values(data)
        
        if short_rsi is None or medium_rsi is None or long_rsi is None:
            return self.HOLD, "RSI 계산 불가", 0.0
        
        # 추세 분석
        trend = self.rsi_calc.detect_trend(data)
        trend_strong = self.rsi_calc.is_trend_strong(data, trend)
        
        # 다이버전스 감지
        divergence = self.rsi_calc.detect_rsi_divergence(data, 'RSI_Medium', lookback=14)
        
        # RSI 기울기 (모멘텀)
        rsi_slope = self.rsi_calc.calculate_rsi_slope(data, 'RSI_Short', lookback=3)
        
        # 반전 및 추세 확인
        short_reversal = self.rsi_calc.detect_rsi_reversal(data, 'RSI_Short', lookback=2)
        short_rising = self.rsi_calc.is_rsi_rising(data, 'RSI_Short', lookback=2)
        medium_rising = self.rsi_calc.is_rsi_rising(data, 'RSI_Medium', lookback=2)
        medium_falling = self.rsi_calc.is_rsi_falling(data, 'RSI_Medium', lookback=2)
        
        # 동적 RSI 임계값 설정
        if trend == 'uptrend' and trend_strong:
            # 강한 상승 추세: 매도 임계값 상향 조정
            sell_threshold = self.STRONG_UPTREND_SELL_THRESHOLD
            strong_sell_threshold = self.STRONG_UPTREND_SELL_THRESHOLD + self.STRONG_UPTREND_SELL_OFFSET
        elif trend == 'uptrend':
            # 상승 추세: 매도 임계값 약간 상향
            sell_threshold = self.UPTREND_SELL_THRESHOLD
            strong_sell_threshold = self.STRONG_UPTREND_SELL_THRESHOLD
        else:
            # 기본 임계값
            sell_threshold = self.DEFAULT_SELL_THRESHOLD
            strong_sell_threshold = self.DEFAULT_SELL_THRESHOLD
        
        if trend == 'downtrend' and trend_strong:
            # 강한 하락 추세: 매수 임계값 하향 조정
            buy_threshold = self.STRONG_DOWNTREND_BUY_THRESHOLD
            strong_buy_threshold = self.STRONG_DOWNTREND_BUY_THRESHOLD
        elif trend == 'downtrend':
            # 하락 추세: 매수 임계값 약간 하향
            buy_threshold = self.DOWNTREND_BUY_THRESHOLD
            strong_buy_threshold = self.DOWNTREND_BUY_THRESHOLD
        else:
            # 기본 임계값
            buy_threshold = self.DEFAULT_BUY_THRESHOLD
            strong_buy_threshold = self.DEFAULT_BUY_THRESHOLD
        
        # === 매수 신호 로직 ===
        
        # 강력 매수 조건
        # 1. 기본: 단기 RSI 과매도 반전 + 중기 RSI 상승 + 장기 RSI 안정
        # 2. 강세 다이버전스 추가 보너스
        # 3. 하락 추세에서는 더 낮은 임계값 적용
        if (short_rsi <= strong_buy_threshold and short_reversal == 'up' and 
            strong_buy_threshold <= medium_rsi <= 50 and medium_rising and 
            long_rsi >= 50):
            strength = self._calculate_buy_strength(short_rsi, medium_rsi, long_rsi)
            
            # 강세 다이버전스가 있으면 신호 강도 증가
            if divergence == 'bullish':
                strength = min(100, strength * self.DIVERGENCE_STRENGTH_MULTIPLIER)
                description = f"강세 다이버전스 감지! 단기 RSI 상승 반전({short_rsi:.1f}), 중기 RSI 상승 중({medium_rsi:.1f}), 장기 RSI 안정({long_rsi:.1f})"
            else:
                description = f"단기 RSI 상승 반전({short_rsi:.1f}), 중기 RSI 상승 중({medium_rsi:.1f}), 장기 RSI 안정({long_rsi:.1f})"
            
            return self.STRONG_BUY, description, strength
        
        # 매수 조건
        # 기본 과매도 조건 + 다이버전스 고려
        if short_rsi <= buy_threshold and medium_rsi <= 40:
            strength = self._calculate_buy_strength(short_rsi, medium_rsi, long_rsi) * 0.7
            
            # 강세 다이버전스가 있으면 신호 강도 증가
            if divergence == 'bullish':
                strength = min(100, strength * self.DIVERGENCE_BUY_MULTIPLIER)
                description = f"강세 다이버전스 + 단기 RSI 과매도({short_rsi:.1f}), 중기 RSI 낮음({medium_rsi:.1f})"
            else:
                description = f"단기 RSI 과매도({short_rsi:.1f}), 중기 RSI 낮음({medium_rsi:.1f})"
            
            return self.BUY, description, strength
        
        # === 매도 신호 로직 ===
        
        # 강세장에서 조기 매도 방지
        # RSI가 과매수 구간이더라도 추세가 강하고 모멘텀이 있으면 보유
        if trend == 'uptrend' and trend_strong:
            # 강한 상승 추세에서는 RSI가 높아도 계속 상승할 수 있음
            # RSI가 매우 높고(85 이상) 하락 반전이 명확할 때만 매도
            if short_rsi >= 85 and short_reversal == 'down':
                strength = self._calculate_sell_strength(short_rsi, medium_rsi, long_rsi) * 0.8
                description = f"강한 상승 추세 중 단기 RSI 하락 반전({short_rsi:.1f}), 주의 필요"
                return self.SELL, description, strength
            elif short_rsi >= sell_threshold:
                # 과매수지만 추세가 강하면 보유 권장
                description = f"상승 추세 중 단기 RSI 과매수({short_rsi:.1f}), 추세 강함 - 보유 권장"
                return self.HOLD, description, 0.0
        
        # 강력 매도 조건
        # 1. 기본: 단기 RSI 과매수 반전 + 중기 RSI 하락 + 장기 RSI 과열
        # 2. 약세 다이버전스 추가 보너스
        # 3. 상승 추세에서는 더 높은 임계값 적용
        if (short_rsi >= strong_sell_threshold and short_reversal == 'down' and 
            medium_rsi >= sell_threshold and medium_falling and 
            long_rsi >= sell_threshold):
            strength = self._calculate_sell_strength(short_rsi, medium_rsi, long_rsi)
            
            # 약세 다이버전스가 있으면 신호 강도 증가
            if divergence == 'bearish':
                strength = min(100, strength * self.DIVERGENCE_STRENGTH_MULTIPLIER)
                description = f"약세 다이버전스 감지! 단기 RSI 하락 반전({short_rsi:.1f}), 중기 RSI 하락 중({medium_rsi:.1f}), 장기 RSI 과열({long_rsi:.1f})"
            else:
                description = f"단기 RSI 하락 반전({short_rsi:.1f}), 중기 RSI 하락 중({medium_rsi:.1f}), 장기 RSI 과열({long_rsi:.1f})"
            
            return self.STRONG_SELL, description, strength
        
        # 매도 조건
        # 기본 과매수 조건 + 다이버전스 고려
        if short_rsi >= sell_threshold and medium_rsi >= 60:
            strength = self._calculate_sell_strength(short_rsi, medium_rsi, long_rsi) * 0.7
            
            # 약세 다이버전스가 있으면 신호 강도 증가
            if divergence == 'bearish':
                strength = min(100, strength * self.DIVERGENCE_SELL_MULTIPLIER)
                description = f"약세 다이버전스 + 단기 RSI 과매수({short_rsi:.1f}), 중기 RSI 높음({medium_rsi:.1f})"
            else:
                description = f"단기 RSI 과매수({short_rsi:.1f}), 중기 RSI 높음({medium_rsi:.1f})"
            
            return self.SELL, description, strength
        
        # 관망
        # 추세 정보 추가
        trend_text = ""
        if trend == 'uptrend':
            trend_text = " [상승 추세]" if not trend_strong else " [강한 상승 추세]"
        elif trend == 'downtrend':
            trend_text = " [하락 추세]" if not trend_strong else " [강한 하락 추세]"
        
        description = f"단기 RSI: {short_rsi:.1f}, 중기 RSI: {medium_rsi:.1f}, 장기 RSI: {long_rsi:.1f}{trend_text}"
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
