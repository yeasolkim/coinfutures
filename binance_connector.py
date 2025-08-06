import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import Config
from utils import logger, timestamp_to_datetime, datetime_to_timestamp, validate_symbol, safe_float_conversion

class BinanceConnector:
    """바이낸스 선물 API 연동 클래스"""
    
    def __init__(self):
        """초기화"""
        self.config = Config.get_binance_config()
        self.client = Client(
            api_key=self.config['api_key'],
            api_secret=self.config['api_secret'],
            testnet=self.config['testnet']
        )
        
        # 선물 클라이언트 사용
        self.client.API_URL = 'https://fapi.binance.com'
        if self.config['testnet']:
            self.client.API_URL = 'https://testnet.binancefuture.com'
        
        logger.info(f"바이낸스 커넥터 초기화 완료 (테스트넷: {self.config['testnet']})")

    async def get_account_trades(self, symbol: str, start_time: datetime = None, end_time: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """계정의 선물 거래 내역 조회 (페이지네이션)"""
        try:
            symbol = validate_symbol(symbol)
            
            # 기본값: 오늘 하루 거래 (오전 9시 기준)
            if not start_time:
                start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            if not end_time:
                end_time = datetime.now()
            
            start_timestamp = datetime_to_timestamp(start_time)
            end_timestamp = datetime_to_timestamp(end_time)
            
            logger.info(f"거래 내역 조회: {symbol} ({start_time} ~ {end_time})")
            
            # 페이지네이션으로 모든 거래 내역 수집
            all_trades = []
            from_id = None
            
            while True:
                try:
                    params = {
                        'symbol': symbol,
                        'startTime': start_timestamp,
                        'endTime': end_timestamp,
                        'limit': 1000
                    }
                    
                    if from_id:
                        params['fromId'] = from_id
                    
                    trades_batch = self.client.futures_account_trades(**params)
                    
                    if not trades_batch:
                        break
                    
                    all_trades.extend(trades_batch)
                    
                    # 다음 페이지가 있으면 마지막 ID + 1 설정
                    if len(trades_batch) == 1000:
                        from_id = int(trades_batch[-1]['id']) + 1
                    else:
                        break
                        
                except Exception as e:
                    logger.warning(f"{symbol} 거래 내역 페이지네이션 중 오류: {e}")
                    break
            
            logger.info(f"{len(all_trades)}개의 거래 내역을 조회했습니다.")
            return all_trades
            
        except BinanceAPIException as e:
            logger.error(f"바이낸스 API 에러 (거래 내역 조회): {e}")
            return []
        except Exception as e:
            logger.error(f"거래 내역 조회 중 오류: {e}")
            return []

    async def get_kline_data(self, symbol: str, interval: str, start_time: datetime = None, end_time: datetime = None, limit: int = 500) -> pd.DataFrame:
        """K라인(캔들) 데이터 조회"""
        try:
            symbol = validate_symbol(symbol)
            
            # 기본값: 최근 데이터
            if start_time and end_time:
                start_timestamp = datetime_to_timestamp(start_time)
                end_timestamp = datetime_to_timestamp(end_time)
                
                klines = self.client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=start_timestamp,
                    endTime=end_timestamp,
                    limit=limit
                )
            else:
                klines = self.client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                )
            
            # DataFrame으로 변환
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # 인덱스 설정
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"K라인 데이터 조회 완료: {symbol} {interval} ({len(df)}개)")
            return df
            
        except BinanceAPIException as e:
            logger.error(f"바이낸스 API 에러 (K라인 조회): {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"K라인 데이터 조회 중 오류: {e}")
            return pd.DataFrame()

    async def get_multiple_timeframe_data(self, symbol: str, timeframes: List[str], start_time: datetime = None, end_time: datetime = None) -> Dict[str, pd.DataFrame]:
        """여러 시간 프레임의 데이터를 동시에 조회"""
        tasks = []
        
        for timeframe in timeframes:
            task = self.get_kline_data(symbol, timeframe, start_time, end_time)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        return {
            timeframes[i]: results[i] 
            for i in range(len(timeframes))
        }

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """심볼 정보 조회"""
        try:
            symbol = validate_symbol(symbol)
            exchange_info = self.client.futures_exchange_info()
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            
            logger.warning(f"심볼 정보를 찾을 수 없습니다: {symbol}")
            return {}
            
        except Exception as e:
            logger.error(f"심볼 정보 조회 중 오류: {e}")
            return {}

    def get_current_price(self, symbol: str) -> float:
        """현재 가격 조회"""
        try:
            symbol = validate_symbol(symbol)
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return safe_float_conversion(ticker['price'])
        except Exception as e:
            logger.error(f"현재 가격 조회 중 오류: {e}")
            return 0.0

    def format_trades_for_analysis(self, trades: List[Dict[str, Any]]) -> pd.DataFrame:
        """거래 데이터를 분석용 DataFrame으로 변환"""
        if not trades:
            return pd.DataFrame()
        
        # DataFrame 생성
        df = pd.DataFrame(trades)
        
        # 시간 변환
        df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        
        # 숫자 타입 변환
        numeric_columns = ['price', 'qty', 'quoteQty', 'commission']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
        # 정렬
        df = df.sort_values('time')
        
        # 인덱스 설정
        df.set_index('datetime', inplace=True)
        
        logger.info(f"거래 데이터 포맷팅 완료: {len(df)}개 거래")
        return df

    async def get_position_info(self, symbol: str = None) -> List[Dict[str, Any]]:
        """현재 포지션 정보 조회"""
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            
            # 열린 포지션만 필터링
            open_positions = [
                pos for pos in positions 
                if safe_float_conversion(pos['positionAmt']) != 0
            ]
            
            logger.info(f"현재 열린 포지션: {len(open_positions)}개")
            return open_positions
            
        except Exception as e:
            logger.error(f"포지션 정보 조회 중 오류: {e}")
            return []

    async def get_position_history(self, symbol: str = None, start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """포지션 히스토리 조회 (실현 손익 기준, 페이지네이션)"""
        try:
            # 기본값: 오늘 하루 (오전 9시 기준)
            if not start_time:
                start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            if not end_time:
                end_time = datetime.now()
            
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            logger.info(f"포지션 히스토리 조회: {symbol if symbol else 'ALL'} ({start_time} ~ {end_time})")
            
            # 페이지네이션으로 REALIZED_PNL 수익 히스토리 수집
            all_income = []
            from_id = None
            
            while True:
                try:
                    params = {
                        'incomeType': 'REALIZED_PNL',
                        'startTime': start_timestamp,
                        'endTime': end_timestamp,
                        'limit': 1000
                    }
                    
                    if symbol:
                        params['symbol'] = symbol
                    
                    if from_id:
                        params['incomeId'] = from_id
                    
                    income_batch = self.client.futures_income_history(**params)
                    
                    if not income_batch:
                        break
                    
                    all_income.extend(income_batch)
                    
                    # 다음 페이지가 있으면 마지막 ID - 1 설정
                    if len(income_batch) == 1000:
                        from_id = int(income_batch[-1]['incomeId']) - 1
                    else:
                        break
                        
                except Exception as e:
                    logger.warning(f"포지션 히스토리 페이지네이션 중 오류: {e}")
                    break
            
            logger.info(f"{len(all_income)}개의 포지션 히스토리를 조회했습니다.")
            return all_income
            
        except BinanceAPIException as e:
            logger.error(f"바이낸스 API 에러 (포지션 히스토리): {e}")
            return []
        except Exception as e:
            logger.error(f"포지션 히스토리 조회 중 오류: {e}")
            return []

    async def get_daily_pnl(self, target_date: datetime) -> Dict[str, Any]:
        """특정 날짜의 Daily P&L 조회 (페이지네이션으로 모든 데이터 수집)"""
        try:
            # 오전 9시 기준으로 하루 시작 (9:00 ~ 다음날 8:59)
            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            logger.info(f"Daily P&L 조회: {target_date.strftime('%Y-%m-%d')}")
            
            # 페이지네이션으로 모든 income 데이터 수집
            all_income = await self._get_all_income_history(start_timestamp, end_timestamp)
            
            # REALIZED_PNL만 필터링 (realized_positions 개수용)
            realized_pnl_items = [item for item in all_income if item['incomeType'] == 'REALIZED_PNL']
            
            # 순손익 계산 (실현손익 + 수수료 + 펀딩피)
            daily_pnl = 0.0
            for income in all_income:
                income_type = income['incomeType']
                asset = income.get('asset', '')
                amount = safe_float_conversion(income['income'])
                
                # USDT 기준 income만 계산
                if asset == 'USDT' and income_type in ['REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE']:
                    daily_pnl += amount
            
            # 페이지네이션으로 모든 거래 데이터 수집
            all_trades = await self._get_all_trades(start_timestamp, end_timestamp)
            
            daily_volume = sum(safe_float_conversion(trade['quoteQty']) for trade in all_trades)
            trade_count = len(all_trades)
            
            daily_summary = {
                'date': target_date.strftime('%Y-%m-%d'),
                'daily_pnl_usd': daily_pnl,
                'trading_volume': daily_volume,
                'trade_count': trade_count,
                'realized_positions': len(realized_pnl_items)
            }
            
            logger.info(f"Daily P&L 조회 완료: {daily_pnl:.2f} USD (거래 {trade_count}건, 거래량 {daily_volume:.2f} USDT)")
            return daily_summary
            
        except Exception as e:
            logger.error(f"Daily P&L 조회 중 오류: {e}")
            return {}

    async def _get_all_income_history(self, start_timestamp: int, end_timestamp: int) -> List[Dict[str, Any]]:
        """페이지네이션으로 모든 income 히스토리 수집"""
        all_income = []
        from_id = None
        
        while True:
            try:
                params = {
                    'startTime': start_timestamp,
                    'endTime': end_timestamp,
                    'limit': 1000
                }
                
                if from_id:
                    params['incomeId'] = from_id
                
                income_batch = self.client.futures_income_history(**params)
                
                if not income_batch:
                    break
                
                all_income.extend(income_batch)
                
                # 다음 페이지가 있으면 마지막 ID 설정
                if len(income_batch) == 1000:
                    from_id = int(income_batch[-1]['incomeId']) - 1
                else:
                    break
                    
            except Exception as e:
                logger.warning(f"Income 히스토리 페이지네이션 중 오류: {e}")
                break
        
        logger.info(f"총 {len(all_income)}개의 income 항목 수집")
        return all_income

    async def _get_all_trades(self, start_timestamp: int, end_timestamp: int) -> List[Dict[str, Any]]:
        """페이지네이션으로 모든 거래 내역 수집"""
        all_trades = []
        from_id = None
        
        while True:
            try:
                params = {
                    'startTime': start_timestamp,
                    'endTime': end_timestamp,
                    'limit': 1000
                }
                
                if from_id:
                    params['fromId'] = from_id
                
                trades_batch = self.client.futures_account_trades(**params)
                
                if not trades_batch:
                    break
                
                all_trades.extend(trades_batch)
                
                # 다음 페이지가 있으면 마지막 ID + 1 설정
                if len(trades_batch) == 1000:
                    from_id = int(trades_batch[-1]['id']) + 1
                else:
                    break
                    
            except Exception as e:
                logger.warning(f"거래 내역 페이지네이션 중 오류: {e}")
                break
        
        logger.info(f"총 {len(all_trades)}개의 거래 내역 수집")
        return all_trades

    async def get_account_balance(self) -> Dict[str, Any]:
        """계정 잔고 정보 조회"""
        try:
            account_info = self.client.futures_account()
            
            balance_info = {
                'total_wallet_balance': safe_float_conversion(account_info.get('totalWalletBalance', 0)),
                'total_unrealized_pnl': safe_float_conversion(account_info.get('totalUnrealizedPnL', 0)),
                'total_margin_balance': safe_float_conversion(account_info.get('totalMarginBalance', 0)),
                'available_balance': safe_float_conversion(account_info.get('availableBalance', 0))
            }
            
            logger.info("계정 잔고 정보 조회 완료")
            return balance_info
            
        except Exception as e:
            logger.error(f"계정 잔고 조회 중 오류: {e}")
            return {}

    async def get_all_traded_symbols_for_date(self, start_time: datetime, end_time: datetime) -> List[str]:
        """특정 날짜에 거래한 모든 종목을 자동 탐지
        
        Args:
            start_time (datetime): 시작 시간
            end_time (datetime): 종료 시간
        
        Returns:
            List[str]: 거래한 종목 리스트
        """
        try:
            logger.info(f"거래 종목 자동 탐지: {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}")
            
            # 계정 거래 내역 전체 조회 (심볼 지정 없음)
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            # 바이낸스 선물 거래 내역 조회 (전체)
            trades = self.client.futures_account_trades(
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=1000  # 최대 1000개
            )
            
            # 거래한 고유 심볼들 추출
            traded_symbols = set()
            for trade in trades:
                symbol = trade['symbol']
                traded_symbols.add(symbol)
            
            traded_symbols_list = list(traded_symbols)
            logger.info(f"자동 탐지된 거래 종목: {len(traded_symbols_list)}개 - {', '.join(traded_symbols_list)}")
            
            return traded_symbols_list
            
        except Exception as e:
            logger.error(f"거래 종목 자동 탐지 실패: {e}")
            # 실패시 기본 주요 종목들 반환
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']

    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            self.client.futures_ping()
            logger.info("바이낸스 API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"바이낸스 API 연결 테스트 실패: {e}")
            return False 