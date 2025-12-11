"""
Yahoo Finance 데이터 수집 모듈
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class DataFetcher:
    """Yahoo Finance에서 주식 데이터를 가져오는 클래스"""
    
    # 모니터링 종목 정의
    STOCKS = {
        'Tesla': 'TSLA',
        'Nvidia': 'NVDA',
        'KORU': '069500.KS',  # KODEX 200 (한국 ETF)
        'SOXL': 'SOXL',
        'TQQQ': 'TQQQ'
    }
    
    def __init__(self):
        """DataFetcher 초기화"""
        pass
    
    def get_stock_data(self, symbol: str, period: str = '6mo') -> Optional[pd.DataFrame]:
        """
        Yahoo Finance에서 주식 데이터를 가져옵니다.
        
        Args:
            symbol: 주식 티커 심볼 (예: 'TSLA', 'NVDA')
            period: 조회 기간 ('1mo', '3mo', '6mo', '1y')
            
        Returns:
            pandas DataFrame with stock data or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df.empty:
                return None
            
            # 필요한 컬럼만 선택
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.index = pd.to_datetime(df.index)
            
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> tuple:
        """
        현재가와 등락률을 가져옵니다.
        
        Args:
            symbol: 주식 티커 심볼
            
        Returns:
            (현재가, 등락률, 등락액) tuple or (None, None, None) if error
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            
            if current_price and previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
                return current_price, change_percent, change
            
            # fallback: 최근 데이터에서 가져오기
            df = self.get_stock_data(symbol, period='5d')
            if df is not None and not df.empty:
                current_price = df['Close'].iloc[-1]
                if len(df) > 1:
                    previous_close = df['Close'].iloc[-2]
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    return current_price, change_percent, change
                return current_price, 0.0, 0.0
            
            return None, None, None
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
            return None, None, None
    
    @classmethod
    def get_stock_list(cls) -> dict:
        """
        모니터링 가능한 종목 리스트를 반환합니다.
        
        Returns:
            dict: {종목명: 티커심볼} 형태의 딕셔너리
        """
        return cls.STOCKS.copy()
    
    def get_all_stocks_data(self, period: str = '6mo') -> dict:
        """
        모든 모니터링 종목의 데이터를 가져옵니다.
        
        Args:
            period: 조회 기간
            
        Returns:
            dict: {심볼: DataFrame} 형태의 딕셔너리
        """
        all_data = {}
        for name, symbol in self.STOCKS.items():
            df = self.get_stock_data(symbol, period)
            if df is not None:
                all_data[symbol] = df
        return all_data
