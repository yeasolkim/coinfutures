# 🚀 빠른 설정 가이드

이 가이드를 따라하면 5분 내에 바이낸스 선물 거래 분석 시스템을 설정할 수 있습니다.

## ✅ 1단계: Python 환경 확인
```bash
python --version  # Python 3.8 이상 필요
pip --version
```

## ✅ 2단계: 종속성 설치
```bash
pip install -r requirements.txt
```

## ✅ 3단계: 환경변수 설정
```bash
# 예시 파일 복사
cp env_example.txt .env

# .env 파일 편집 (실제 API 키 입력)
nano .env  # 또는 다른 텍스트 에디터 사용
```

### 필요한 API 키들:

#### 🔑 Binance API (필수)
1. [Binance 로그인](https://www.binance.com) → API Management
2. Create API → **선물 거래 권한만 활성화** (Read Only)
3. API Key + Secret Key 복사

#### 🤖 OpenAI API (필수) 
1. [OpenAI Platform](https://platform.openai.com) → API Keys
2. Create new secret key
3. GPT-4 접근 권한 확인

#### 📝 Notion API (필수)
1. [Notion Developers](https://developers.notion.com) → New Integration
2. 권한: Read, Insert, Update content
3. Integration Token 복사
4. Database 생성 및 Integration 연결
5. Database ID 복사 (URL에서 확인 가능)

### .env 파일 예시:
```
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_SECRET_KEY=your_actual_secret_key_here
BINANCE_TESTNET=False
OPENAI_API_KEY=sk-your_openai_key_here
NOTION_TOKEN=secret_your_notion_token_here  
NOTION_DATABASE_ID=your_database_id_here
```

## ✅ 4단계: Notion 데이터베이스 설정

새 Notion 페이지에서 데이터베이스 생성:

```
/database → Full page 선택
```

다음 컬럼들을 추가:

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| 제목 | Title | (기본 생성됨) |
| 날짜 | Date | 거래 날짜 |
| 종목 | Rich Text | 거래 종목 |
| 거래횟수 | Number | 총 거래 횟수 |
| 평균가 | Number | 평균 체결가 |
| 총거래량 | Number | 총 거래량 |
| 수수료 | Number | 총 수수료 |
| 평가등급 | Select | A, B, C, D, F 옵션 추가 |
| 상태 | Select | 완료, 진행중 옵션 추가 |

**Integration 연결하기:**
1. 데이터베이스 페이지에서 `...` 클릭
2. `Add connections` 선택
3. 생성한 Integration 선택

## ✅ 5단계: 설정 확인
```bash
python main.py --config-check
```

✅가 모두 나오면 설정 완료!

## ✅ 6단계: 첫 실행
```bash
# 테스트 실행 (실제 API 사용)
python main.py --symbol BTCUSDT

# 테스트넷으로 먼저 테스트하려면:
# .env에서 BINANCE_TESTNET=True로 설정 후 실행
```

## 🎯 완료!

성공적으로 실행되면:
- `charts/` 폴더에 차트 이미지 생성
- Notion 데이터베이스에 매매일지 추가
- 콘솔에 Notion 페이지 링크 출력

## 🆘 문제 해결

### "API 키 오류"
- `.env` 파일의 API 키들을 다시 확인
- Binance API 권한 설정 확인

### "Notion 연결 실패"  
- Database ID가 정확한지 확인
- Integration이 데이터베이스에 연결되어 있는지 확인

### "거래 데이터 없음"
- 지정한 날짜에 실제 거래가 있었는지 확인
- 심볼명이 정확한지 확인 (BTCUSDT, ETHUSDT 등)

### 기타 문제
- `trading_journal.log` 파일에서 상세 로그 확인
- `python main.py --config-check`로 설정 재확인

---

**🎉 이제 자동화된 매매일지를 즐겨보세요!** 