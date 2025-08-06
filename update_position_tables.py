#!/usr/bin/env python3
"""
📊 포지션별 상세 내역 업데이트 스크립트

8월 1일부터 8월 4일까지의 매매일지에서 포지션별 상세 내역만 업데이트합니다.
기존 컨텐츠는 그대로 두고 포지션 테이블만 새로운 형식으로 변경합니다.
"""

import asyncio
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 모듈 import
from config import Config
from utils import logger, setup_logging
from main import EmotionalTradingJournal
from notion_uploader import NotionUploader

async def update_position_tables_for_date_range(start_date: str, end_date: str):
    """지정된 날짜 범위의 포지션 테이블만 업데이트"""
    try:
        # 날짜 파싱
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 감성적인 매매일지 시스템 초기화
        journal_system = EmotionalTradingJournal()
        notion_uploader = journal_system.notion_uploader
        
        # 날짜 범위 생성
        current_date = start_dt
        total_days = (end_dt - start_dt).days + 1
        
        logger.info(f"📅 {start_date} ~ {end_date} 포지션 테이블 업데이트 시작 ({total_days}일)")
        print(f"📅 {start_date} ~ {end_date} 포지션 테이블 업데이트 시작 ({total_days}일)")
        
        success_count = 0
        failed_dates = []
        
        # 각 날짜별로 포지션 테이블 업데이트
        for i in range(total_days):
            current_date = start_dt + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            logger.info(f"📝 [{i+1}/{total_days}] {date_str} 포지션 테이블 업데이트 중...")
            print(f"📝 [{i+1}/{total_days}] {date_str} 포지션 테이블 업데이트 중...")
            
            try:
                # 기존 페이지 검색
                existing_page_id = await notion_uploader.find_existing_page_for_date(current_date)
                
                if not existing_page_id:
                    logger.warning(f"⚠️ {date_str} 기존 페이지를 찾을 수 없습니다.")
                    print(f"⚠️ {date_str} 기존 페이지를 찾을 수 없습니다.")
                    failed_dates.append(date_str)
                    continue
                
                # 해당 날짜의 포지션 데이터 조회
                if journal_system.supabase:
                    # Supabase 기반 포지션 조회
                    closed_positions = await journal_system.supabase.get_closed_positions_for_date(current_date)
                    
                    # 포지션 데이터 변환
                    positions = []
                    for pos in closed_positions:
                        position = {
                            'symbol': pos['symbol'],
                            'side': pos['side'],
                            'entry_price': float(pos['entry_price']),
                            'exit_price': float(pos['exit_price']),
                            'quantity': float(pos['quantity']),
                            'pnl_amount': float(pos['pnl_amount']),
                            'pnl_percentage': float(pos['pnl_percentage']),
                            'start_time': pos['start_time'][:8] if pos['start_time'] else 'N/A',  # HH:MM:SS 형식
                            'end_time': pos['end_time'][:8] if pos['end_time'] else '',
                            'duration_minutes': pos['duration_minutes'],
                            'trade_count': pos['trade_count'],
                            'position_type': 'Closed'
                        }
                        positions.append(position)
                else:
                    # 기존 방식으로 포지션 조회
                    start_time = current_date.replace(hour=9, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(days=1)
                    
                    # 거래 종목 자동 탐지
                    traded_symbols = await journal_system.binance.get_all_traded_symbols_for_date(start_time, end_time)
                    
                    if not traded_symbols:
                        logger.info(f"📊 {date_str} 거래 종목이 없습니다.")
                        positions = []
                    else:
                        # 모든 거래 데이터 수집
                        all_trades = []
                        all_position_history = []
                        
                        for symbol in traded_symbols:
                            # 거래 내역
                            trades = await journal_system.binance.get_account_trades(symbol, start_time, end_time)
                            all_trades.extend(trades)
                            
                            # 포지션 히스토리
                            positions_history = await journal_system.binance.get_position_history(symbol, start_time, end_time)
                            all_position_history.extend(positions_history)
                        
                        # 포지션 히스토리 생성
                        positions = journal_system._create_position_history_from_api(all_position_history, all_trades)
                
                # 기존 페이지 내용 가져오기
                children_response = notion_uploader.client.blocks.children.list(block_id=existing_page_id)
                existing_blocks = children_response['results']
                
                # 새로운 포지션 테이블 생성
                new_position_table = notion_uploader._create_position_table_section({'positions': positions})
                
                # 기존 블록들을 순회하면서 포지션 테이블 섹션만 교체
                updated_blocks = []
                in_position_section = False
                skip_until_next_heading = False
                
                for block in existing_blocks:
                    block_type = block.get('type', '')
                    
                    # 포지션 테이블 섹션 시작 확인
                    if block_type == 'heading_2':
                        heading_text = ''
                        if 'rich_text' in block['heading_2']:
                            for text in block['heading_2']['rich_text']:
                                heading_text += text.get('text', {}).get('content', '')
                        
                        if '포지션별 상세 내역' in heading_text:
                            in_position_section = True
                            skip_until_next_heading = True
                            # 새로운 포지션 테이블 섹션 추가
                            updated_blocks.extend(new_position_table)
                            continue
                        elif in_position_section and skip_until_next_heading:
                            # 포지션 섹션이 끝나고 다음 섹션 시작
                            in_position_section = False
                            skip_until_next_heading = False
                            updated_blocks.append(block)
                            continue
                        else:
                            in_position_section = False
                            skip_until_next_heading = False
                    
                    # 포지션 섹션 내부 블록들은 건너뛰기
                    if skip_until_next_heading:
                        continue
                    
                    # 포지션 섹션이 아닌 블록들은 그대로 유지
                    updated_blocks.append(block)
                
                # 기존 내용 삭제
                for block in existing_blocks:
                    try:
                        notion_uploader.client.blocks.delete(block_id=block['id'])
                    except:
                        pass  # 일부 블록은 삭제 불가능할 수 있음
                
                # 새 내용 추가
                if updated_blocks:
                    notion_uploader.client.blocks.children.append(
                        block_id=existing_page_id,
                        children=updated_blocks
                    )
                
                logger.info(f"✅ {date_str} 포지션 테이블 업데이트 완료!")
                print(f"✅ {date_str} 포지션 테이블 업데이트 완료!")
                success_count += 1
                
                # API 호출 제한을 위한 대기 (1초)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ {date_str} 포지션 테이블 업데이트 중 오류: {e}")
                print(f"❌ {date_str} 포지션 테이블 업데이트 중 오류: {e}")
                failed_dates.append(date_str)
        
        # 결과 요약
        logger.info(f"🎉 포지션 테이블 업데이트 완료! 성공: {success_count}/{total_days}")
        print(f"\n🎉 포지션 테이블 업데이트 완료!")
        print(f"✅ 성공: {success_count}/{total_days}일")
        
        if failed_dates:
            print(f"❌ 실패: {len(failed_dates)}일")
            print(f"   실패한 날짜: {', '.join(failed_dates)}")
        else:
            print("🎊 모든 날짜의 포지션 테이블이 성공적으로 업데이트되었습니다!")
        
        return success_count == total_days
        
    except Exception as e:
        logger.error(f"❌ 포지션 테이블 업데이트 중 오류: {e}")
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
        # 8/1~4일 포지션 테이블 업데이트
        start_date = "2025-08-01"
        end_date = "2025-08-04"
        
        print("🚀 8/1~4일 포지션 테이블 업데이트 시작!")
        print("=" * 50)
        
        success = await update_position_tables_for_date_range(start_date, end_date)
        
        if success:
            print("\n🎉 모든 포지션 테이블이 성공적으로 업데이트되었습니다!")
        else:
            print("\n⚠️ 일부 포지션 테이블 업데이트에 실패했습니다. 로그를 확인해주세요.")
        
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