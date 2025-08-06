#!/usr/bin/env python3
"""
Supabase 테이블 중복 데이터 확인 스크립트
"""

import asyncio
from supabase_manager import SupabaseManager
from utils import logger

async def check_duplicates():
    """trades와 position_groups 테이블의 중복 데이터 확인"""
    try:
        logger.info("🔍 Supabase 테이블 중복 데이터 확인 시작...")
        
        # Supabase 연결
        supabase = SupabaseManager()
        
        # 1. trades 테이블 중복 확인
        logger.info("📊 trades 테이블 중복 확인...")
        trades = await supabase.get_all_trades()
        
        # trade_id 기준 중복 확인
        trade_ids = [trade['trade_id'] for trade in trades]
        duplicate_trade_ids = [tid for tid in set(trade_ids) if trade_ids.count(tid) > 1]
        
        if duplicate_trade_ids:
            logger.warning(f"⚠️ trades 테이블에 중복된 trade_id 발견: {len(duplicate_trade_ids)}개")
            logger.warning(f"중복된 trade_ids: {duplicate_trade_ids[:10]}...")  # 처음 10개만 표시
        else:
            logger.info("✅ trades 테이블에 중복 데이터 없음")
        
        # 2. position_groups 테이블 중복 확인
        logger.info("📊 position_groups 테이블 중복 확인...")
        
        # 모든 포지션 그룹 조회
        result = supabase.supabase.table('position_groups').select('*').execute()
        position_groups = result.data
        
        # 중복 확인을 위한 키 생성 (symbol + start_time + side)
        position_keys = []
        for pos in position_groups:
            key = f"{pos['symbol']}_{pos['start_time']}_{pos['side']}"
            position_keys.append(key)
        
        duplicate_position_keys = [key for key in set(position_keys) if position_keys.count(key) > 1]
        
        if duplicate_position_keys:
            logger.warning(f"⚠️ position_groups 테이블에 중복된 포지션 발견: {len(duplicate_position_keys)}개")
            logger.warning(f"중복된 포지션 키: {duplicate_position_keys[:10]}...")  # 처음 10개만 표시
        else:
            logger.info("✅ position_groups 테이블에 중복 데이터 없음")
        
        # 3. 통계 정보
        logger.info("📈 테이블 통계:")
        logger.info(f"   - trades 테이블: {len(trades)}개 레코드")
        logger.info(f"   - position_groups 테이블: {len(position_groups)}개 레코드")
        
        # 4. 최근 데이터 확인
        logger.info("📅 최근 데이터 확인:")
        if trades:
            latest_trade = max(trades, key=lambda x: x['time'])
            logger.info(f"   - 최근 거래: {latest_trade['symbol']} ({latest_trade['trade_date']})")
        
        if position_groups:
            latest_position = max(position_groups, key=lambda x: x['start_time'])
            logger.info(f"   - 최근 포지션: {latest_position['symbol']} ({latest_position['start_time'][:10]})")
        
        logger.info("✅ 중복 데이터 확인 완료!")
        
    except Exception as e:
        logger.error(f"❌ 중복 데이터 확인 실패: {e}")

if __name__ == "__main__":
    asyncio.run(check_duplicates()) 