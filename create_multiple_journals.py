#!/usr/bin/env python3
"""
📅 다중 날짜 매매일지 생성 스크립트

8/1~4일까지의 매매일지를 순차적으로 생성하여 Notion에 업로드합니다.
"""

import asyncio
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 모듈 import
from config import Config
from utils import logger, setup_logging
from main import EmotionalTradingJournal

async def create_journals_for_date_range(start_date: str, end_date: str):
    """지정된 날짜 범위의 매매일지 생성"""
    try:
        # 날짜 파싱
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 감성적인 매매일지 시스템 초기화
        journal_system = EmotionalTradingJournal()
        
        # 날짜 범위 생성
        current_date = start_dt
        total_days = (end_dt - start_dt).days + 1
        
        logger.info(f"📅 {start_date} ~ {end_date} 매매일지 생성 시작 ({total_days}일)")
        print(f"📅 {start_date} ~ {end_date} 매매일지 생성 시작 ({total_days}일)")
        
        success_count = 0
        failed_dates = []
        
        # 각 날짜별로 매매일지 생성
        for i in range(total_days):
            current_date = start_dt + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            logger.info(f"📝 [{i+1}/{total_days}] {date_str} 매매일지 생성 중...")
            print(f"📝 [{i+1}/{total_days}] {date_str} 매매일지 생성 중...")
            
            try:
                # 매매일지 생성
                success = await journal_system.run_full_pipeline(current_date)
                
                if success:
                    logger.info(f"✅ {date_str} 매매일지 생성 완료!")
                    print(f"✅ {date_str} 매매일지 생성 완료!")
                    success_count += 1
                else:
                    logger.error(f"❌ {date_str} 매매일지 생성 실패")
                    print(f"❌ {date_str} 매매일지 생성 실패")
                    failed_dates.append(date_str)
                
                # API 호출 제한을 위한 대기 (1초)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ {date_str} 매매일지 생성 중 오류: {e}")
                print(f"❌ {date_str} 매매일지 생성 중 오류: {e}")
                failed_dates.append(date_str)
        
        # 결과 요약
        logger.info(f"🎉 매매일지 생성 완료! 성공: {success_count}/{total_days}")
        print(f"\n🎉 매매일지 생성 완료!")
        print(f"✅ 성공: {success_count}/{total_days}일")
        
        if failed_dates:
            print(f"❌ 실패: {len(failed_dates)}일")
            print(f"   실패한 날짜: {', '.join(failed_dates)}")
        else:
            print("🎊 모든 날짜의 매매일지가 성공적으로 생성되었습니다!")
        
        return success_count == total_days
        
    except Exception as e:
        logger.error(f"❌ 다중 매매일지 생성 중 오류: {e}")
        print(f"❌ 오류: {e}")
        return False

async def main():
    """메인 실행 함수"""
    # 설정 유효성 검사
    config_status = Config.validate_config()
    if not config_status['is_valid']:
        logger.error("❌ 설정 오류:")
        for error in config_status['errors']:
            logger.error(f"   - {error}")
        sys.exit(1)
    
    try:
        # 8/1~4일 매매일지 생성
        start_date = "2025-08-01"
        end_date = "2025-08-04"
        
        print("🚀 8/1~4일 매매일지 자동 생성 시작!")
        print("=" * 50)
        
        success = await create_journals_for_date_range(start_date, end_date)
        
        if success:
            print("\n🎉 모든 매매일지가 성공적으로 생성되었습니다!")
        else:
            print("\n⚠️ 일부 매매일지 생성에 실패했습니다. 로그를 확인해주세요.")
        
    except KeyboardInterrupt:
        logger.info("👋 사용자에 의해 중단되었습니다.")
        print("\n👋 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        print(f"❌ 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 로깅 설정
    setup_logging()
    
    # 이벤트 루프 실행
    asyncio.run(main()) 