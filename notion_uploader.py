import os
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from notion_client import Client
from config import Config
from utils import logger, format_percentage, format_korean_won

class NotionUploader:
    """감성적인 매매일지를 위한 Notion API 연동 클래스"""
    
    def __init__(self):
        """초기화"""
        self.client = Client(auth=Config.NOTION_TOKEN)
        self.database_id = Config.NOTION_DATABASE_ID
        logger.info("감성적인 Notion 업로더 초기화 완료")

    async def find_existing_page_for_date(self, target_date: datetime) -> Optional[str]:
        """특정 날짜의 기존 페이지 검색"""
        try:
            # 날짜 포맷 (August 4, 2025)
            date_str = target_date.strftime('%B %d, %Y')
            
            # 데이터베이스에서 해당 날짜의 페이지 검색
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Date",
                    "date": {
                        "equals": target_date.strftime('%Y-%m-%d')
                    }
                }
            )
            
            if response['results']:
                page_id = response['results'][0]['id']
                logger.info(f"기존 페이지 발견: {page_id} ({date_str})")
                return page_id
            else:
                logger.info(f"기존 페이지 없음 - 새로 생성: {date_str}")
                return None
                
        except Exception as e:
            logger.error(f"기존 페이지 검색 중 오류: {e}")
            return None

    async def update_existing_page(self, page_id: str, journal_data: Dict[str, Any]) -> bool:
        """기존 페이지 업데이트"""
        try:
            # 페이지 속성 업데이트
            properties = self._build_emotional_properties(journal_data)
            
            # 페이지 내용 완전 교체
            content = await self._build_emotional_content(journal_data)
            
            # 기존 내용 삭제 후 새 내용 추가
            # 먼저 기존 children 가져오기
            children_response = self.client.blocks.children.list(block_id=page_id)
            
            # 기존 블록들 삭제
            for block in children_response['results']:
                try:
                    self.client.blocks.delete(block_id=block['id'])
                except:
                    pass  # 일부 블록은 삭제 불가능할 수 있음
            
            # 속성 업데이트
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            # 새 내용 추가
            if content:
                self.client.blocks.children.append(
                    block_id=page_id,
                    children=content
                )
            
            logger.info(f"기존 페이지 업데이트 완료: {page_id}")
            return True
            
        except Exception as e:
            logger.error(f"페이지 업데이트 중 오류: {e}")
            return False

    async def create_emotional_journal_page(self, journal_data: Dict[str, Any]) -> bool:
        """감성적인 매매일지 페이지 생성 또는 업데이트 (하루에 하나만)
        
        Args:
            journal_data: 매매일지 데이터
            
        Returns:
            성공 여부
        """
        try:
            target_date = journal_data.get('date')
            if not target_date:
                target_date = datetime.now()
            
            # 기존 페이지 검색
            existing_page_id = await self.find_existing_page_for_date(target_date)
            
            if existing_page_id:
                # 기존 페이지 업데이트
                logger.info("📝 기존 페이지를 업데이트합니다...")
                success = await self.update_existing_page(existing_page_id, journal_data)
                if success:
                    page_url = f"https://www.notion.so/{existing_page_id.replace('-', '')}"
                    logger.info(f"페이지 URL: {page_url}")
                return success
            else:
                # 새 페이지 생성
                logger.info("🆕 새로운 페이지를 생성합니다...")
                
                # 페이지 속성 구성
                properties = self._build_emotional_properties(journal_data)
                
                # 페이지 내용 구성
                children = await self._build_emotional_content(journal_data)
            
            # Notion 페이지 생성
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )
            
            logger.info(f"감성적인 매매일지 페이지 생성 완료: {response['id']}")
            page_url = f"https://www.notion.so/{response['id'].replace('-', '')}"
            logger.info(f"페이지 URL: {page_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"Notion 페이지 생성/업데이트 중 오류: {e}")
            return False

    def _build_emotional_properties(self, journal_data: Dict[str, Any]) -> Dict[str, Any]:
        """감성적인 매매일지 페이지 속성 구성"""
        try:
            daily_summary = journal_data.get('daily_summary', {})
            target_date = journal_data.get('date', datetime.now())
            
            # 날짜 포맷팅 (August 2, 2025 형태)
            formatted_date = target_date.strftime('%B %d, %Y')
            
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": journal_data.get('title', '오늘의 매매일지')
                            }
                        }
                    ]
                },
                "Date": {
                    "date": {
                        "start": target_date.strftime('%Y-%m-%d')
                    }
                },
                "Rate": {
                    "select": {
                        "name": self._convert_rate_to_stars(journal_data.get('emotional_rate', 3))
                    }
                },
                "Type": {
                    "select": {
                        "name": journal_data.get('market_type', '횡보장')
                    }
                },
                "Level": {
                    "select": {
                        "name": journal_data.get('difficulty_level', '중')
                    }
                },
                "수익금": {
                    "number": round(daily_summary.get('daily_pnl_usd', 0.0), 2)
                }
            }
            
            return properties
            
        except Exception as e:
            logger.error(f"페이지 속성 구성 중 오류: {e}")
            return {
                "제목": {
                    "title": [
                        {
                            "text": {
                                "content": "매매일지 (속성 오류)"
                            }
                        }
                    ]
                }
            }

    def _convert_rate_to_stars(self, rate: int) -> str:
        """중요도 Rate를 별 아이콘 개수로 변환 (0~5개)"""
        try:
            # 0~5 범위로 제한
            rate = max(0, min(5, int(rate)))
            
            # 별 아이콘으로 변환
            if rate == 0:
                return "-"  # 별 없음
            elif rate == 1:
                return "⭐"      # 별 1개
            elif rate == 2:
                return "⭐⭐"    # 별 2개
            elif rate == 3:
                return "⭐⭐⭐"  # 별 3개
            elif rate == 4:
                return "⭐⭐⭐⭐"  # 별 4개
            else:  # rate == 5
                return "⭐⭐⭐⭐⭐"  # 별 5개
                
        except Exception as e:
            logger.error(f"Rate 변환 중 오류: {e}")
            return "⭐⭐⭐"  # 기본값

    async def _build_emotional_content(self, journal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """감성적인 매매일지 페이지 내용 구성"""
        try:
            children = []
            daily_summary = journal_data.get('daily_summary', {})
            
            # 1. 매매 요약 섹션
            children.extend(self._create_trading_summary_section(daily_summary))
            
            # 2. 포지션별 상세 내역
            children.extend(self._create_position_table_section(journal_data))
            
            return children
            
        except Exception as e:
            logger.error(f"페이지 내용 구성 중 오류: {e}")
            return [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "페이지 내용 구성 중 오류가 발생했습니다."
                                }
                            }
                        ]
                    }
                }
            ]

    def _create_trading_summary_section(self, daily_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """매매 요약 섹션 생성 (Daily P&L 기반)"""
        try:
            # Daily P&L 기반 정확한 하루 손익 데이터
            daily_pnl_usd = daily_summary.get('daily_pnl_usd', 0)
            daily_pnl_krw = daily_summary.get('daily_pnl_krw', 0)
            daily_percentage = daily_summary.get('daily_pnl_percentage', 0)
            trade_count = daily_summary.get('trade_count', 0)
            position_count = daily_summary.get('position_count', 0)
            date = daily_summary.get('date', '오늘')
            
            # 손익에 따른 이모지 선택
            profit_emoji = "📈" if daily_pnl_usd >= 0 else "📉"
            money_emoji = "💰" if daily_pnl_usd >= 0 else "💸"
            
            return [
                # {
                #     "object": "block",
                #     "type": "heading_2",
                #     "heading_2": {
                #         "rich_text": [
                #             {
                #                 "type": "text",
                #                 "text": {
                #                     "content": f"📊 매매 요약"
                #                 }
                #             }
                #         ]
                #     }
                # },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {
                            "emoji": profit_emoji
                        },
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Daily P&L: {daily_pnl_usd:+.4f} USDT ({daily_percentage:+.2f}%)"
                                },
                                "annotations": {
                                    "bold": True
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"💱 거래량: {daily_summary.get('trading_volume', 0):.2f} USDT"
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"🎯 총 포지션: {position_count}개"
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
            
        except Exception as e:
            logger.error(f"매매 요약 섹션 생성 중 오류: {e}")
            return []

    def _create_position_table_section(self, journal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """포지션별 상세 내역 표 섹션 생성"""
        try:
            positions = journal_data.get('positions', [])
            
            sections = []
            
            if not positions:
                sections.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "오늘은 포지션 수익이 없었습니다."
                                }
                            }
                        ]
                    }
                })
                return sections
            
            # 표 헤더 생성
            table_rows = [
                {
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": "종목"}}],
                            [{"type": "text", "text": {"content": "방향"}}],
                            [{"type": "text", "text": {"content": "거래횟수"}}],
                            [{"type": "text", "text": {"content": "수익률"}}],
                            [{"type": "text", "text": {"content": "실손익"}}],
                            [{"type": "text", "text": {"content": "순수익"}}],
                            [{"type": "text", "text": {"content": "수수료"}}],
                            [{"type": "text", "text": {"content": "진입시점"}}],
                            [{"type": "text", "text": {"content": "종료시점"}}],
                            [{"type": "text", "text": {"content": "보유기간"}}]
                            ]
                        }
                }
            ]
            
            # 포지션 데이터 행 추가 (최대 20개까지)
            for pos in positions[:20]:
                # 수익금에 따른 아이콘 결정
                pnl_amount = float(pos.get('pnl_amount', 0))
                if pnl_amount > 0:
                    symbol_icon = "🟢"  # 초록색 동그라미 (수익)
                elif pnl_amount < 0:
                    symbol_icon = "🔴"  # 빨간색 동그라미 (손실)
                else:
                    symbol_icon = "⚪"  # 흰색 동그라미 (무손익)
                
                # 종목명에 아이콘 추가
                symbol_name = f"{symbol_icon} {pos['symbol']}"
                
                # 실제 수수료 데이터 사용
                trade_count = pos.get('trade_count', 1)
                commission = pos.get('commission', 0)  # 실제 수수료
                pure_pnl = float(pos.get('pnl_amount', 0))  # 순수익 (가격 차익)
                actual_pnl = pos.get('actual_pnl', pure_pnl)  # 실손익
                
                table_rows.append({
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": symbol_name}}],
                            [{"type": "text", "text": {"content": pos['side']}}],
                            [{"type": "text", "text": {"content": f"{trade_count}회"}}],
                            [{"type": "text", "text": {"content": f"{pos['pnl_percentage']:+.2f}%"}}],
                            [{"type": "text", "text": {"content": f"{actual_pnl:+.4f} USDT"}}],
                            [{"type": "text", "text": {"content": f"{pure_pnl:+.4f} USDT"}}],
                            [{"type": "text", "text": {"content": f"-{commission:.4f} USDT"}}],
                            [{"type": "text", "text": {"content": pos.get('entry_time', '')}}],
                            [{"type": "text", "text": {"content": pos.get('exit_time', '')}}],
                            [{"type": "text", "text": {"content": pos.get('duration', '')}}]
                        ]
                    }
                })
                
            # 표 블록 추가
            sections.append({
                        "object": "block",
                "type": "table",
                "table": {
                    "table_width": 10,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_rows
                        }
                    })
            
            # 요약 정보 추가
            if len(positions) > 20:
                sections.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"* 총 {len(positions)}개 포지션 중 상위 20개만 표시됨"
                                },
                                "annotations": {
                                    "italic": True
                                }
                            }
                        ]
                    }
                })
            
            return sections
            
        except Exception as e:
            logger.error(f"포지션 표 섹션 생성 중 오류: {e}")
            return []





    def test_connection(self) -> bool:
        """Notion API 연결 테스트"""
        try:
            # 데이터베이스 정보 조회로 연결 테스트
            self.client.databases.retrieve(database_id=self.database_id)
            logger.info("Notion API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"Notion API 연결 테스트 실패: {e}")
            return False 