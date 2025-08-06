import os
from dotenv import load_dotenv
from typing import Dict, Any

# .env 파일에서 환경변수 로드
load_dotenv()

class Config:
    """프로젝트 설정 관리 클래스"""
    
    # Binance API 설정
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'False').lower() == 'true'
    
    # OpenAI API 설정
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Notion API 설정
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Supabase 설정 (선택사항)
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # 매매 원칙 (GPT 피드백용)
    TRADING_RULES = """
    나의 매매 원칙:
    1. RSI 30 이하일 때만 매수 진입
    2. RSI 70 이상일 때 매도 진입 고려
    3. MACD 저점에서 반등 시 진입
    4. 거래량 증가 확인 시 진입
    5. 추세 확인 후 진입 (상승추세에서 롱, 하락추세에서 숏)
    6. 손절은 진입가 대비 2% 이내
    7. 익절은 진입가 대비 3% 이상
    """
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """설정 유효성 검사"""
        required_keys = [
            'BINANCE_API_KEY', 'BINANCE_SECRET_KEY',
            'NOTION_TOKEN', 'NOTION_DATABASE_ID'
            # 선택사항: OPENAI_API_KEY (반성 메모 AI 생성용), SUPABASE_URL, SUPABASE_KEY
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        return {
            'is_valid': len(missing_keys) == 0,
            'missing_keys': missing_keys,
            'errors': [f"{key} 키가 누락되었습니다." for key in missing_keys]
        }

    @classmethod
    def get_binance_config(cls) -> Dict[str, str]:
        """Binance API 설정 반환"""
        return {
            'api_key': cls.BINANCE_API_KEY,
            'api_secret': cls.BINANCE_SECRET_KEY,
            'testnet': cls.BINANCE_TESTNET
        } 