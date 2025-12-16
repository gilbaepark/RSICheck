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
        all_data = {}
        
        try:
            # 여러 종목을 한 번에 다운로드
            # tickers는 공백으로 구분된 문자열로 전달
            data = yf.download(
                tickers=' '.join(symbols),
                period=period,
                group_by='ticker',
                auto_adjust=False,
                progress=False
            )
            
            # 데이터가 비어있거나 None인 경우 fallback
            if data is None or data.empty:
                print("Batch download returned empty data, falling back to individual download")
                return self._fallback_individual_download(symbols, period)
            
            # 단일 종목인 경우
            if len(symbols) == 1:
                symbol = symbols[0]
                try:
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    # 모든 필수 컬럼이 존재하는지 확인
                    if all(col in data.columns for col in required_cols):
                        df = data[required_cols].copy()
                        df.index = pd.to_datetime(df.index)
                        # Close 컬럼의 NaN을 제거
                        df = df.dropna(subset=['Close'])
                        if not df.empty:
                            all_data[symbol] = df
                    else:
                        print(f"Missing required columns for {symbol}, trying individual download")
                        self._try_individual_download(symbol, period, all_data)
                except Exception as e:
                    print(f"Error processing single symbol {symbol}: {e}")
                    # 개별 다운로드로 재시도
                    self._try_individual_download(symbol, period, all_data)
            else:
                # 여러 종목인 경우 - MultiIndex 처리
                # columns 속성이 유효한지 먼저 확인
                if not hasattr(data, 'columns') or data.columns is None:
                    print("Invalid data structure, falling back to individual download")
                    return self._fallback_individual_download(symbols, period)
                
                # MultiIndex DataFrame 체크
                if isinstance(data.columns, pd.MultiIndex):
                    # 성능 최적화: level 0 값을 미리 추출
                    level_0_values = data.columns.get_level_values(0)
                    
                    for symbol in symbols:
                        try:
                            # MultiIndex에서 해당 종목이 존재하는지 확인
                            if symbol in level_0_values:
                                # 종목별 데이터 추출
                                symbol_data = data[symbol]
                                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                                
                                # 필수 컬럼이 모두 있는지 확인
                                if all(col in symbol_data.columns for col in required_cols):
                                    df = symbol_data[required_cols].copy()
                                    
                                    # 데이터 정제
                                    df.index = pd.to_datetime(df.index)
                                    df = df.dropna(subset=['Close'])
                                    
                                    # 유효한 데이터가 있는 경우에만 추가
                                    if not df.empty:
                                        all_data[symbol] = df
                                    else:
                                        print(f"No valid data for {symbol} after cleaning")
                                else:
                                    print(f"Missing required columns for {symbol}, skipping")
                            else:
                                print(f"Symbol {symbol} not found in MultiIndex, trying individual download")
                                self._try_individual_download(symbol, period, all_data)
                                
                        except Exception as e:
                            print(f"Error processing {symbol}: {e}")
                            # 개별 종목 실패 시 개별 다운로드 시도
                            self._try_individual_download(symbol, period, all_data)
                else:
                    # MultiIndex가 아닌 경우 - 예상치 못한 상황이므로 개별 다운로드로 전환
                    print(f"Expected MultiIndex for multiple symbols but got regular columns, falling back to individual download")
                    return self._fallback_individual_download(symbols, period)
            
            # 아무 데이터도 없으면 fallback
            if not all_data:
                print("No data retrieved from batch download, falling back to individual download")
                return self._fallback_individual_download(symbols, period)
            
            return all_data
            
        except Exception as e:
            print(f"Error in batch download: {e}")
            # 전체 실패 시 개별 다운로드로 대체
            return self._fallback_individual_download(symbols, period)
    
    def _try_individual_download(self, symbol: str, period: str, all_data: dict) -> None:
        """
        단일 종목에 대해 개별 다운로드를 시도하고 결과를 all_data에 추가합니다.
        
        Args:
            symbol: 주식 티커 심볼
            period: 조회 기간
            all_data: 결과를 저장할 딕셔너리
        """
        try:
            df = self.get_stock_data(symbol, period)
            if df is not None and not df.empty:
                all_data[symbol] = df
        except Exception as e:
            print(f"Individual download failed for {symbol}: {e}")
    
    def _fallback_individual_download(self, symbols: list, period: str) -> dict:
        """
        배치 다운로드 실패 시 개별 다운로드로 대체합니다.
        
        Args:
            symbols: 주식 티커 심볼 리스트
            period: 조회 기간
            
        Returns:
            dict: {심볼: DataFrame} 형태의 딕셔너리
        """
        all_data = {}
        for symbol in symbols:
            self._try_individual_download(symbol, period, all_data)
        return all_data
    
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
