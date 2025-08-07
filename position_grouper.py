"""
Supabase 거래 데이터를 포지션 그룹으로 변환하는 스크립트

롱/숏 수량이 같아지면 하나의 포지션으로 간주하여
완전한 포지션 히스토리를 position_groups 테이블에 저장
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from supabase_manager import SupabaseManager
from utils import setup_logging

# 로거 설정
setup_logging()

class PositionGrouper:
    """거래 데이터를 포지션 그룹으로 변환"""

    def __init__(self):
        """초기화"""
        self.supabase = SupabaseManager()
        logging.info("🔗 Supabase 포지션 그룹화기 초기화 완료")

    async def create_all_position_groups(self, target_date: datetime = None):
        """모든 거래 데이터를 포지션 그룹으로 변환 (9시 기준 날짜 범위 지원)"""
        try:
            logging.info("🚀 전체 포지션 그룹화 시작...")
            
            # 1. 거래 데이터 조회 (날짜 범위 지정 가능)
            if target_date:
                # 9시 기준으로 해당 날짜의 거래만 조회
                start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
                all_trades = await self.supabase.get_all_trades(start_time, end_time)
                logging.info(f"📊 {target_date.date()} (9시 기준) 거래 데이터: {len(all_trades)}개")
            else:
                # 전체 거래 데이터 조회
                all_trades = await self.supabase.get_all_trades()
                logging.info(f"📊 총 {len(all_trades)}개 거래 데이터 로드 완료")
            
            if not all_trades:
                logging.warning("❌ 거래 데이터가 없습니다.")
                return
            
            # 2. 종목별로 그룹핑
            trades_by_symbol = {}
            for trade in all_trades:
                symbol = trade['symbol']
                if symbol not in trades_by_symbol:
                    trades_by_symbol[symbol] = []
                trades_by_symbol[symbol].append(trade)
            
            logging.info(f"🏷️ {len(trades_by_symbol)}개 종목 발견: {list(trades_by_symbol.keys())}")
            
            # 3. 각 종목별 포지션 그룹화
            all_position_groups = []
            for symbol, symbol_trades in trades_by_symbol.items():
                logging.info(f"🔄 {symbol} 포지션 그룹화 시작... ({len(symbol_trades)}개 거래)")
                
                position_groups = await self._group_trades_by_net_position(symbol, symbol_trades, target_date)
                all_position_groups.extend(position_groups)
                
                logging.info(f"✅ {symbol}: {len(position_groups)}개 포지션 생성")
            
            # 4. Supabase에 저장
            if all_position_groups:
                await self.supabase.save_position_groups(all_position_groups)
                logging.info(f"🎉 총 {len(all_position_groups)}개 포지션 그룹 저장 완료!")
            else:
                logging.warning("❌ 생성된 포지션 그룹이 없습니다.")
                
            return all_position_groups
            
        except Exception as e:
            logging.error(f"❌ 포지션 그룹화 실패: {e}")
            raise

    async def _group_trades_by_net_position(self, symbol: str, trades: List[Dict[str, Any]], target_date: datetime = None) -> List[Dict[str, Any]]:
        """Net Position 로직으로 거래들을 포지션 그룹으로 변환 (9시 기준 날짜 범위 지원)"""
        try:
            # 시간순 정렬
            sorted_trades = sorted(trades, key=lambda x: x['time'])
            
            position_groups = []
            current_group_trades = []
            current_net_position = 0.0
            
            for trade in sorted_trades:
                side = trade['side']
                qty = float(trade['qty'])
                
                # 포지션에 거래 추가
                current_group_trades.append(trade)
                
                # Net Position 계산
                if side == 'BUY':
                    current_net_position += qty
                else:  # SELL
                    current_net_position -= qty
                
                # 포지션이 완료되었는지 확인 (0에 가까우면 완료)
                if abs(current_net_position) < 0.0001:  # 소수점 오차 허용
                    # 포지션 그룹 생성
                    position_group = await self._create_position_group(symbol, current_group_trades, 'Closed')
                    if position_group:
                        # 9시 기준 날짜 범위 체크 (target_date가 지정된 경우)
                        if target_date:
                            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                            end_time = start_time + timedelta(days=1)
                            position_start = datetime.fromtimestamp(current_group_trades[0]['time'] / 1000)
                            position_end = datetime.fromtimestamp(current_group_trades[-1]['time'] / 1000)
                            
                            # 해당 날짜 범위에 완료된 포지션만 포함
                            if start_time <= position_end < end_time:
                                position_groups.append(position_group)
                        else:
                            position_groups.append(position_group)
                    
                    # 초기화
                    current_group_trades = []
                    current_net_position = 0.0
            
            # 미완료 포지션 처리 (9시 기준 날짜 범위 체크)
            if current_group_trades and abs(current_net_position) > 0.0001:
                position_group = await self._create_position_group(symbol, current_group_trades, 'Open')
                if position_group:
                    # 9시 기준 날짜 범위 체크 (target_date가 지정된 경우)
                    if target_date:
                        start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
                        end_time = start_time + timedelta(days=1)
                        position_start = datetime.fromtimestamp(current_group_trades[0]['time'] / 1000)
                        
                        # 해당 날짜 범위에 시작된 미완료 포지션만 포함
                        if start_time <= position_start < end_time:
                            position_groups.append(position_group)
                            logging.info(f"🔴 {symbol}: 미완료 포지션 발견 (Net: {current_net_position:.4f})")
                    else:
                        position_groups.append(position_group)
                        logging.info(f"🔴 {symbol}: 미완료 포지션 발견 (Net: {current_net_position:.4f})")
            
            return position_groups
            
        except Exception as e:
            logging.error(f"❌ {symbol} 포지션 그룹화 실패: {e}")
            return []

    async def _create_position_group(self, symbol: str, trades: List[Dict[str, Any]], status: str) -> Dict[str, Any]:
        """거래 그룹에서 포지션 그룹 데이터 생성"""
        try:
            if not trades:
                return None
            
            # 기본 정보
            first_trade = trades[0]
            last_trade = trades[-1]
            
            # 시간 계산 (실제 거래 시간 기준)
            start_time = datetime.fromtimestamp(first_trade['time'] / 1000)
            end_time = datetime.fromtimestamp(last_trade['time'] / 1000) if status == 'Closed' else None
            
            # 진입/청산 가격 계산
            buy_trades = [t for t in trades if t['side'] == 'BUY']
            sell_trades = [t for t in trades if t['side'] == 'SELL']
            
            # 가중평균 가격 계산
            entry_price = 0.0
            exit_price = 0.0
            total_qty = 0.0
            
            # 모든 거래의 가중평균으로 진입가 계산
            for trade in trades:
                price = float(trade['price'])
                qty = float(trade['qty'])
                entry_price += price * qty
                total_qty += qty
            
            if total_qty > 0:
                entry_price = entry_price / total_qty
            
            # 포지션 방향 결정 (첫 번째 거래 기준)
            side = 'Long' if first_trade['side'] == 'BUY' else 'Short'
            
            # 수량 계산 (절댓값)
            net_qty = sum(float(t['qty']) for t in buy_trades) - sum(float(t['qty']) for t in sell_trades)
            quantity = abs(net_qty)
            
            # P&L 계산 (실제 실현손익)
            if status == 'Closed':
                # 매수 금액 - 매도 금액
                buy_amount = sum(float(t['price']) * float(t['qty']) for t in buy_trades)
                sell_amount = sum(float(t['price']) * float(t['qty']) for t in sell_trades)
                pnl_amount = sell_amount - buy_amount
                
                if buy_amount > 0:
                    pnl_percentage = (pnl_amount / buy_amount) * 100
                else:
                    pnl_percentage = 0.0
                    
                exit_price = sell_amount / sum(float(t['qty']) for t in sell_trades) if sell_trades else 0.0
            else:
                # 미완료 포지션은 손익 0
                pnl_amount = 0.0
                pnl_percentage = 0.0
                exit_price = 0.0
            
            # 지속시간 계산
            duration_minutes = 0
            if end_time:
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
            
            position_group = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl_amount': pnl_amount,
                'pnl_percentage': pnl_percentage,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat() if end_time else None,
                'duration_minutes': duration_minutes,
                'trade_count': len(trades),
                'position_type': status,
                'position_status': status
            }
            
            return position_group
            
        except Exception as e:
            logging.error(f"❌ 포지션 그룹 생성 실패: {e}")
            return None

async def main():
    """메인 실행 함수"""
    try:
        print("🚀 === Supabase 포지션 그룹화 시작 ===")
        
        grouper = PositionGrouper()
        
        # 포지션 그룹화 실행
        position_groups = await grouper.create_all_position_groups()
        
        if position_groups:
            print(f"\n🎉 === 포지션 그룹화 완료 ===")
            print(f"✅ 총 {len(position_groups)}개 포지션 생성")
            
            # 종목별 통계
            symbol_stats = {}
            for group in position_groups:
                symbol = group['symbol']
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {'closed': 0, 'open': 0}
                symbol_stats[symbol][group['position_status'].lower()] += 1
            
            print("\n📊 종목별 포지션 통계:")
            for symbol, stats in symbol_stats.items():
                print(f"   {symbol}: {stats['closed']}개 완료, {stats['open']}개 미완료")
            
            print("\n🎯 position_groups 테이블에 저장 완료!")
            print("💡 이제 매매일지에서 정확한 포지션 히스토리를 볼 수 있습니다!")
        
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        logging.error(f"실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 