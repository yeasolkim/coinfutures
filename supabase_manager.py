"""
Supabase 기반 거래 데이터 관리 모듈

전체 거래/포지션 데이터를 Supabase에 중앙화하여 
정확한 포지션 생명주기 추적과 일별 매매일지 생성
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import Config

class SupabaseManager:
    """Supabase 기반 거래 데이터 관리"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        try:
            self.supabase: Client = create_client(
                Config.SUPABASE_URL, 
                Config.SUPABASE_KEY
            )
            logging.info("Supabase 연결 완료")
        except Exception as e:
            logging.error(f"Supabase 연결 실패: {e}")
            raise

    async def initialize_tables(self):
        """필요한 테이블들을 생성 (SQL 스크립트 실행 필요)"""
        tables_sql = """
        -- 거래 기록 테이블
        CREATE TABLE IF NOT EXISTS trades (
            id BIGSERIAL PRIMARY KEY,
            trade_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            price DECIMAL NOT NULL,
            qty DECIMAL NOT NULL,
            commission DECIMAL NOT NULL,
            commission_asset TEXT,
            time BIGINT NOT NULL,
            trade_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        -- 포지션 그룹 테이블
        CREATE TABLE IF NOT EXISTS position_groups (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price DECIMAL NOT NULL,
            exit_price DECIMAL,
            quantity DECIMAL NOT NULL,
            pnl_amount DECIMAL NOT NULL,
            pnl_percentage DECIMAL NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            trade_count INTEGER NOT NULL,
            position_status TEXT NOT NULL, -- 'Open', 'Closed'
            close_date DATE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- 일별 P&L 요약 테이블
        CREATE TABLE IF NOT EXISTS daily_pnl (
            id BIGSERIAL PRIMARY KEY,
            trade_date DATE UNIQUE NOT NULL,
            daily_pnl_usd DECIMAL NOT NULL,
            trade_count INTEGER NOT NULL,
            trading_volume DECIMAL NOT NULL,
            position_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_trades_symbol_date ON trades(symbol, trade_date);
        CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(time);
        CREATE INDEX IF NOT EXISTS idx_position_groups_close_date ON position_groups(close_date);
        CREATE INDEX IF NOT EXISTS idx_position_groups_status ON position_groups(position_status);
        CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl(trade_date);
        """
        
        logging.info("⚠️  테이블 초기화 SQL이 준비되었습니다.")
        logging.info("Supabase 대시보드의 SQL Editor에서 다음 스크립트를 실행해주세요:")
        print("\n" + "="*80)
        print("SUPABASE SQL INITIALIZATION SCRIPT")
        print("="*80)
        print(tables_sql)
        print("="*80)
        
        return tables_sql

    async def save_trades(self, trades: List[Dict[str, Any]], trade_date: datetime):
        """거래 데이터를 Supabase에 저장"""
        if not trades:
            return
            
        try:
            # 거래 데이터 변환
            trade_records = []
            for trade in trades:
                trade_record = {
                    'trade_id': str(trade['id']),
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'price': float(trade['price']),
                    'qty': float(trade['qty']),
                    'commission': float(trade['commission']),
                    'commission_asset': trade['commissionAsset'],
                    'time': int(trade['time']),
                    'trade_date': trade_date.date().isoformat()
                }
                trade_records.append(trade_record)
            
            # 배치 삽입 (중복 무시)
            result = self.supabase.table('trades').upsert(
                trade_records, 
                on_conflict='trade_id'
            ).execute()
            
            logging.info(f"✅ {len(trade_records)}개 거래 데이터 저장 완료")
            return result
            
        except Exception as e:
            logging.error(f"거래 데이터 저장 실패: {e}")
            raise

    async def save_position_groups(self, position_groups: List[Dict[str, Any]]):
        """포지션 그룹 데이터를 Supabase에 저장"""
        if not position_groups:
            return
            
        try:
            position_records = []
            for group in position_groups:
                # 시간 문자열을 datetime으로 변환
                start_time = self._parse_time_string(group['start_time'])
                end_time = self._parse_time_string(group.get('end_time'))
                
                position_record = {
                    'symbol': group['symbol'],
                    'side': group['side'],
                    'entry_price': float(group['entry_price']),
                    'exit_price': float(group.get('exit_price', 0)),
                    'quantity': float(group['quantity']),
                    'pnl_amount': float(group['pnl_amount']),
                    'pnl_percentage': float(group['pnl_percentage']),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat() if end_time else None,
                    'duration_minutes': group.get('duration_minutes', 0),
                    'trade_count': group['trade_count'],
                    'position_status': group.get('position_type', 'Closed'),
                    'close_date': end_time.date().isoformat() if end_time else None
                }
                position_records.append(position_record)
            
            # 포지션 그룹 저장 (중복 방지)
            # 기존 포지션 그룹 삭제 후 새로 생성
            if position_records:
                # 기존 포지션 그룹 모두 삭제 (더 안전한 방법)
                try:
                    # 모든 레코드 삭제를 위해 항상 참인 조건 사용
                    self.supabase.table('position_groups').delete().gte('id', 0).execute()
                    logging.info("🗑️ 기존 포지션 그룹 삭제 완료")
                except Exception as e:
                    logging.warning(f"기존 포지션 그룹 삭제 중 오류 (무시하고 진행): {e}")
                
                # 새로운 포지션 그룹 저장
                result = self.supabase.table('position_groups').insert(
                    position_records
                ).execute()
            
            logging.info(f"✅ {len(position_records)}개 포지션 그룹 저장 완료")
            return result
            
        except Exception as e:
            logging.error(f"포지션 그룹 저장 실패: {e}")
            raise

    async def save_position_history(self, positions: List[Dict[str, Any]], trade_date: datetime):
        """포지션 히스토리 데이터를 Supabase에 저장 (거래 데이터로부터 포지션 그룹 생성)"""
        if not positions:
            return
            
        try:
            # 포지션 히스토리를 포지션 그룹으로 변환
            position_groups = []
            for position in positions:
                # 포지션 히스토리 데이터를 포지션 그룹 형식으로 변환
                position_group = {
                    'symbol': position.get('symbol', ''),
                    'side': position.get('side', 'Long'),
                    'entry_price': float(position.get('entryPrice', 0)),
                    'exit_price': float(position.get('exitPrice', 0)),
                    'quantity': float(position.get('quantity', 0)),
                    'pnl_amount': float(position.get('pnl', 0)),
                    'pnl_percentage': float(position.get('pnlPercentage', 0)),
                    'start_time': position.get('startTime', ''),
                    'end_time': position.get('endTime', ''),
                    'duration_minutes': int(position.get('durationMinutes', 0)),
                    'trade_count': int(position.get('tradeCount', 1)),
                    'position_type': 'Closed',
                    'position_status': 'Closed'
                }
                position_groups.append(position_group)
            
            # 포지션 그룹 저장
            if position_groups:
                await self.save_position_groups(position_groups)
            
            logging.info(f"✅ {len(position_groups)}개 포지션 히스토리 저장 완료")
            
        except Exception as e:
            logging.error(f"포지션 히스토리 저장 실패: {e}")
            raise

    async def update_position_groups(self, target_date: datetime = None):
        """포지션 그룹 업데이트 (PositionGrouper 사용) - 9시 기준 날짜 범위 지원"""
        try:
            from position_grouper import PositionGrouper
            
            logging.info("🔄 포지션 그룹 업데이트 시작...")
            
            # PositionGrouper를 사용하여 포지션 그룹 재생성
            grouper = PositionGrouper()
            position_groups = await grouper.create_all_position_groups(target_date)
            
            if target_date:
                logging.info(f"✅ {target_date.date()} (9시 기준) 포지션 그룹 업데이트 완료: {len(position_groups) if position_groups else 0}개")
            else:
                logging.info(f"✅ 전체 포지션 그룹 업데이트 완료: {len(position_groups) if position_groups else 0}개")
            
            return position_groups
            
        except Exception as e:
            logging.error(f"포지션 그룹 업데이트 실패: {e}")
            raise

    async def save_daily_pnl(self, daily_pnl_data: Dict[str, Any], trade_date: datetime):
        """일별 P&L 데이터를 Supabase에 저장"""
        try:
            pnl_record = {
                'trade_date': trade_date.date().isoformat(),
                'daily_pnl_usd': float(daily_pnl_data['daily_pnl_usd']),
                'trade_count': daily_pnl_data['trade_count'],
                'trading_volume': float(daily_pnl_data['trading_volume']),
                'position_count': daily_pnl_data['position_count']
            }
            
            # Upsert (날짜 기준으로 중복 방지)
            result = self.supabase.table('daily_pnl').upsert(
                pnl_record,
                on_conflict='trade_date'
            ).execute()
            
            logging.info(f"✅ {trade_date.date()} 일별 P&L 저장 완료")
            return result
            
        except Exception as e:
            logging.error(f"일별 P&L 저장 실패: {e}")
            raise

    async def get_all_trades(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """전체 거래 데이터 조회 (날짜 범위 옵션)"""
        try:
            query = self.supabase.table('trades').select('*')
            
            if start_date:
                query = query.gte('trade_date', start_date.date().isoformat())
            if end_date:
                query = query.lte('trade_date', end_date.date().isoformat())
                
            result = query.order('time').execute()
            
            logging.info(f"📊 {len(result.data)}개 거래 데이터 조회 완료")
            return result.data
            
        except Exception as e:
            logging.error(f"거래 데이터 조회 실패: {e}")
            return []

    async def get_closed_positions_for_date(self, target_date: datetime) -> List[Dict[str, Any]]:
        """특정 날짜에 완료된 포지션들만 조회 (9시 기준)"""
        try:
            # 해당 날짜의 9시부터 다음날 9시까지의 포지션 조회
            start_of_day = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # 1. 해당 날짜에 완료된 포지션들 (close_date 기준)
            result = self.supabase.table('position_groups').select('*').eq(
                'close_date', target_date.date().isoformat()
            ).eq(
                'position_status', 'Closed'
            ).order('start_time').execute()
            
            positions = result.data
            
            # 2. 해당 날짜에 시작되어 아직 완료되지 않은 포지션들 (start_time 기준)
            result2 = self.supabase.table('position_groups').select('*').gte(
                'start_time', start_of_day.isoformat()
            ).lt(
                'start_time', end_of_day.isoformat()
            ).eq(
                'position_status', 'Closed'
            ).order('start_time').execute()
            
            # 중복 제거하면서 합치기
            seen_ids = set()
            final_positions = []
            
            for pos in positions + result2.data:
                if pos['id'] not in seen_ids:
                    seen_ids.add(pos['id'])
                    final_positions.append(pos)
            
            logging.info(f"📊 {target_date.date()} 완료 포지션: {len(final_positions)}개")
            return final_positions
            
        except Exception as e:
            logging.error(f"완료 포지션 조회 실패: {e}")
            return []

    async def get_positions_for_date_range(self, target_date: datetime) -> List[Dict[str, Any]]:
        """특정 날짜 범위의 모든 포지션 조회 (9시 기준, 중복 포함)"""
        try:
            # 해당 날짜의 9시부터 다음날 9시까지의 포지션 조회
            start_of_day = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # 해당 날짜에 시작하거나 완료된 모든 포지션 조회
            result = self.supabase.table('position_groups').select('*').or_(
                f"start_time.gte.{start_of_day.isoformat()},start_time.lt.{end_of_day.isoformat()},close_date.eq.{target_date.date().isoformat()}"
            ).eq(
                'position_status', 'Closed'
            ).order('start_time').execute()
            
            positions = result.data
            
            # 포지션 시작/종료 시간을 datetime으로 변환
            for pos in positions:
                if pos.get('start_time'):
                    pos['start_datetime'] = self._parse_time_string(pos['start_time'])
                if pos.get('end_time'):
                    pos['end_datetime'] = self._parse_time_string(pos['end_time'])
            
            logging.info(f"📊 {target_date.date()} 관련 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"날짜 범위 포지션 조회 실패: {e}")
            return []

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """현재 열린 포지션들 조회"""
        try:
            result = self.supabase.table('position_groups').select('*').eq(
                'position_status', 'Open'
            ).order('start_time').execute()
            
            logging.info(f"📊 열린 포지션: {len(result.data)}개")
            return result.data
            
        except Exception as e:
            logging.error(f"열린 포지션 조회 실패: {e}")
            return []

    async def update_position_status(self, position_id: int, status: str, end_time: datetime = None, exit_price: float = None):
        """포지션 상태 업데이트 (Open -> Closed)"""
        try:
            update_data = {
                'position_status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if end_time:
                update_data['end_time'] = end_time.isoformat()
                update_data['close_date'] = end_time.date().isoformat()
                
            if exit_price:
                update_data['exit_price'] = exit_price
            
            result = self.supabase.table('position_groups').update(
                update_data
            ).eq('id', position_id).execute()
            
            logging.info(f"✅ 포지션 {position_id} 상태 업데이트: {status}")
            return result
            
        except Exception as e:
            logging.error(f"포지션 상태 업데이트 실패: {e}")
            raise

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """시간 문자열을 datetime으로 변환"""
        if not time_str:
            return None

        # ISO 형식의 datetime 파싱
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            # 레거시 시간 형식 처리 (%H:%M:%S)
            try:
                today = datetime.now().date()
                time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
                return datetime.combine(today, time_obj)
            except ValueError:
                logging.warning(f"시간 파싱 실패: {time_str}")
                return None

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """오래된 데이터 정리 (옵션)"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()
            
            # 오래된 거래 데이터 삭제
            result = self.supabase.table('trades').delete().lt(
                'trade_date', cutoff_date.isoformat()
            ).execute()
            
            logging.info(f"✅ {cutoff_date} 이전 데이터 정리 완료")
            return result
            
        except Exception as e:
            logging.error(f"데이터 정리 실패: {e}")
            raise

    async def test_connection(self):
        """Supabase 연결 테스트"""
        try:
            # 간단한 쿼리로 연결 확인
            result = self.supabase.table('trades').select('count').limit(1).execute()
            logging.info("✅ Supabase 연결 테스트 성공")
            return True
        except Exception as e:
            logging.error(f"❌ Supabase 연결 테스트 실패: {e}")
            return False 