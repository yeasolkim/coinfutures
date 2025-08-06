# import openai  # OpenAI 기능 비활성화
from datetime import datetime
from typing import Dict, List, Any, Optional
from config import Config
from utils import logger, format_percentage, format_korean_won

class GPTFeedbackGenerator:
    """감성적인 매매일지를 위한 GPT 피드백 생성 클래스"""
    
    def __init__(self):
        """초기화 (GPT 비활성화 모드)"""
        # GPT가 비활성화된 상태에서는 API 키 검증을 건너뜀
        # try:
        #     self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        # except:
        #     self.client = None  # GPT 비활성화 상태
        self.client = None  # OpenAI 기능 완전 비활성화
        
        self.trading_rules = Config.TRADING_RULES
        logger.info("감성적인 GPT 피드백 생성기 초기화 완료 (비활성화 모드)")

    async def generate_feedback(
        self, 
        positions: List[Dict[str, Any]],
        daily_summary: Dict[str, Any]
    ) -> str:
        """감성적인 매매 피드백 생성 (비활성화됨)
        
        Args:
            positions: 포지션별 손익 데이터
            daily_summary: 하루 전체 요약
            
        Returns:
            감성적인 피드백 텍스트
        """
        # OpenAI 기능이 비활성화되어 있으므로 fallback 피드백 반환
        return self._get_fallback_feedback(daily_summary)

    def _get_emotional_system_prompt(self) -> str:
        """감성적인 시스템 프롬프트"""
        return f"""
당신은 따뜻하고 인간적인 트레이딩 멘토입니다. 
매매일지를 작성하는 트레이더에게 감정적으로 공감하면서도 전문적인 조언을 제공해주세요.

매매 원칙:
{self.trading_rules}

피드백 스타일:
- 감정에 공감하면서 시작 (수익이면 축하, 손실이면 위로)
- 구체적이고 실용적인 조언 제공
- 격려와 동기부여 포함
- 존댓말보다는 친근한 반말 사용
- 이모지 적절히 활용
- 3-5개 문단으로 구성

피드백 구조:
1. 감정적 공감 및 전체 평가
2. 잘한 점과 아쉬운 점 분석
3. 기술적 지표와 원칙 준수 여부
4. 구체적인 개선 방안
5. 격려 메시지와 다음 목표

따뜻하면서도 전문적인 톤으로 작성해주세요.
"""

    def _build_emotional_feedback_prompt(
        self, 
        positions: List[Dict[str, Any]],
        daily_summary: Dict[str, Any]
    ) -> str:
        """감성적인 피드백 프롬프트 구성"""
        
        # 수익률과 거래 요약
        total_pnl = daily_summary.get('daily_pnl_percentage', 0)
        total_amount = daily_summary.get('total_pnl_amount', 0)
        total_trades = daily_summary.get('total_trades', 0)
        win_rate = daily_summary.get('win_rate', 0)
        
        # 오늘의 거래 개요
        prompt = f"""
오늘의 매매 결과를 분석해줘:

📊 **거래 요약**
- 전체 수익률: {total_pnl:+.2f}%
- 총 수익금: {format_korean_won(total_amount)}
- 거래 횟수: {total_trades}회
- 승률: {win_rate:.1f}%
"""

        # 포지션별 상세 분석
        if positions:
            prompt += f"\n💹 **포지션별 결과**\n"
            for i, pos in enumerate(positions[:5], 1):  # 최대 5개만
                prompt += f"{i}. {pos['symbol']} {pos['side']} | 진입: ${pos['entry_price']:,.2f} → 청산: ${pos['exit_price']:,.2f} | {pos['pnl_percentage']:+.2f}% ({format_korean_won(pos['pnl_amount'])})\n"
        
        prompt += f"""
        
🎯 **분석 요청**
위 매매 결과를 나의 매매 원칙과 비교해서 따뜻하고 친근하게 피드백해줘.
잘한 점은 칭찬하고, 아쉬운 점은 다음에 어떻게 개선할지 구체적으로 조언해줘.
"""
        
        return prompt

    def _get_fallback_feedback(self, daily_summary: Dict[str, Any]) -> str:
        """GPT API 실패 시 대체 피드백"""
        pnl_percentage = daily_summary.get('daily_pnl_percentage', 0)
        
        if pnl_percentage > 0:
            return """
🎉 오늘은 수익을 냈네! 축하해!

비록 AI 분석은 받을 수 없었지만, 플러스로 마감한 것 자체가 대단한 일이야. 

✅ 잘한 점:
- 손실 없이 수익으로 마감
- 시장 흐름을 어느 정도 읽었음
- 감정 조절이 어느 정도 되었음

🎯 다음 목표:
- 오늘의 성공 패턴을 기억하고 반복하자
- 원칙을 지키면서 꾸준히 성장하자
- 욕심 부리지 말고 안전한 매매 계속하자

📈 계속 이런 식으로 꾸준히 하면 분명 좋은 결과가 있을 거야!
"""
        else:
            return """
😔 오늘은 조금 아쉬운 결과였네...

하지만 괜찮아! 손실도 트레이딩의 일부이고, 중요한 건 여기서 배우는 거야.

💪 긍정적인 점:
- 큰 손실 없이 적당한 선에서 마감
- 경험과 교훈을 얻었음
- 다음 기회를 위한 준비 시간

🎯 다음 목표:
- 오늘의 실수를 분석하고 반복하지 말자
- 손절 원칙을 더 철저히 지키자
- 감정 조절에 더 신경 쓰자

🌈 내일은 분명 더 좋은 결과가 있을 거야. 포기하지 말고 계속 도전하자!
"""

    async def generate_learning_points(
        self, 
        positions: List[Dict[str, Any]]
    ) -> List[str]:
        """오늘의 학습 포인트 생성 (비활성화됨)"""
        # OpenAI 기능이 비활성화되어 있으므로 기본 학습 포인트 반환
        return ["📚 오늘도 소중한 경험을 쌓았다", "매매 원칙을 더 철저히 지키자", "리스크 관리에 더 신경 쓰자"]

    async def generate_motivation_message(
        self, 
        daily_summary: Dict[str, Any]
    ) -> str:
        """동기부여 메시지 생성 (비활성화됨)"""
        # OpenAI 기능이 비활성화되어 있으므로 기본 동기부여 메시지 반환
        return "🌟 매일 조금씩 성장하는 트레이더가 되자!" 