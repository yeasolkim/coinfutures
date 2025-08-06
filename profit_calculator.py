import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from utils import logger, safe_float_conversion, format_korean_won, format_percentage

class ProfitCalculator:
    """포지션별 및 전체 수익률 계산 클래스"""
    
    def __init__(self):
        """초기화"""
        logger.info("수익률 계산기 초기화 완료")
    
    def calculate_position_pnl(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """포지션별 손익 계산
        
        Args:
            trades: 바이낸스 거래 내역 리스트
            
        Returns:
            포지션별 손익 정보 리스트
        """
        try:
            if not trades:
                return []
            
            # 심볼별로 거래 그룹화
            symbol_trades = {}
            for trade in trades:
                symbol = trade['symbol']
                if symbol not in symbol_trades:
                    symbol_trades[symbol] = []
                symbol_trades[symbol].append(trade)
            
            positions = []
            
            for symbol, symbol_trade_list in symbol_trades.items():
                # 시간순 정렬
                symbol_trade_list.sort(key=lambda x: int(x['time']))
                
                # 포지션 분석
                position_info = self._analyze_position(symbol, symbol_trade_list)
                if position_info:
                    positions.extend(position_info)
            
            logger.info(f"총 {len(positions)}개 포지션 분석 완료")
            return positions
            
        except Exception as e:
            logger.error(f"포지션 손익 계산 중 오류: {e}")
            return []
    
    def _analyze_position(self, symbol: str, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """개별 심볼의 포지션 분석"""
        try:
            positions = []
            current_position = 0.0  # 현재 포지션 크기
            position_cost = 0.0     # 평균 진입가격 * 수량
            
            open_time = None
            close_time = None
            
            for trade in trades:
                price = safe_float_conversion(trade['price'])
                qty = safe_float_conversion(trade['qty'])
                side = trade['side']
                time = int(trade['time'])
                
                # 포지션 방향에 따른 수량 조정
                if side == 'BUY':
                    trade_qty = qty
                else:  # SELL
                    trade_qty = -qty
                
                # 포지션이 없었다면 새로 시작
                if abs(current_position) < 0.0001:
                    open_time = time
                    current_position = trade_qty
                    position_cost = price * abs(trade_qty)
                else:
                    # 같은 방향이면 추가 매수/매도
                    if (current_position > 0 and trade_qty > 0) or (current_position < 0 and trade_qty < 0):
                        # 평균 진입가 계산
                        total_qty = abs(current_position) + abs(trade_qty)
                        avg_price = (position_cost + price * abs(trade_qty)) / total_qty
                        
                        current_position += trade_qty
                        position_cost = avg_price * abs(current_position)
                    else:
                        # 반대 방향이면 청산 또는 반전
                        if abs(trade_qty) >= abs(current_position):
                            # 완전 청산 또는 반전
                            entry_price = position_cost / abs(current_position)
                            exit_price = price
                            position_side = "Long" if current_position > 0 else "Short"
                            closed_qty = abs(current_position)
                            
                            # 손익 계산
                            if position_side == "Long":
                                pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
                            else:
                                pnl_percentage = ((entry_price - exit_price) / entry_price) * 100
                            
                            pnl_amount = (pnl_percentage / 100) * (entry_price * closed_qty)
                            
                            position_info = {
                                'symbol': symbol,
                                'side': position_side,
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'quantity': closed_qty,
                                'pnl_percentage': pnl_percentage,
                                'pnl_amount': pnl_amount,
                                'open_time': open_time,
                                'close_time': time,
                                'duration_minutes': (time - open_time) / 60000  # 밀리초를 분으로 변환
                            }
                            
                            positions.append(position_info)
                            
                            # 남은 수량으로 새 포지션 시작
                            remaining_qty = abs(trade_qty) - abs(current_position)
                            if remaining_qty > 0.0001:
                                current_position = remaining_qty if trade_qty > 0 else -remaining_qty
                                position_cost = price * remaining_qty
                                open_time = time
                            else:
                                current_position = 0.0
                                position_cost = 0.0
                                open_time = None
                        else:
                            # 부분 청산
                            current_position += trade_qty
            
            return positions
            
        except Exception as e:
            logger.error(f"포지션 분석 중 오류 ({symbol}): {e}")
            return []
    
    def calculate_position_pnl_from_history(self, position_history: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Position History API 데이터를 기반으로 포지션 정보 생성
        
        Args:
            position_history: futures_income_history API 결과 (REALIZED_PNL)
            trades: 거래 내역 (가격 정보용)
            
        Returns:
            포지션별 손익 정보 리스트
        """
        try:
            if not position_history:
                return []
            
            positions = []
            
            # TradeId별로 거래 매핑 생성 (가격 정보 추출용)
            trade_map = {}
            for trade in trades:
                trade_id = str(trade.get('id', ''))
                if trade_id:
                    trade_map[trade_id] = trade
            
            # Position History를 TradeId별로 그룹화
            trade_groups = {}
            for income in position_history:
                trade_id = str(income.get('tradeId', ''))
                if trade_id and trade_id in trade_map:
                    if trade_id not in trade_groups:
                        trade_groups[trade_id] = []
                    trade_groups[trade_id].append(income)
            
            # 각 그룹을 하나의 포지션으로 처리
            for trade_id, income_list in trade_groups.items():
                try:
                    # 해당 거래 정보 가져오기
                    trade_info = trade_map[trade_id]
                    
                    # 실현손익 합계
                    total_pnl = sum(safe_float_conversion(income['income']) for income in income_list)
                    
                    # 거래 정보에서 가격과 수량 추출
                    price = safe_float_conversion(trade_info['price'])
                    qty = safe_float_conversion(trade_info['qty'])
                    side = trade_info['side']
                    symbol = trade_info['symbol']
                    time = int(trade_info['time'])
                    
                    # 포지션 정보 구성 (단순화된 버전)
                    position_info = {
                        'symbol': symbol,
                        'side': 'Long' if side == 'BUY' else 'Short',
                        'entry_price': price,  # 실제로는 평균가가 필요하지만 단순화
                        'exit_price': price,   # 청산가는 별도 계산 필요
                        'quantity': qty,
                        'pnl_percentage': (total_pnl / (price * qty)) * 100 if price * qty > 0 else 0,
                        'pnl_amount': total_pnl,
                        'close_time': time,
                        'trade_id': trade_id
                    }
                    
                    positions.append(position_info)
                    
                except Exception as e:
                    logger.error(f"포지션 정보 구성 중 오류 (TradeId: {trade_id}): {e}")
                    continue
            
            # 실현손익이 있는 포지션만 반환
            valid_positions = [pos for pos in positions if abs(pos['pnl_amount']) > 0.001]
            
            logger.info(f"Position History 기반 {len(valid_positions)}개 포지션 분석 완료")
            return valid_positions
            
        except Exception as e:
            logger.error(f"Position History 기반 포지션 분석 중 오류: {e}")
            return []
    
    def create_positions_from_api_data(self, position_history: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """바이낸스 포지션 추적 알고리즘 (오픈/클로즈 사이클 기준)
        
        Args:
            position_history: futures_income_history API 결과
            trades: 거래 내역
            
        Returns:
            실제 포지션 오픈/클로즈 사이클 기준 포지션 리스트
        """
        try:
            if not trades:
                return []
            
            # 거래 내역을 시간순 정렬
            trades.sort(key=lambda x: int(x['time']))
            
            # 포지션 추적 변수
            current_position = 0.0  # 현재 포지션 크기 (양수: 롱, 음수: 숏)
            position_cost = 0.0     # 현재 포지션 비용
            open_time = None        # 포지션 오픈 시간
            positions = []          # 완료된 포지션들
            
            # TradeId별 PnL 매핑
            trade_pnl_map = {}
            for income in position_history:
                trade_id = str(income.get('tradeId', ''))
                if trade_id:
                    trade_pnl_map[trade_id] = safe_float_conversion(income['income'])
            
            for trade in trades:
                trade_id = str(trade.get('id', ''))
                price = safe_float_conversion(trade['price'])
                qty = safe_float_conversion(trade['qty'])
                side = trade['side']
                time = int(trade['time'])
                symbol = trade['symbol']
                
                # 거래량 방향 설정 (BUY: +, SELL: -)
                trade_qty = qty if side == 'BUY' else -qty
                
                if current_position == 0:
                    # 새 포지션 시작
                    current_position = trade_qty
                    position_cost = abs(trade_qty) * price
                    open_time = time
                    
                elif (current_position > 0 and trade_qty > 0) or (current_position < 0 and trade_qty < 0):
                    # 같은 방향 - 포지션 크기 증가
                    avg_price = position_cost / abs(current_position)
                    current_position += trade_qty
                    position_cost = abs(current_position) * ((avg_price * abs(current_position - trade_qty)) + (price * abs(trade_qty))) / abs(current_position)
                    
                else:
                    # 반대 방향 - 포지션 감소 또는 방향 전환
                    if abs(trade_qty) >= abs(current_position):
                        # 완전 청산 또는 방향 전환
                        entry_price = position_cost / abs(current_position)
                        exit_price = price
                        position_side = "Long" if current_position > 0 else "Short"
                        closed_qty = abs(current_position)
                        
                        # 해당 거래의 실제 PnL 사용
                        actual_pnl = trade_pnl_map.get(trade_id, 0)
                        
                        # 수익률 계산
                        if position_side == "Long":
                            pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
                        else:
                            pnl_percentage = ((entry_price - exit_price) / entry_price) * 100
                        
                        position_info = {
                            'symbol': symbol,
                            'side': position_side,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'quantity': closed_qty,
                            'pnl_percentage': pnl_percentage,
                            'pnl_amount': actual_pnl,
                            'open_time': open_time,
                            'close_time': time,
                            'position_type': 'Closed',
                            'duration_minutes': (time - open_time) / 60000  # 밀리초를 분으로 변환
                        }
                        
                        positions.append(position_info)
                        
                        # 남은 수량으로 새 포지션 시작
                        remaining_qty = abs(trade_qty) - abs(current_position)
                        if remaining_qty > 0.0001:
                            current_position = remaining_qty if trade_qty > 0 else -remaining_qty
                            position_cost = price * remaining_qty
                            open_time = time
                        else:
                            current_position = 0.0
                            position_cost = 0.0
                            open_time = None
                    else:
                        # 부분 청산
                        current_position += trade_qty
                        # 비용은 비례적으로 감소
                        position_cost = (position_cost * abs(current_position)) / abs(current_position - trade_qty) if (current_position - trade_qty) != 0 else position_cost
            
            # 수익 기준 내림차순 정렬
            positions.sort(key=lambda x: x['pnl_amount'], reverse=True)
            
            logger.info(f"포지션 추적 알고리즘으로 {len(positions)}개 포지션 구성 완료")
            return positions
            
        except Exception as e:
            logger.error(f"포지션 추적 중 오류: {e}")
            return []
    
    def calculate_daily_summary(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """하루 전체 수익 요약 계산"""
        try:
            if not positions:
                return {
                    'total_pnl_percentage': 0.0,
                    'total_pnl_amount': 0.0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'best_trade': None,
                    'worst_trade': None,
                    'symbols_traded': []
                }
            
            total_pnl_amount = sum(pos['pnl_amount'] for pos in positions)
            winning_trades = [pos for pos in positions if pos['pnl_percentage'] > 0]
            losing_trades = [pos for pos in positions if pos['pnl_percentage'] < 0]
            
            win_rate = (len(winning_trades) / len(positions)) * 100 if positions else 0
            
            # 최고/최악 거래
            best_trade = max(positions, key=lambda x: x['pnl_percentage']) if positions else None
            worst_trade = min(positions, key=lambda x: x['pnl_percentage']) if positions else None
            
            # 거래한 심볼들
            symbols_traded = list(set(pos['symbol'] for pos in positions))
            
            # 전체 수익률 계산 (가정: 초기 자본 대비)
            # 여기서는 각 포지션의 진입 금액 합계 대비 손익으로 계산
            total_entry_value = sum(pos['entry_price'] * pos['quantity'] for pos in positions)
            total_pnl_percentage = (total_pnl_amount / total_entry_value * 100) if total_entry_value > 0 else 0
            
            return {
                'total_pnl_percentage': total_pnl_percentage,
                'total_pnl_amount': total_pnl_amount,
                'total_trades': len(positions),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'symbols_traded': symbols_traded,
                'total_entry_value': total_entry_value
            }
            
        except Exception as e:
            logger.error(f"일일 요약 계산 중 오류: {e}")
            return {}
    
    def format_position_table(self, positions: List[Dict[str, Any]]) -> str:
        """포지션을 Notion 표 형식으로 포맷팅"""
        try:
            if not positions:
                return "오늘은 거래가 없었습니다."
            
            table_rows = []
            for pos in positions:
                row = f"| {pos['symbol']} | {pos['side']} | {pos['entry_price']:,.2f} | {pos['exit_price']:,.2f} | {pos['pnl_percentage']:+.2f}% | {format_korean_won(pos['pnl_amount'])} |"
                table_rows.append(row)
            
            table = "| 종목 | 방향 | 진입가 | 청산가 | 수익률 | 수익금 |\n"
            table += "|------|------|--------|--------|--------|---------|\n"
            table += "\n".join(table_rows)
            
            return table
            
        except Exception as e:
            logger.error(f"포지션 테이블 포맷팅 중 오류: {e}")
            return "포지션 데이터 포맷팅 실패"
    
    def get_market_type(self, positions: List[Dict[str, Any]], price_data: Dict[str, pd.DataFrame]) -> str:
        """시장 유형 판단 (상승장/하락장/횡보장)"""
        try:
            if not price_data:
                return "횡보장"
            
            # 주요 심볼들의 가격 변화 분석
            main_symbols = ['BTCUSDT', 'ETHUSDT']
            price_changes = []
            
            for symbol in main_symbols:
                if symbol in price_data and not price_data[symbol].empty:
                    df = price_data[symbol]
                    if len(df) >= 2:
                        price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                        price_changes.append(price_change)
            
            if not price_changes:
                return "횡보장"
            
            avg_change = sum(price_changes) / len(price_changes)
            
            if avg_change > 2:
                return "상승장"
            elif avg_change < -2:
                return "하락장"
            else:
                return "횡보장"
                
        except Exception as e:
            logger.error(f"시장 유형 판단 중 오류: {e}")
            return "횡보장"
    
    def get_difficulty_level(self, positions: List[Dict[str, Any]], win_rate: float) -> str:
        """매매 난이도 판단 - 거래 복잡도 기반"""
        try:
            if not positions:
                return "난이도 하"
            
            # 거래 복잡도 점수 계산
            complexity_score = 0
            total_positions = len(positions)
            
            # 1. 포지션당 평균 거래 횟수 계산
            total_trades_in_positions = 0
            high_frequency_positions = 0
            
            for position in positions:
                trade_count = position.get('trade_count', 1)
                total_trades_in_positions += trade_count
                
                # 한 포지션에서 거래가 많이 일어난 경우 복잡도 증가
                if trade_count >= 10:
                    complexity_score += 3  # 10회 이상 거래한 포지션
                    high_frequency_positions += 1
                elif trade_count >= 5:
                    complexity_score += 2  # 5-9회 거래한 포지션
                    high_frequency_positions += 1
                elif trade_count >= 3:
                    complexity_score += 1  # 3-4회 거래한 포지션
            
            # 2. 평균 거래 횟수
            avg_trades_per_position = total_trades_in_positions / total_positions if total_positions > 0 else 1
            if avg_trades_per_position >= 8:
                complexity_score += 3
            elif avg_trades_per_position >= 5:
                complexity_score += 2
            elif avg_trades_per_position >= 3:
                complexity_score += 1
            
            # 3. 고빈도 거래 포지션 비율
            if total_positions > 0:
                high_freq_ratio = high_frequency_positions / total_positions
                if high_freq_ratio >= 0.5:  # 50% 이상이 고빈도 거래
                    complexity_score += 2
                elif high_freq_ratio >= 0.3:  # 30% 이상이 고빈도 거래
                    complexity_score += 1
            
            # 4. 전체 포지션 수도 고려
            if total_positions >= 15:
                complexity_score += 2
            elif total_positions >= 10:
                complexity_score += 1
            
            # 5. 승률이 낮으면 난이도 증가 (어려웠다는 의미)
            if win_rate < 40:
                complexity_score += 2
            elif win_rate < 60:
                complexity_score += 1
            
            # 최종 난이도 결정
            if complexity_score >= 8:
                return "난이도 상"  # 매우 복잡한 거래 패턴
            elif complexity_score >= 4:
                return "난이도 중"  # 어느 정도 복잡한 거래
            else:
                return "난이도 하"  # 단순한 거래 패턴
                
        except Exception as e:
            logger.error(f"난이도 판단 중 오류: {e}")
            return "난이도 중" 