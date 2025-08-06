#!/usr/bin/env python3
"""
Binance → Supabase 데이터 동기화 테스트 스크립트

이 스크립트는 Binance에서 데이터를 가져와서 Supabase의 
trades, position_groups, daily_pnl 테이블을 업데이트하는 기능을 테스트합니다.
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from main import EmotionalTradingJournal
from utils import logger

async def test_binance_sync(target_date: datetime):
    """Binance → Supabase 동기화 테스트"""
    try:
        logger.info("🧪 Binance → Supabase 동기화 테스트 시작...")
        
        # 매매일지 시스템 초기화
        journal_system = EmotionalTradingJournal()
        
        if not journal_system.supabase:
            logger.error("❌ Supabase 연결이 설정되지 않았습니다.")
            return False
        
        # Supabase 연결 테스트
        logger.info("🔗 Supabase 연결 테스트...")
        connection_ok = await journal_system.supabase.test_connection()
        if not connection_ok:
            logger.error("❌ Supabase 연결 테스트 실패")
            return False
        
        logger.info("✅ Supabase 연결 테스트 성공")
        
        # Binance → Supabase 동기화 실행
        logger.info(f"🔄 {target_date.strftime('%Y-%m-%d')} 데이터 동기화 시작...")
        await journal_system._sync_all_data_to_supabase(target_date)
        
        # 동기화 결과 확인
        logger.info("📊 동기화 결과 확인...")
        
        # 1. 거래 데이터 확인
        trades = await journal_system.supabase.get_all_trades(
            start_date=target_date - timedelta(days=7),
            end_date=target_date
        )
        logger.info(f"📈 최근 7일 거래 데이터: {len(trades)}개")
        
        # 2. 포지션 그룹 확인
        closed_positions = await journal_system.supabase.get_closed_positions_for_date(target_date)
        logger.info(f"📊 {target_date.date()} 완료 포지션: {len(closed_positions)}개")
        
        # 3. 일별 P&L 확인
        daily_pnl = await journal_system.binance.get_daily_pnl(target_date)
        logger.info(f"💰 {target_date.date()} 일별 P&L: ${daily_pnl['daily_pnl_usd']:.2f}")
        
        logger.info("✅ Binance → Supabase 동기화 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Binance → Supabase 동기화 테스트")
    parser.add_argument("--date", type=str, help="테스트할 날짜 (YYYY-MM-DD)", 
                       default=datetime.now().strftime("%Y-%m-%d"))
    
    args = parser.parse_args()
    
    try:
        # 날짜 파싱
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
        
        print("🚀 === Binance → Supabase 동기화 테스트 ===")
        print(f"📅 테스트 날짜: {target_date.strftime('%Y-%m-%d')}")
        print("=" * 50)
        
        success = await test_binance_sync(target_date)
        
        if success:
            print("\n🎉 테스트 성공!")
            print("💡 이제 매매일지 생성이 가능합니다.")
        else:
            print("\n❌ 테스트 실패!")
            print("🔧 설정을 확인하고 다시 시도해주세요.")
            
    except ValueError:
        print("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 