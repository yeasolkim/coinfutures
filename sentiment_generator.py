import random
# import openai  # OpenAI 기능 비활성화
from typing import Dict, List, Any, Optional
from utils import logger, format_percentage, format_korean_won
from config import Config
import re # Added for regex in _generate_ai_reflection

class SentimentGenerator:
    """감정 요약 및 반성 생성 클래스"""
    
    def __init__(self):
        """초기화"""
        # OpenAI 클라이언트 초기화 (비활성화)
        # try:
        #     self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        # except:
        #     self.client = None  # GPT 비활성화 상태
        self.client = None  # OpenAI 기능 완전 비활성화
        
        # 매매 원칙 정의
        self.trading_rules = """
📌 목표 : 손실 없는 매매 기록 만들기를 목표로 하기. 돈벌기 🙅🙅‍♀️🙅‍♂️

### 🍹매매 원칙

- 물타는 시점은 신중히! 2차 저점이라고 생각되는 곳!
- 1/20, 1/40 반드시 분할매매.
- 레버리지는 5배 미만으로 하기.
    - 5배 - 변동성 20% 청산
    - 60배 - 변동성 3% 청산
- 매수/매도 자리가 명확한 경우만 진입하기.역추세매매: 과매도/과매수
- 횡보할때는 진입하기 말기
- 횡보하다가 볼린저 밴드가 넓어지려고 하는 경우에는 2틱정도 더 보고 진입하기. 큰 방향성 나올 수 있음. 볼린저 밴드 다 열린 후 바닥잡기
- 풀 음봉/양봉 후에는 2틱 정도 더 기다려보기
- 5분봉, 15분봉, 4시간봉, 일봉, RSI, MACD, 거래량, Bollinger Bands, 차트형태
- 발목 매도하기. 못먹는 구간을 아까워하지 말기.
- 차트를 보고 있지 않으면 포지션 모두 정리하기(수면매매 ❌)
- 상승장에서는 바닥이라고 생각되는곳에서 줍줍 앤 존버
        """
        
        self.emotional_phrases = {
            'high_profit': [
                "💰 돈이 우르르 들어와서 기분이 날아갈 것 같음",
                "🚀 로켓처럼 수익이 치솟아서 심장이 두근거림",
                "⚡ 번개같은 수익에 잠깐 이게 현실인가 싶었음",
                "🎯 완벽한 타이밍에 진입해서 소름이 돋았음",
                "🔥 불타는 차트를 보며 내 안의 트레이더 혼이 깨어남",
                "💎 다이아몬드 핸드로 버틴 결과가 이렇게 달콤할 줄이야"
            ],
            'medium_profit': [
                "😊 적당한 수익으로 오늘도 밥값은 벌었다",
                "👍 꾸준히 올라가는 수익을 보니 뿌듯함",
                "🎈 풍선처럼 부풀어 오르는 계좌 잔고",
                "🌱 작지만 꾸준한 성장, 이게 바로 복리의 힘",
                "⭐ 오늘도 무난하게 플러스, 나쁘지 않아",
                "🍯 꿀같은 수익률이지만 욕심은 금물"
            ],
            'small_profit': [
                "🤏 쥐꼬리만한 수익이지만 그래도 플러스",
                "😅 간신히 손익분기점을 넘어선 기분",
                "🐜 개미같이 작은 수익도 모이면 태산",
                "📈 조금씩이라도 올라가는 게 어디야",
                "🌟 작은 별이라도 빛나고 있으니까",
                "💧 한 방울 한 방울이 바다를 만든다"
            ],
            'small_loss': [
                "😔 작은 손실이지만 마음이 쓰라림",
                "💸 돈이 날아가는 소리가 들리는 것 같아",
                "🌧️ 조금 아쉬운 결과, 내일은 더 잘하자",
                "😤 이 정도 손실은 수업료라고 생각하자",
                "🎭 손실의 아픔보다는 교훈을 얻었다",
                "⚡ 작은 번개라도 맞으면 아프네"
            ],
            'medium_loss': [
                "😰 제법 큰 손실에 식은땀이 나기 시작",
                "🩸 피같은 내 돈이 흘러가는 게 보임",
                "💔 심장이 쪼개지는 것 같은 손실",
                "😵 어지러워지는 손실 폭풍",
                "🌊 손실의 파도에 휩쓸린 기분",
                "⛈️ 폭풍같은 손실에 멘탈이 흔들림"
            ],
            'high_loss': [
                "😱 세상이 무너지는 것 같은 충격적인 손실",
                "🔥 불지옥 같은 손실에 정신을 잃을 뻔",
                "💀 죽을 맛인 손실, 트레이딩이 이렇게 무서운 거였나",
                "⚰️ 관짝에 한 발 들여놓은 기분의 손실",
                "🌪️ 토네이도 같은 손실에 모든 게 날아가버림",
                "🥶 얼어붙은 계좌를 보며 오한이 들기 시작"
            ],
            'high_win_rate': [
                "🎯 백발백중 스나이퍼 모드 ON",
                "🏹 화살이 과녁을 뚫는 듯한 정확성",
                "⚡ 번개같은 판단력이 빛을 발함",
                "🔮 수정구슬이라도 가진 것처럼 정확함",
                "🎪 서커스 곡예사 같은 완벽한 컨트롤"
            ],
            'low_win_rate': [
                "🎰 도박장에서 연패하는 기분",
                "🎲 주사위가 계속 나쁜 숫자만 나오네",
                "🌪️ 뭘 해도 꼬이는 날이었나봐",
                "💫 별들이 모두 나에게 등을 돌린 느낌",
                "🎭 트레이딩 신이 나를 시험하는 건가"
            ]
        }
        
        self.reflection_templates = {
            'profit': [
                "수익을 낸 건 좋지만 {}이 아쉬웠다",
                "다음에는 {}을 더 주의해야겠다",
                "{}에서 운이 좋았던 것 같다",
                "{}을 제대로 지켜서 수익을 낼 수 있었다",
                "앞으로는 {}을 더 철저히 해야겠다"
            ],
            'loss': [
                "{}때문에 손실을 봤다, 다음에는 꼭 주의하자",
                "{}을 무시한 결과가 이렇게 나왔다",
                "{}에 대한 공부가 더 필요할 것 같다",
                "{}을 제대로 했다면 이런 손실은 없었을 텐데",
                "{}이 얼마나 중요한지 다시 한 번 깨달았다"
            ]
        }
        
        self.trading_issues = [
            "손절 타이밍", "익절 타이밍", "진입 타이밍", "레버리지 조절",
            "리스크 관리", "감정 조절", "시장 분석", "기술적 분석",
            "자금 관리", "포지션 사이징", "추세 판단", "변동성 대응"
        ]
        
        logger.info("감정 생성기 초기화 완료")
    
    def generate_emotional_title(self, daily_summary: Dict[str, Any]) -> str:
        """감정적인 제목 생성 (고정 형식)"""
        try:
            # 날짜 정보 추출
            date = daily_summary.get('date', '')
            
            # 날짜가 있으면 "x월 x일 매매일지" 형식으로 반환
            if date:
                return f"{date} 매매일지"
            else:
                # 날짜 정보가 없으면 기본 형식
                return "매매일지"
            
        except Exception as e:
            logger.error(f"제목 생성 중 오류: {e}")
            return "매매일지"
    
    def generate_emotion_summary(self, daily_summary: Dict[str, Any]) -> List[str]:
        """감정 요약 생성"""
        try:
            pnl_percentage = daily_summary.get('daily_pnl_percentage', 0)
            win_rate = daily_summary.get('win_rate', 0)
            total_trades = daily_summary.get('total_trades', 0)
            
            emotions = []
            
            # 수익률 기반 감정
            if pnl_percentage > 5:
                emotions.extend(random.sample(self.emotional_phrases['high_profit'], 2))
            elif pnl_percentage > 2:
                emotions.extend(random.sample(self.emotional_phrases['medium_profit'], 2))
            elif pnl_percentage > 0:
                emotions.extend(random.sample(self.emotional_phrases['small_profit'], 2))
            elif pnl_percentage > -2:
                emotions.extend(random.sample(self.emotional_phrases['small_loss'], 2))
            elif pnl_percentage > -5:
                emotions.extend(random.sample(self.emotional_phrases['medium_loss'], 2))
            else:
                emotions.extend(random.sample(self.emotional_phrases['high_loss'], 2))
            
            # 승률 기반 감정
            if win_rate > 70:
                emotions.append(random.choice(self.emotional_phrases['high_win_rate']))
            elif win_rate < 40:
                emotions.append(random.choice(self.emotional_phrases['low_win_rate']))
            
            # 거래 횟수 기반 감정
            if total_trades > 10:
                emotions.append("🔄 오늘은 정말 바쁜 하루였다, 차트에 붙어살았네")
            elif total_trades == 0:
                emotions.append("😴 오늘은 시장이 심심해서 그냥 쉬었다")
            
            return emotions[:3]  # 최대 3개까지
            
        except Exception as e:
            logger.error(f"감정 요약 생성 중 오류: {e}")
            return ["😐 오늘의 매매에 대한 감정을 표현하기 어렵네요"]
    
    def generate_reflection_memo(self, daily_summary: Dict[str, Any], positions: List[Dict[str, Any]]) -> List[str]:
        """반성 메모 생성 (OpenAI 기반)"""
        try:
            # OpenAI가 활성화되어 있다면 GPT로 생성
            if self.client:
                return self._generate_ai_reflection(daily_summary, positions)
            else:
                # 기존 템플릿 방식으로 fallback
                return self._generate_template_reflection(daily_summary, positions)
            
        except Exception as e:
            logger.error(f"반성 메모 생성 중 오류: {e}")
            return ["📝 오늘의 매매에서 배운 점을 정리해보자"]

    def _generate_ai_reflection(self, daily_summary: Dict[str, Any], positions: List[Dict[str, Any]]) -> List[str]:
        """OpenAI 기반 반성 메모 생성 (매매원칙 평가 강화) - 비활성화됨"""
        # OpenAI 기능이 비활성화되어 있으므로 템플릿 기반 반성 메모 반환
        return self._generate_template_reflection(daily_summary, positions)

    def _generate_template_reflection(self, daily_summary: Dict[str, Any], positions: List[Dict[str, Any]]) -> List[str]:
        """기존 템플릿 방식 반성 메모 생성 (Fallback)"""
        pnl_percentage = daily_summary.get('daily_pnl_percentage', 0)
        win_rate = daily_summary.get('win_rate', 0)
        
        reflections = []
        
        # 수익/손실에 따른 반성
        if pnl_percentage > 0:
            template = random.choice(self.reflection_templates['profit'])
            issue = random.choice(self.trading_issues)
            reflections.append(template.format(issue))
            
            if win_rate < 60:
                reflections.append("수익은 났지만 승률이 아쉽다. 더 신중하게 진입점을 선택하자")
                
        else:
            template = random.choice(self.reflection_templates['loss'])
            issue = random.choice(self.trading_issues)
            reflections.append(template.format(issue))
            
            reflections.append("손실을 본 것도 경험이다. 다음에는 더 잘할 수 있을 거야")
        
        # 일반적인 다짐
        general_reflections = [
            "원칙을 지키는 게 가장 중요하다",
            "감정에 휘둘리지 말고 차분하게 매매하자",
            "작은 수익이라도 꾸준히 쌓아가는 게 답이다",
            "리스크 관리가 수익보다 더 중요하다",
            "시장은 항상 옳다, 내가 틀릴 수 있다는 겸손함을 잊지 말자",
            "매일 조금씩이라도 발전하는 트레이더가 되자"
        ]
        
        reflections.append(random.choice(general_reflections))
        
        return reflections[:3]  # 최대 3개까지
    
    def get_emotion_rate(self, daily_summary: Dict[str, Any], positions: List[Dict[str, Any]] = None) -> int:
        """중요도 Rate (0~5) 생성 - 손실이 클수록, 손실 포지션이 많을수록 높은 중요도"""
        try:
            pnl_percentage = daily_summary.get('daily_pnl_percentage', 0)
            positions = positions or []
            
            # 손실 포지션 개수와 손실 규모 계산
            loss_positions = [pos for pos in positions if float(pos.get('pnl_amount', 0)) < 0]
            loss_count = len(loss_positions)
            total_positions = len(positions)
            
            # 총 손실 비율
            total_loss_amount = sum(float(pos.get('pnl_amount', 0)) for pos in loss_positions)
            loss_percentage = abs(pnl_percentage) if pnl_percentage < 0 else 0
            
            # 중요도 계산 (손실이 클수록, 손실 포지션이 많을수록 높은 별점)
            importance_score = 0
            
            # 1. 손실 비율에 따른 점수
            if loss_percentage > 5:
                importance_score += 3  # 5% 이상 손실 시 +3점
            elif loss_percentage > 2:
                importance_score += 2  # 2-5% 손실 시 +2점
            elif loss_percentage > 0:
                importance_score += 1  # 약간의 손실 시 +1점
            
            # 2. 손실 포지션 비율에 따른 점수
            if total_positions > 0:
                loss_ratio = loss_count / total_positions
                if loss_ratio > 0.7:  # 70% 이상이 손실
                    importance_score += 2
                elif loss_ratio > 0.5:  # 50-70%가 손실
                    importance_score += 1
            
            # 3. 큰 손실 포지션 존재 여부
            big_loss_positions = [pos for pos in loss_positions if float(pos.get('pnl_percentage', 0)) < -5]
            if big_loss_positions:
                importance_score += 1
            
            # 4. 수익이 나도 손실 포지션이 많으면 경고
            if pnl_percentage > 0 and loss_count >= 3:
                importance_score += 1
            
            # 최종 중요도 결정 (0~5점)
            if importance_score >= 5:
                return 5  # ⭐⭐⭐⭐⭐ 매우 중요 - 큰 손실, 반드시 분석 필요
            elif importance_score >= 4:
                return 4  # ⭐⭐⭐⭐ 중요 - 상당한 손실
            elif importance_score >= 2:
                return 3  # ⭐⭐⭐ 보통 - 일부 손실
            elif importance_score >= 1:
                return 2  # ⭐⭐ 낮음 - 약간의 손실
            elif pnl_percentage > 2:
                return 1  # ⭐ 매우 낮음 - 좋은 수익, 특별히 분석할 필요 없음
            else:
                return 0  # 별 없음 - 평범한 수익
                
        except Exception as e:
            logger.error(f"중요도 평점 생성 중 오류: {e}")
            return 3
    
    def generate_motivational_quote(self, daily_summary: Dict[str, Any]) -> str:
        """동기부여 명언 생성"""
        try:
            pnl_percentage = daily_summary.get('daily_pnl_percentage', 0)
            
            if pnl_percentage > 0:
                quotes = [
                    "🌟 성공은 준비된 자에게 기회가 왔을 때 만들어진다",
                    "💎 다이아몬드는 압력 속에서 만들어진다",
                    "🏆 오늘의 성공은 내일의 더 큰 성공을 위한 발판이다",
                    "⚡ 기회는 준비된 자에게만 찾아온다"
                ]
            else:
                quotes = [
                    "🌱 실패는 성공의 어머니다",
                    "💪 넘어져도 다시 일어서는 것이 진정한 용기다",
                    "🌈 폭풍 후에 무지개가 온다",
                    "🔥 시련은 나를 더 강하게 만든다"
                ]
            
            return random.choice(quotes)
            
        except Exception as e:
            logger.error(f"동기부여 명언 생성 중 오류: {e}")
            return "📈 매일 조금씩 성장하는 트레이더가 되자" 