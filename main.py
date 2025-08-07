#!/usr/bin/env python3
"""
🎯 감성적인 바이낸스 선물 매매일지 자동화 시스템

이 시스템은 바이낸스 선물 거래 데이터를 기반으로
감정적이고 인간적인 매매일지를 자동으로 Notion에 생성합니다.

사용법:
    python main.py --date 2025-01-15    # 특정 날짜
    python main.py                      # 오늘 날짜
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os

# 프로젝트 모듈 import
from config import Config
from utils import logger, ensure_directory_exists, timestamp_to_datetime
from binance_connector import BinanceConnector
from profit_calculator import ProfitCalculator
# from gpt_feedback import GPTFeedbackGenerator
from sentiment_generator import SentimentGenerator
from notion_uploader import NotionUploader
from supabase_manager import SupabaseManager

class EmotionalTradingJournal:
    """감성적인 매매일지 생성 시스템"""
    
    def __init__(self):
        """시스템 초기화"""
        logger.info("🎯 감성적인 매매일지 시스템 초기화 시작...")
        
        # 핵심 컴포넌트 초기화
        self.binance = BinanceConnector()
        self.profit_calc = ProfitCalculator()
        # self.gpt_feedback = GPTFeedbackGenerator()  # OpenAI 기능 비활성화
        self.sentiment = SentimentGenerator()
        self.notion_uploader = NotionUploader()
        
        # Supabase 매니저 초기화 (옵션)
        self.supabase = None
        try:
            self.supabase = SupabaseManager()
            logger.info("✅ Supabase 연결 완료")
        except Exception as e:
            logger.warning(f"⚠️  Supabase 연결 실패 (기존 방식으로 진행): {e}")
        
        logger.info("✅ 모든 컴포넌트 초기화 완료!")

    async def run_full_pipeline(self, target_date: datetime) -> bool:
        """전체 파이프라인 실행"""
        try:
            logger.info(f"📅 {target_date.strftime('%Y-%m-%d')} 매매일지 생성 시작...")
            
            # Supabase 사용 가능하면 새로운 방식, 아니면 기존 방식
            if self.supabase:
                return await self._run_supabase_pipeline(target_date)
            else:
                return await self._run_legacy_pipeline(target_date)
                
        except Exception as e:
            logger.error(f"❌ 파이프라인 실행 중 오류 발생: {e}")
            return False

    async def _run_supabase_pipeline(self, target_date: datetime) -> bool:
        """Supabase 기반 새로운 파이프라인"""
        try:
            logger.info("🚀 매매일지 생성 파이프라인 시작...")
            logger.info("=" * 60)
            
            # 1. Binance → Supabase 데이터 동기화
            logger.info("📊 STEP 1: Binance에서 최신 데이터 수집 및 Supabase 업데이트")
            await self._sync_all_data_to_supabase(target_date)
            logger.info("=" * 60)
            
            # 2. 해당 날짜에 완료된 포지션만 조회
            logger.info("📊 STEP 2: 완료된 포지션 데이터 조회")
            closed_positions = await self.supabase.get_closed_positions_for_date(target_date)
            logger.info(f"✅ {len(closed_positions)}개 완료 포지션 발견")
            logger.info("=" * 60)
            
            # 3. 일별 P&L 데이터 조회
            logger.info("📊 STEP 3: 일별 P&L 데이터 조회")
            daily_pnl_data = await self.binance.get_daily_pnl(target_date)
            logger.info(f"✅ 일별 P&L: ${daily_pnl_data['daily_pnl_usd']:.2f}")
            logger.info("=" * 60)
            
            # 4. 매매일지 데이터 구성
            logger.info("📝 STEP 4: 매매일지 데이터 구성")
            journal_data = await self._create_journal_data_from_supabase(
                target_date, closed_positions, daily_pnl_data
            )
            logger.info("✅ 매매일지 데이터 구성 완료")
            logger.info("=" * 60)
            
            # 5. Notion 업로드
            logger.info("📤 STEP 5: Notion에 매매일지 업로드")
            success = await self.notion_uploader.create_emotional_journal_page(journal_data)
            
            if success:
                logger.info("✅ Notion 업로드 완료!")
                logger.info("🎉 매매일지 생성 파이프라인 완료!")
                return True
            else:
                logger.error("❌ Notion 업로드 실패")
                return False
            
        except Exception as e:
            logger.error(f"❌ Supabase 파이프라인 실행 중 오류: {e}")
            return False

    async def _run_legacy_pipeline(self, target_date: datetime) -> bool:
        """기존 방식의 파이프라인 (하루치 데이터 기반)"""
        try:
            logger.info("📊 거래 데이터 수집 중...")
            
            # 시간 범위 설정
            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            # 거래 종목 자동 탐지
            logger.info(f"거래 종목 자동 탐지: {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}")
            traded_symbols = await self.binance.get_all_traded_symbols_for_date(start_time, end_time)
            
            if not traded_symbols:
                logger.warning("❌ 거래 종목을 찾을 수 없습니다!")
                return False
            
            logger.info(f"자동 탐지된 거래 종목: {len(traded_symbols)}개 - {', '.join(traded_symbols)}")
            logger.info(f"🎯 분석할 종목들: {', '.join(traded_symbols)}")
            
            # 모든 거래 데이터 수집
            all_trades = []
            all_position_history = []
            all_kline_data = {}
            
            for symbol in traded_symbols:
                # 거래 내역
                trades = await self.binance.get_account_trades(symbol, start_time, end_time)
                all_trades.extend(trades)
                
                # 포지션 히스토리
                positions = await self.binance.get_position_history(symbol, start_time, end_time)
                all_position_history.extend(positions)
                
                # K라인 데이터
                klines = await self.binance.get_kline_data(symbol, '5m', start_time, end_time)
                all_kline_data[symbol] = klines
            
            logger.info(f"💹 총 {len(all_trades)}개의 거래 발견")
            logger.info(f"📊 총 {len(all_position_history)}개의 포지션 수익 발견")
            
            if not all_trades:
                logger.warning("❌ 거래 데이터가 없습니다!")
                return await self._create_empty_journal(target_date)
            
            # 수익률 계산
            logger.info("💰 수익률 계산 중...")
            
            # Daily P&L 계산 (API 기반)
            logger.info(f"Daily P&L 조회: {target_date.strftime('%Y-%m-%d')}")
            daily_pnl_data = await self.binance.get_daily_pnl(target_date)
            logger.info(f"Daily P&L 조회 완료: {daily_pnl_data['daily_pnl_usd']:.2f} USD (거래 {daily_pnl_data['trade_count']}건, 거래량 {daily_pnl_data['trading_volume']:.2f} USDT)")
            
                        # 수익률 계산 (거래량 기준)
            if daily_pnl_data['trading_volume'] > 0:
                daily_pnl_data['daily_pnl_percentage'] = (daily_pnl_data['daily_pnl_usd'] / daily_pnl_data['trading_volume']) * 100
            else:
                daily_pnl_data['daily_pnl_percentage'] = 0.0
            
            # 포지션 히스토리 생성 (Net Position 기반)
            logger.info("📊 포지션 히스토리 생성 중...")
            positions = self._create_position_history_from_api(all_position_history, all_trades)
            logger.info(f"Net Position 기준 포지션 그룹핑 완료: {len(positions)}개 포지션 그룹")
            
            # 시장 분석
            market_type = self.profit_calc.get_market_type(positions, all_kline_data)
            difficulty_level = self.profit_calc.get_difficulty_level(positions, 0.5)  # 기본 승률
            market_analysis = {
                'market_type': market_type,
                'difficulty_level': difficulty_level
            }
            
            # 감정적 요소 생성
            logger.info("😊 감정적 요소 생성 중...")
            
            # 일별 요약 데이터 구성
            daily_summary = {
                'date': target_date.strftime('%Y년 %m월 %d일'),
                'daily_pnl_percentage': daily_pnl_data['daily_pnl_percentage'],
                'daily_pnl_usd': daily_pnl_data['daily_pnl_usd'],
                'trade_count': daily_pnl_data['trade_count'],
                'trading_volume': daily_pnl_data['trading_volume'],
                'position_count': len(positions)
            }
            
            # 감정적 제목 생성
            emotional_title = self.sentiment.generate_emotional_title(daily_summary)
            
            # 매매일지 데이터 구성
            journal_data = {
                'date': target_date,
                'title': emotional_title,
                'emotional_rate': self.sentiment.get_emotion_rate(daily_summary, positions),
                'market_type': market_analysis['market_type'],
                'difficulty_level': market_analysis['difficulty_level'],
                'daily_summary': daily_summary,
                'positions': positions,
                'trading_symbols': traded_symbols
            }
            
            logger.info("✅ 매매일지 데이터 생성 완료!")
            
            # daily_pnl 테이블에 매매 요약 저장 (Supabase 사용 가능한 경우만)
            if self.supabase:
                await self._save_daily_pnl_to_supabase(target_date, journal_data)
            
            # Notion 업로드
            logger.info("📝 Notion 업로드 시작...")
            success = await self.notion_uploader.create_emotional_journal_page(journal_data)
            
            if success:
                logger.info("✅ Notion 업로드 완료!")
                return True
            else:
                logger.error("❌ Notion 업로드 실패")
                return False
            
        except Exception as e:
            logger.error(f"❌ Notion 업로드 중 오류: {e}")
            return False

    async def _sync_all_data_to_supabase(self, target_date: datetime):
        """Binance에서 데이터를 가져와서 Supabase의 trades, position_groups, daily_pnl 테이블 업데이트"""
        try:
            logger.info(f"🔄 Binance → Supabase 데이터 동기화 시작...")
            
            # 1. 최근 7일간의 거래 종목 수집 (API 제한 우회)
            all_symbols = set()
            for i in range(7):  # 7일간
                check_date = target_date - timedelta(days=i)
                start_time = check_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
                
                symbols = await self.binance.get_all_traded_symbols_for_date(start_time, end_time)
                all_symbols.update(symbols)
            
            logger.info(f"📊 발견된 거래 종목: {len(all_symbols)}개")
            
            # 2. 각 종목별로 거래 데이터 수집 및 저장 (최적화)
            total_trades_saved = 0
            for symbol in all_symbols:
                # 해당 종목의 최신 거래 데이터 확인
                latest_trade = await self._get_latest_trade_for_symbol(symbol)
                
                if latest_trade:
                    # 이미 저장된 최신 거래 이후부터만 수집
                    latest_time = latest_trade['time']
                    logger.info(f"📊 {symbol}: 최신 거래 시간 {latest_time} 이후부터 수집")
                else:
                    # 처음 수집하는 종목이면 최근 7일간 수집
                    latest_time = None
                    logger.info(f"📊 {symbol}: 처음 수집, 최근 7일간 데이터 수집")
                
                # 최신 거래 이후의 데이터만 수집
                for i in range(7):  # 7일간 일별로
                    sync_date = target_date - timedelta(days=i)
                    start_time = sync_date.replace(hour=9, minute=0, second=0, microsecond=0)
                    end_time = start_time + timedelta(days=1)
                    
                    # 이미 저장된 데이터는 건너뛰기
                    if latest_time and start_time.timestamp() * 1000 <= latest_time:
                        continue
                    
                    # 거래 데이터 수집 및 저장
                    trades = await self.binance.get_account_trades(symbol, start_time, end_time)
                    if trades:
                        await self.supabase.save_trades(trades, sync_date)
                        total_trades_saved += len(trades)
                        logger.info(f"✅ {symbol} ({sync_date.date()}): {len(trades)}개 거래 저장")
            
            logger.info(f"📊 총 {total_trades_saved}개 거래 데이터 저장 완료")
            
            # 3. 포지션 그룹핑 업데이트 (해당 날짜 9시 기준으로 포지션 그룹 재생성)
            logger.info("🔄 포지션 그룹핑 업데이트 중...")
            position_groups = await self.supabase.update_position_groups(target_date)
            
            # 4. 일별 P&L 데이터 수집 및 저장
            logger.info("📊 일별 P&L 데이터 수집 중...")
            daily_pnl_data = await self.binance.get_daily_pnl(target_date)
            
            # daily_pnl 테이블에 저장할 데이터 구성
            daily_pnl_record = {
                'daily_pnl_usd': daily_pnl_data['daily_pnl_usd'],
                'trade_count': daily_pnl_data['trade_count'],
                'trading_volume': daily_pnl_data['trading_volume'],
                'position_count': len(position_groups) if position_groups else 0
            }
            
            await self.supabase.save_daily_pnl(daily_pnl_record, target_date)
            
            logger.info("✅ Binance → Supabase 데이터 동기화 완료!")
            logger.info(f"   - 거래 데이터: {total_trades_saved}개")
            logger.info(f"   - 포지션 그룹: {len(position_groups) if position_groups else 0}개")
            logger.info(f"   - 일별 P&L: {target_date.date()}")
            
        except Exception as e:
            logger.error(f"❌ Supabase 데이터 동기화 실패: {e}")
            raise

    async def _get_latest_trade_for_symbol(self, symbol: str) -> Optional[Dict]:
        """특정 종목의 최신 거래 데이터 조회"""
        try:
            result = self.supabase.supabase.table('trades').select('*').eq(
                'symbol', symbol
            ).order('time', desc=True).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ {symbol} 최신 거래 조회 실패: {e}")
            return None

    async def _create_journal_data_from_supabase(self, target_date: datetime, closed_positions: List[Dict], daily_pnl_data: Dict) -> Dict:
        """Supabase 데이터로부터 매매일지 데이터 생성"""
        try:
            # 포지션별 수수료 계산을 위해 해당 날짜의 거래 데이터 조회
            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            daily_trades = await self.supabase.get_all_trades(start_time, end_time)
            
            # 포지션별 거래 데이터 매핑
            position_trades = {}
            for trade in daily_trades:
                symbol = trade['symbol']
                if symbol not in position_trades:
                    position_trades[symbol] = []
                position_trades[symbol].append(trade)
            
            # 포지션 데이터 변환 (수수료 정보 추가)
            positions = []
            for pos in closed_positions:
                symbol = pos['symbol']
                symbol_trades = position_trades.get(symbol, [])
                
                # 해당 포지션 기간의 거래들 필터링 (시간 범위로 추정)
                position_start = datetime.fromisoformat(pos['start_time'])
                position_end = datetime.fromisoformat(pos['end_time']) if pos['end_time'] else position_start
                
                # 포지션 기간과 겹치는 거래들 찾기
                position_related_trades = []
                for trade in symbol_trades:
                    trade_time = datetime.fromtimestamp(trade['time'] / 1000)
                    if position_start <= trade_time <= position_end:
                        position_related_trades.append(trade)
                
                # 수수료 계산
                total_commission = sum(float(trade['commission']) for trade in position_related_trades)
                
                # 시간 정보를 Supabase 데이터 그대로 사용
                # 진입 시간 (HH:MM:SS 형식)
                entry_time_str = pos['start_time'][11:16] if len(pos['start_time']) >= 16 else pos['start_time']
                
                # 종료 시간 (HH:MM:SS 형식)
                exit_time_str = ''
                if pos['end_time']:
                    exit_time_str = pos['end_time'][11:16] if len(pos['end_time']) >= 16 else pos['end_time']
                
                # 보유 기간 계산
                duration_hours = pos['duration_minutes'] // 60
                duration_minutes = pos['duration_minutes'] % 60
                if duration_hours > 0:
                    duration_str = f"{duration_hours}시간 {duration_minutes}분"
                else:
                    duration_str = f"{duration_minutes}분"
                
                position = {
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'entry_price': float(pos['entry_price']),
                    'exit_price': float(pos['exit_price']),
                    'quantity': float(pos['quantity']),
                    'pnl_amount': float(pos['pnl_amount']),  # 순수익 (가격 차익)
                    'pnl_percentage': float(pos['pnl_percentage']),
                    'entry_time': entry_time_str,  # 한국 시간 진입시점
                    'exit_time': exit_time_str,  # 한국 시간 종료시점
                    'duration': duration_str,  # 보유기간
                    'duration_minutes': pos['duration_minutes'],
                    'trade_count': pos['trade_count'],
                    'commission': total_commission,  # 수수료 추가
                    'actual_pnl': float(pos['pnl_amount']) - total_commission,  # 실손익
                    'position_type': 'Closed'
                }
                positions.append(position)
            
            # 일별 요약 데이터
            daily_summary = {
                'date': target_date.strftime('%Y년 %m월 %d일'),
                'daily_pnl_percentage': (daily_pnl_data['daily_pnl_usd'] / daily_pnl_data['trading_volume'] * 100) if daily_pnl_data['trading_volume'] > 0 else 0.0,
                'daily_pnl_usd': daily_pnl_data['daily_pnl_usd'],
                'trade_count': daily_pnl_data['trade_count'],
                'trading_volume': daily_pnl_data['trading_volume'],
                'position_count': len(positions)
            }
            
            # 승률 계산
            win_positions = [pos for pos in positions if float(pos.get('pnl_amount', 0)) > 0]
            win_rate = (len(win_positions) / len(positions) * 100) if positions else 0
            
            # 시장 분석 (Supabase에서는 간소화)
            market_analysis = {
                'market_type': '횡보장',  # 간소화 (price_data 없이 판단하기 어려움)
                'difficulty_level': self.profit_calc.get_difficulty_level(positions, win_rate)
            }
            
            # 감정적 요소 생성
            emotional_title = self.sentiment.generate_emotional_title(daily_summary)
            
            # 매매일지 데이터 구성
            return {
                'date': target_date,
                'title': emotional_title,
                'emotional_rate': self.sentiment.get_emotion_rate(daily_summary, positions),
                'market_type': market_analysis['market_type'],
                'difficulty_level': market_analysis['difficulty_level'],
                'daily_summary': daily_summary,
                'positions': positions,
                'trading_symbols': list(set(pos['symbol'] for pos in positions))
            }
            
        except Exception as e:
            logger.error(f"❌ Supabase 매매일지 데이터 생성 실패: {e}")
            raise

    def _create_position_history_from_api(self, all_position_history: List[Dict], all_trades: List[Dict]) -> List[Dict]:
        """API 데이터로부터 포지션 히스토리 생성 (Net Position 그룹핑)"""
        try:
            # 심볼별로 그룹핑
            symbol_groups = {}
            for pos in all_position_history:
                symbol = pos['symbol']
                if symbol not in symbol_groups:
                    symbol_groups[symbol] = []
                symbol_groups[symbol].append(pos)
            
            # 거래 데이터도 심볼별로 그룹핑
            trades_by_symbol = {}
            for trade in all_trades:
                symbol = trade['symbol']
                if symbol not in trades_by_symbol:
                    trades_by_symbol[symbol] = []
                trades_by_symbol[symbol].append(trade)
            
            # 각 심볼별로 Net Position 그룹핑
            all_position_groups = []
            for symbol in symbol_groups:
                symbol_positions = symbol_groups[symbol]
                symbol_trades = trades_by_symbol.get(symbol, [])
                
                position_groups = self._group_positions_by_net_position(symbol, symbol_positions, symbol_trades)
                all_position_groups.extend(position_groups)
            
            # PnL 기준으로 내림차순 정렬
            all_position_groups.sort(key=lambda x: x['pnl_amount'], reverse=True)
            
            return all_position_groups
            
        except Exception as e:
            logger.error(f"❌ 포지션 히스토리 생성 실패: {e}")
            return []

    def _group_positions_by_net_position(self, symbol: str, positions: List[Dict], trades: List[Dict]) -> List[Dict]:
        """Net Position 기준으로 포지션 그룹핑"""
        try:
            # 거래를 시간순으로 정렬
            trades.sort(key=lambda x: int(x['time']))
            
            # Trade ID별 PnL 매핑
            pnl_map = {}
            for pos in positions:
                trade_id = str(pos.get('tradeId', ''))
                if trade_id:
                    pnl_map[trade_id] = float(pos.get('income', 0))
            
            position_groups = []
            current_group_trades = []
            current_net_position = 0.0
            
            for trade in trades:
                price = float(trade['price'])
                qty = float(trade['qty'])
                side = trade['side']
                
                # 거래량 방향 설정 (BUY는 +, SELL은 -)
                trade_qty = qty if side == 'BUY' else -qty
                prev_net_position = current_net_position
                current_net_position += trade_qty
                
                current_group_trades.append(trade)
                
                # Net position이 0에 도달하면 포지션 그룹 완료
                if abs(current_net_position) < 0.1 and len(current_group_trades) > 1:
                    group_pnl = sum(pnl_map.get(str(t.get('id', '')), 0) for t in current_group_trades)
                    
                    if abs(group_pnl) > 0.001:  # 유의미한 손익만
                        # 그룹의 첫 거래와 마지막 거래
                        first_trade = current_group_trades[0]
                        last_trade = current_group_trades[-1]
                        
                        # 포지션 방향 결정
                        if prev_net_position > 0:
                            position_side = 'Long'
                            # 진입 거래들 (BUY)
                            entry_trades = [t for t in current_group_trades if t['side'] == 'BUY']
                        else:
                            position_side = 'Short'
                            # 진입 거래들 (SELL)
                            entry_trades = [t for t in current_group_trades if t['side'] == 'SELL']
                        
                        # 평균 진입가 계산
                        if entry_trades:
                            total_cost = sum(float(t['price']) * float(t['qty']) for t in entry_trades)
                            total_qty = sum(float(t['qty']) for t in entry_trades)
                            avg_entry_price = total_cost / total_qty if total_qty > 0 else float(first_trade['price'])
                        else:
                            avg_entry_price = float(first_trade['price'])
                            total_qty = sum(float(t['qty']) for t in current_group_trades)
                        
                        # 청산가 (마지막 거래 가격)
                        exit_price = float(last_trade['price'])
                        
                        # 수익률 계산
                        if position_side == 'Long':
                            pnl_percentage = ((exit_price - avg_entry_price) / avg_entry_price) * 100
                        else:
                            pnl_percentage = ((avg_entry_price - exit_price) / avg_entry_price) * 100
                        
                        # 시간 정보
                        start_time = datetime.fromtimestamp(int(first_trade['time']) / 1000)
                        end_time = datetime.fromtimestamp(int(last_trade['time']) / 1000)
                        duration_minutes = (int(last_trade['time']) - int(first_trade['time'])) / 60000
                        
                        position_group = {
                            'symbol': symbol,
                            'side': position_side,
                            'entry_price': avg_entry_price,
                            'exit_price': exit_price,
                            'quantity': total_qty,
                            'pnl_amount': group_pnl,
                            'pnl_percentage': pnl_percentage,
                            'start_time': start_time.strftime('%H:%M:%S'),
                            'end_time': end_time.strftime('%H:%M:%S'),
                            'duration_minutes': duration_minutes,
                            'trade_count': len(current_group_trades),
                            'position_type': 'Closed'
                        }
                        
                        position_groups.append(position_group)
                    
                    # 그룹 초기화
                    current_group_trades = []
                
                # 포지션 방향이 바뀌는 경우 (오버 트레이딩)
                elif (prev_net_position > 0 and current_net_position < 0) or (prev_net_position < 0 and current_net_position > 0):
                    # 이전 포지션 종료 및 새 포지션 시작 처리
                    # 복잡한 케이스이므로 현재는 단순하게 처리
                    pass
            
            # 마지막에 미완료 포지션이 있는 경우 처리
            if current_group_trades and abs(current_net_position) > 0.1:
                group_pnl = sum(pnl_map.get(str(t.get('id', '')), 0) for t in current_group_trades)
                
                if abs(group_pnl) > 0.001:  # 유의미한 손익만
                    # 그룹의 첫 거래와 마지막 거래
                    first_trade = current_group_trades[0]
                    last_trade = current_group_trades[-1]
                    
                    # 포지션 방향 결정 (net position 기준)
                    if current_net_position > 0:
                        position_side = 'Long'
                        # 진입 거래들 (BUY)
                        entry_trades = [t for t in current_group_trades if t['side'] == 'BUY']
                    else:
                        position_side = 'Short'
                        # 진입 거래들 (SELL)
                        entry_trades = [t for t in current_group_trades if t['side'] == 'SELL']
                    
                    # 평균 진입가 계산
                    if entry_trades:
                        total_cost = sum(float(t['price']) * float(t['qty']) for t in entry_trades)
                        total_qty = sum(float(t['qty']) for t in entry_trades)
                        avg_entry_price = total_cost / total_qty if total_qty > 0 else float(first_trade['price'])
                    else:
                        avg_entry_price = float(first_trade['price'])
                        total_qty = abs(current_net_position)
                    
                    # 미완료 포지션이므로 마지막 거래 가격을 현재가로 사용
                    current_price = float(last_trade['price'])
                    
                    # 수익률 계산 (미실현 손익 기반)
                    if position_side == 'Long':
                        pnl_percentage = ((current_price - avg_entry_price) / avg_entry_price) * 100
                    else:
                        pnl_percentage = ((avg_entry_price - current_price) / avg_entry_price) * 100
                    
                    # 시간 정보
                    start_time = datetime.fromtimestamp(int(first_trade['time']) / 1000)
                    end_time = datetime.fromtimestamp(int(last_trade['time']) / 1000)
                    duration_minutes = (int(last_trade['time']) - int(first_trade['time'])) / 60000
                    
                    position_group = {
                        'symbol': symbol,
                        'side': position_side,
                        'entry_price': avg_entry_price,
                        'exit_price': current_price,
                        'quantity': abs(current_net_position),
                        'pnl_amount': group_pnl,
                        'pnl_percentage': pnl_percentage,
                        'start_time': start_time.strftime('%H:%M:%S'),
                        'end_time': end_time.strftime('%H:%M:%S'),
                        'duration_minutes': duration_minutes,
                        'trade_count': len(current_group_trades),
                        'position_type': 'Open'  # 미완료 포지션 표시
                    }
                    
                    position_groups.append(position_group)
            
            return position_groups
            
        except Exception as e:
            logger.error(f"❌ {symbol} 포지션 그룹핑 실패: {e}")
            return []

    async def _create_empty_journal(self, target_date: datetime) -> bool:
        """거래 데이터가 없을 때 빈 매매일지 생성"""
        try:
            empty_daily_summary = {
                'date': target_date.strftime('%Y년 %m월 %d일'),
                'daily_pnl_percentage': 0.0,
                'daily_pnl_usd': 0.0,
                'trade_count': 0,
                'trading_volume': 0.0,
                'position_count': 0
            }
            
            journal_data = {
                'date': target_date,
                'title': '😴 오늘은 쉬어간 날... 내일은 더 열심히!',
                'emotional_rate': 3,
                'market_type': '횡보장',
                'difficulty_level': '하',
                'daily_summary': empty_daily_summary,
                'positions': [],
                'trading_symbols': []
            }
            
            success = await self.notion_uploader.create_emotional_journal_page(journal_data)
            return success
            
        except Exception as e:
            logger.error(f"❌ 빈 매매일지 생성 실패: {e}")
            return False

    async def test_api_connections(self):
        """API 연결 상태 테스트"""
        logger.info("🔍 API 연결 테스트 시작...")
        
        # Binance API 테스트
        try:
            account_info = await self.binance.test_connection()
            if account_info:
                logger.info(f"✅ Binance API 연결 성공")
                print("✅ Binance API: 연결 성공")
            else:
                logger.error("❌ Binance API 연결 실패")
                print("❌ Binance API: 연결 실패")
        except Exception as e:
            logger.error(f"❌ Binance API 연결 오류: {e}")
            print(f"❌ Binance API: 연결 오류 - {e}")
        
        # Notion API 테스트  
        try:
            success = await self.notion_uploader.test_connection()
            if success:
                logger.info("✅ Notion API 연결 성공")
                print("✅ Notion API: 연결 성공")
            else:
                logger.error("❌ Notion API 연결 실패")
                print("❌ Notion API: 연결 실패")
        except Exception as e:
            logger.error(f"❌ Notion API 연결 오류: {e}")
            print(f"❌ Notion API: 연결 오류 - {e}")
        
        # Supabase API 테스트
        if self.supabase:
            try:
                success = await self.supabase.test_connection()
                if success:
                    logger.info("✅ Supabase API 연결 성공")
                    print("✅ Supabase API: 연결 성공")
                else:
                    logger.error("❌ Supabase API 연결 실패")
                    print("❌ Supabase API: 연결 실패")
            except Exception as e:
                logger.error(f"❌ Supabase API 연결 오류: {e}")
                print(f"❌ Supabase API: 연결 오류 - {e}")
        else:
            print("⚠️  Supabase API: 설정되지 않음 (선택사항)")

    async def _save_daily_pnl_to_supabase(self, target_date: datetime, journal_data: Dict[str, Any]):
        """daily_pnl 테이블에 매매 요약 데이터 저장"""
        try:
            if not self.supabase:
                logger.warning("⚠️ Supabase가 설정되지 않았습니다.")
                return
            
            daily_summary = journal_data.get('daily_summary', {})
            positions = journal_data.get('positions', [])
            
            # daily_pnl 데이터 구성
            daily_pnl_data = {
                'daily_pnl_usd': float(daily_summary.get('daily_pnl_usd', 0)),
                'trade_count': int(daily_summary.get('trade_count', 0)),
                'trading_volume': float(daily_summary.get('trading_volume', 0)),
                'position_count': len(positions)  # 실제 포지션 수
            }
            
            # Supabase에 저장
            await self.supabase.save_daily_pnl(daily_pnl_data, target_date)
            logger.info(f"✅ {target_date.date()} 일별 매매 요약 저장 완료 (포지션: {daily_pnl_data['position_count']}개)")
            
        except Exception as e:
            logger.error(f"❌ daily_pnl 저장 실패: {e}")

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
        # 명령행 인수 파싱
        parser = argparse.ArgumentParser(
            description='감성적인 바이낸스 선물 매매일지 자동화 시스템',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
사용 예시:
  python main.py --date 2025-01-15    # 특정 날짜의 매매일지 생성
  python main.py                      # 오늘 날짜의 매매일지 생성
  python main.py --test-connection    # API 연결 테스트
            """
        )
        
        parser.add_argument(
            '--date', '-d',
            type=str,
            help='분석할 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)',
            default=None
        )
        
        parser.add_argument(
            '--test-connection', '-t',
            action='store_true',
            help='API 연결 상태만 테스트'
        )
        
        args = parser.parse_args()
        
        # 감성적인 매매일지 시스템 초기화
        journal_system = EmotionalTradingJournal()
        
        # 연결 테스트 모드
        if args.test_connection:
            await journal_system.test_api_connections()
            return
        
        # 날짜 설정
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d')
            except ValueError:
                logger.error("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.")
                sys.exit(1)
        else:
            target_date = datetime.now() - timedelta(days=1)  # 어제 날짜 기본값
        
        logger.info(f"📅 분석 날짜: {target_date.strftime('%Y년 %m월 %d일')}")
        
        # 매매일지 생성 파이프라인 실행
        logger.info("🚀 감성적인 매매일지 생성 파이프라인 시작!")
        success = await journal_system.run_full_pipeline(target_date)
        
        if success:
            print("🎉 감성적인 매매일지가 성공적으로 생성되어 Notion에 업로드되었습니다!")
        else:
            print("❌ 매매일지 생성에 실패했습니다. 로그를 확인해주세요.")
            sys.exit(1)
        
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
    from utils import setup_logging
    setup_logging()
    
    # 이벤트 루프 실행
    asyncio.run(main()) 