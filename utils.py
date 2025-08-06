import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading_journal.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_directory_exists(directory: str) -> None:
    """디렉토리가 존재하지 않으면 생성"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def timestamp_to_datetime(timestamp: int) -> datetime:
    """밀리초 타임스탬프를 datetime 객체로 변환"""
    return datetime.fromtimestamp(timestamp / 1000)

def datetime_to_timestamp(dt: datetime) -> int:
    """datetime 객체를 밀리초 타임스탬프로 변환"""
    return int(dt.timestamp() * 1000)

def get_date_range(date: datetime, days_before: int = 1) -> tuple:
    """지정된 날짜 기준으로 시작일과 종료일 반환"""
    start_date = date - timedelta(days=days_before)
    end_date = date + timedelta(days=1)
    return start_date, end_date

def format_korean_won(amount: float) -> str:
    """금액을 한국 원화 형식으로 포맷팅"""
    return f"₩{amount:,.0f}"

def format_percentage(value: float, decimal_places: int = 2) -> str:
    """백분율 형식으로 포맷팅"""
    return f"{value:.{decimal_places}f}%"

def calculate_pnl(entry_price: float, exit_price: float, quantity: float, side: str) -> Dict[str, float]:
    """손익 계산"""
    if side.upper() == 'BUY' or side.upper() == 'LONG':
        pnl = (exit_price - entry_price) * quantity
        pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
    else:  # SELL or SHORT
        pnl = (entry_price - exit_price) * quantity
        pnl_percentage = ((entry_price - exit_price) / entry_price) * 100
    
    return {
        'pnl': pnl,
        'pnl_percentage': pnl_percentage
    }

def validate_symbol(symbol: str) -> str:
    """심볼 유효성 검사 및 포맷팅"""
    symbol = symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    return symbol

def round_to_tick_size(price: float, tick_size: float) -> float:
    """틱 사이즈에 맞춰 가격 반올림"""
    return round(price / tick_size) * tick_size

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """안전한 float 변환"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def group_trades_by_date(trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """거래를 날짜별로 그룹화"""
    grouped = {}
    
    for trade in trades:
        trade_time = timestamp_to_datetime(int(trade['time']))
        date_key = trade_time.strftime('%Y-%m-%d')
        
        if date_key not in grouped:
            grouped[date_key] = []
        
        grouped[date_key].append(trade)
    
    return grouped

def calculate_trade_summary(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """거래 요약 통계 계산"""
    if not trades:
        return {
            'total_trades': 0,
            'total_volume': 0,
            'avg_price': 0,
            'total_commission': 0
        }
    
    # 실제 거래량 계산 (USDT 기준)
    total_volume = sum(safe_float_conversion(trade.get('quoteQty', 0)) for trade in trades)
    total_commission = sum(safe_float_conversion(trade['commission']) for trade in trades)
    
    # 가중평균 가격 계산
    total_qty = sum(safe_float_conversion(trade['qty']) for trade in trades)
    weighted_sum = sum(
        safe_float_conversion(trade['price']) * safe_float_conversion(trade['qty']) 
        for trade in trades
    )
    avg_price = weighted_sum / total_qty if total_qty > 0 else 0
    
    return {
        'total_trades': len(trades),
        'total_volume': total_volume,
        'avg_price': avg_price,
        'total_commission': total_commission,
        'first_trade_time': min(int(trade['time']) for trade in trades),
        'last_trade_time': max(int(trade['time']) for trade in trades)
    }

def format_trade_for_display(trade: Dict[str, Any]) -> str:
    """거래 정보를 사람이 읽기 쉬운 형식으로 포맷팅"""
    trade_time = timestamp_to_datetime(int(trade['time']))
    
    return (
        f"시간: {trade_time.strftime('%H:%M:%S')} | "
        f"방향: {trade['side']} | "
        f"가격: {safe_float_conversion(trade['price']):,.2f} | "
        f"수량: {safe_float_conversion(trade['qty']):,.4f} | "
        f"수수료: {safe_float_conversion(trade['commission']):,.6f}"
    )

def create_time_windows(df: pd.DataFrame, window_minutes: int = 30) -> List[pd.DataFrame]:
    """데이터를 시간 윈도우별로 분할"""
    if df.empty:
        return []
    
    df_copy = df.copy()
    df_copy['window'] = df_copy.index // pd.Timedelta(minutes=window_minutes)
    
    windows = []
    for window_id in df_copy['window'].unique():
        window_df = df_copy[df_copy['window'] == window_id].drop('window', axis=1)
        if not window_df.empty:
            windows.append(window_df)
    
    return windows

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """안전한 나눗셈 (0으로 나누기 방지)"""
    if denominator == 0:
        return default
    return numerator / denominator

def normalize_timeframe(timeframe: str) -> str:
    """시간 프레임 정규화"""
    timeframe_mapping = {
        '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
        '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
        '1d': '1d', '3d': '3d', '1w': '1w', '1M': '1M'
    }
    
    return timeframe_mapping.get(timeframe, '5m')

def create_directories(directories: list):
    """필요한 디렉토리들을 생성"""
    import os
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"디렉토리 생성/확인: {directory}")
        except Exception as e:
            logger.error(f"디렉토리 생성 실패 {directory}: {e}")

logger = setup_logging() 