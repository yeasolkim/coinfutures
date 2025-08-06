#!/usr/bin/env python3
"""
Supabase position_groups 테이블 중복 데이터 정리 스크립트
"""

import asyncio
from supabase_manager import SupabaseManager
from utils import logger

async def cleanup_duplicates():
    """position_groups 테이블의 중복 데이터 정리"""
    try:
        logger.info("🧹 position_groups 테이블 중복 데이터 정리 시작...")
        
        # Supabase 연결
        supabase = SupabaseManager()
        
        # 모든 포지션 그룹 조회
        result = supabase.supabase.table('position_groups').select('*').execute()
        position_groups = result.data
        
        logger.info(f"📊 총 {len(position_groups)}개 포지션 발견")
        
        # 중복 제거를 위한 딕셔너리 생성
        unique_positions = {}
        duplicates_to_remove = []
        
        for pos in position_groups:
            # 고유 키 생성 (symbol + start_time + side)
            key = f"{pos['symbol']}_{pos['start_time']}_{pos['side']}"
            
            if key in unique_positions:
                # 중복 발견 - 나중에 생성된 것(더 큰 ID)을 제거 대상으로
                existing_id = unique_positions[key]['id']
                current_id = pos['id']
                
                if current_id > existing_id:
                    # 현재 것이 더 최신이면 기존 것을 제거 대상으로
                    duplicates_to_remove.append(existing_id)
                    unique_positions[key] = pos
                else:
                    # 기존 것이 더 최신이면 현재 것을 제거 대상으로
                    duplicates_to_remove.append(current_id)
            else:
                unique_positions[key] = pos
        
        logger.info(f"📈 중복 제거 후 고유 포지션: {len(unique_positions)}개")
        logger.info(f"🗑️ 제거할 중복 포지션: {len(duplicates_to_remove)}개")
        
        if duplicates_to_remove:
            # 중복 데이터 삭제
            for pos_id in duplicates_to_remove:
                try:
                    supabase.supabase.table('position_groups').delete().eq('id', pos_id).execute()
                    logger.info(f"✅ 중복 포지션 삭제: ID {pos_id}")
                except Exception as e:
                    logger.error(f"❌ 포지션 삭제 실패 (ID {pos_id}): {e}")
            
            logger.info(f"🎉 중복 데이터 정리 완료! {len(duplicates_to_remove)}개 제거")
        else:
            logger.info("✅ 중복 데이터가 없습니다.")
        
        # 정리 후 통계
        result_after = supabase.supabase.table('position_groups').select('*').execute()
        position_groups_after = result_after.data
        
        logger.info(f"📊 정리 후 포지션 수: {len(position_groups_after)}개")
        
    except Exception as e:
        logger.error(f"❌ 중복 데이터 정리 실패: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates()) 