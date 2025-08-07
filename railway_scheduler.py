#!/usr/bin/env python3
"""
Railway 스케줄러 - 매일 매매일지 자동 생성

Railway의 Cron Job 기능을 사용하여 매일 오전 9시 1분에 실행
"""

import asyncio
import os
import sys
from datetime import datetime
from main import EmotionalTradingJournal
from utils import logger

async def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 Railway 매매일지 생성 시작...")
        
        # Railway 스케줄러용 날짜 설정
        # UTC 9시 1분에 실행되므로 전날 매매일지 생성
        from datetime import timedelta
        target_date = datetime.now() - timedelta(days=1)
        
        logger.info(f"📅 Railway 스케줄러: {target_date.strftime('%Y-%m-%d')} 매매일지 생성")
        
        # 매매일지 시스템 초기화
        journal_system = EmotionalTradingJournal()
        
        # 매매일지 생성
        success = await journal_system.run_full_pipeline(target_date)
        
        if success:
            logger.info("✅ Railway 매매일지 생성 완료!")
            return 0
        else:
            logger.error("❌ Railway 매매일지 생성 실패")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Railway 실행 중 오류: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 