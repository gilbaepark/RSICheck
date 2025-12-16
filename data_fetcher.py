"""
Yahoo Finance 데이터 수집 모듈
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class DataFetcher:
    """Yahoo Finance에서 주식 데이터를 가져오는 클래스"""
    
    # 병렬 처리 설정
    MAX_WORKERS = 5  # ThreadPoolExecutor 최대 워커 수
    
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
        fast_info를 사용하여 성능을 개선했습니다.
        
        Args:
            symbol: 주식 티커 심볼
            
        Returns:
            (현재가, 등락률, 등락액) tuple or (None, None, None) if error
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # fast_info 사용 (info보다 훨씬 빠름)
            try:
                fast_info = ticker.fast_info
                current_price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
                previous_close = fast_info.get('previousClose')
                
                if current_price and previous_close:
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100
                    return current_price, change_percent, change
            except Exception:
                # fast_info 실패 시 기본 info 사용
                pass
            
            # fallback: 최근 2일 데이터에서 가져오기 (5일 대신 2일로 줄여서 빠르게)
            df = ticker.history(period='2d')
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
        모든 모니터링 종목의 데이터를 병렬로 가져옵니다.
        
        Args:
            period: 조회 기간
            
        Returns:
            dict: {심볼: DataFrame} 형태의 딕셔너리
        """
        all_data = {}
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_symbol = {
                executor.submit(self.get_stock_data, symbol, period): symbol 
                for symbol in self.STOCKS.values()
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    if df is not None:
                        all_data[symbol] = df
                except Exception as e:
                    print(f"Error fetching data for {symbol}: {e}")
        
        return all_data
    
    def get_batch_stock_data(self, symbols: list, period: str = '6mo') -> dict:
        """
        여러 종목의 데이터를 한 번에 배치로 다운로드합니다.
        yf.download()를 사용하여 더 빠르게 가져옵니다.
        
        Args:
            symbols: 주식 티커 심볼 리스트
            period: 조회 기간
            
        Returns:
            dict: {심볼: DataFrame} 형태의 딕셔너리
        """
        try:
            # 여러 종목을 한 번에 다운로드
            data = yf.download(
                tickers=' '.join(symbols),
                period=period,
                group_by='ticker',
                auto_adjust=False,
                progress=False
            )
            
            all_data = {}
            
            if len(symbols) == 1:
                # 단일 종목인 경우
                symbol = symbols[0]
                if not data.empty:
                    df = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    df.index = pd.to_datetime(df.index)
                    all_data[symbol] = df
            else:
                # 여러 종목인 경우
                for symbol in symbols:
                    try:
                        if symbol in data.columns.levels[0]:
                            df = data[symbol][['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                            df.index = pd.to_datetime(df.index)
                            # NaN이 너무 많으면 제외
                            if not df.empty and df['Close'].notna().sum() > 0:
                                all_data[symbol] = df
                    except Exception as e:
                        print(f"Error processing {symbol}: {e}")
            
            return all_data
        except Exception as e:
            print(f"Error in batch download: {e}")
            # 배치 다운로드 실패 시 개별 다운로드로 대체
            return self.get_all_stocks_data(period)
    
    def get_all_current_prices(self) -> dict:
        """
        모든 모니터링 종목의 현재가를 병렬로 가져옵니다.
        
        Returns:
            dict: {심볼: (현재가, 등락률, 등락액)} 형태의 딕셔너리
        """
        all_prices = {}
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_symbol = {
                executor.submit(self.get_current_price, symbol): symbol
                for symbol in self.STOCKS.values()
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result[0] is not None:
                        all_prices[symbol] = result
                except Exception as e:
                    print(f"Error fetching price for {symbol}: {e}")
        
        return all_prices
